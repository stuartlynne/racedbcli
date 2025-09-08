#!/usr/bin/env python3

import sys
import os
import io
import json
import autopage, argparse
from enum import Enum
import traceback
#import argparse
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
import time
from urllib.parse import urljoin
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from libs.autopageex import AutoPagerEx
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL
from libs.bikeregcsv import BikeRegCSV
from libs.ccn import GetCCN
#from libs.categorymap import CategoryMap
from libs.catmap import CatMap
from libs.lib import gprint, yprint
from cli.competition import create_competition_from_template
from enum import Enum

# This script will process a BikeReg CSV file to load into RaceDB competition.
#
# 1. Process the BikeReg CSV file
# 2. Process the registrations
# 3. Upload the license holders
# 4. Create a new competition using older date as template
# 5. Upload the registrations
# 

class LicenseCheck:
    class LicenseCheckLevel(Enum):
        no_license_check = 0
        club_license_check = 1
        regional_license_check = 2
        regional_champion_license_check = 3

    @staticmethod
    def level_for_race_class(race_class: str | None) -> "LicenseCheck.LicenseCheckLevel":
        if not race_class:
            return LicenseCheck.LicenseCheckLevel.regional_license_check
        rc = race_class.strip().lower()
        if rc.startswith('citizen'):
            return LicenseCheck.LicenseCheckLevel.no_license_check
        if rc.startswith('club'):
            return LicenseCheck.LicenseCheckLevel.club_license_check
        if rc.startswith('reg. champ') or rc.startswith('regional champ'):
            return LicenseCheck.LicenseCheckLevel.regional_champion_license_check
        if rc.startswith('regional'):
            return LicenseCheck.LicenseCheckLevel.regional_license_check
        return LicenseCheck.LicenseCheckLevel.regional_license_check

    def __init__(self, race_class: str | None = None):
        # Map known race classes to a license check level (see above)
        self.level = self.level_for_race_class(race_class)


class GetBikeReg:
    def __init__(self, racedb=None, ccn=None, sql=None, catmap=None, comp=None, username=None, password=None, csvfile=None):
        self.racedb = racedb
        self.ccn = ccn
        self.sql = sql
        self.catmap = catmap
        self.comp = comp
        self.username = username
        self.password = password
        self.csvfile = csvfile
        self.bikeregcsv = BikeRegCSV(csvfile)
        self.registrations = []

        # Determine license check level from competition race class (if available)
        self.license_check = LicenseCheck.level_for_race_class(comp.get('race_class_name') if isinstance(comp, dict) else None)
        print(f"Determined license check level: {self.license_check.name}", file=sys.stdout)


        # Per-format organizer label mapping (CatMap instance)
        # and allowed category codes from DB for purchase detection
        self.allowed_codes = None
        self.stats = {
                'racedb_found': 0,
                'ccn_found': 0,
                'both_found': 0,
        }

    # check license holder
    #   - missing in RaceDB
    #   - license number does not match
    #   - uci id does not match
    def check_license_holder(self, first_name=None, last_name=None, uci_id=None, license_holder=None, person=None, msg=None):
        print(f"Checking: {first_name} {last_name} {uci_id} using {msg}", file=sys.stdout)
        print(f"  Person: {person}", file=sys.stdout)
        print(f"  License Holder: {license_holder}", file=sys.stdout)
        if not license_holder:
            self.racedb.new_license_holder(first_name, last_name, uci_id, person)
            return
        if person["license_number"] != license_holder["license_code"]:
            self.racedb.update_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                  dob=license_holder['date_of_birth'], license_number=person["license_number"], team=person["team"], msg="license number")
            return
        if person["uci_id"] != license_holder["uci_id"]:
            self.racedb.update_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                  dob=license_holder['date_of_birth'], license_number=person["license_number"], team=person["team"], msg="uci id")

        
    def process_bikereg(self):
        for i, br in self.bikeregcsv.get_next():
            first_name = br['First Name']
            last_name = br['Last Name']
            dob = br['Date of Birth']
            gender = br['Gender']
            age = br.get('Age on 12/31/2025', None)
            # XXX for testing with last years REG files
            if not age:
                age = br.get('Age on 12/31/2024', None)
            br['Age'] = age

            # 
            # 1. See if we can find in CCN to get license and uci id
            # 2. If not found, then see if we can find in RaceDB using first name, last name, dob
            # 3. If not found, see if we can find in RaceDB using first name, last name

            print(f"Processing[{i}]: {last_name}, {first_name}, {dob}, {gender}", file=sys.stderr)
            licenses = ccn_license_holder = racedb_license_holder = None
            
            if dob:
                racedb_license_holders = self.sql.find_name_dob(first_name, last_name, dob)
                by = "name dob"
            else:
                racedb_license_holders = self.sql.find_name(first_name, last_name)
                by = "name"

            if racedb_license_holders:
                self.stats['racedb_found'] += 1
                for i, licenseholder in enumerate(racedb_license_holders):
                    info = [ licenseholder[k] for k in ['last_name', 'first_name', 'license_code', 'uci_id',] ]
                    print(f"  RaceDB[{i}] {info} {by}", file=sys.stdout)



            #if racedb_license_holders:
            #    racedb_license_holder = racedb_license_holders[0]

            ccn_license_holders = self.ccn.get_license_holders(first_name, last_name, )
            if ccn_license_holders and len(ccn_license_holders) == 1:
                self.stats['ccn_found'] += 1
                ccn_license_holder = ccn_license_holders[0]
                print('  CCN License Holder:', ccn_license_holder, file=sys.stderr)
                licenses = ccn_license_holder['licenses']
                road = licenses.get('Road', None)
                cyclocross = licenses.get('Cyclocross', None)
                print(f'  CCN: {ccn_license_holder["uci_id"]} {ccn_license_holder["license_number"]} {road} {cyclocross}', file=sys.stdout)
                license_categories = ccn_license_holder['licenses']
            else:
                license_categories = {}

            self.stats['both_found'] += 1 if ccn_license_holders and racedb_license_holders else 0

            br['licenses'] = license_categories

            if ccn_license_holders and racedb_license_holders:
                uciIdFlag = ccn_license_holders[0]["uci_id"] != racedb_license_holders[0]["uci_id"] 
                licenseNumberFlag = ccn_license_holders[0]["license_number"] != racedb_license_holders[0]["license_code"]
                info = []
                if uciIdFlag:
                    yprint(f"  UCI ID does not match: {ccn_license_holders[0]['uci_id']} != {racedb_license_holders[0]['uci_id']}", file=sys.stdout)
                    info.append('UCI_ID')
                if licenseNumberFlag:
                    yprint(f"  License Number does not match: {ccn_license_holders[0]['license_number']} != {racedb_license_holders[0]['license_code']}", 
                          file=sys.stdout)
                    info.append('License Number')
                if uciIdFlag or licenseNumberFlag:
                    self.racedb.update_license_holder(first_name=first_name, last_name=last_name, dob=dob, gender=gender,
                                  uci_id=ccn_license_holders[0]["uci_id"], license_number=ccn_license_holders[0]["license_number"], msg=info)
                br['uci_id'] = ccn_license_holders[0]["uci_id"]
                br['license_number'] = ccn_license_holders[0]["license_number"]
                br['license_type'] = ccn_license_holders[0]["license_type"]
                br['license_check'] = True
            elif racedb_license_holders:
                br['license_number'] = racedb_license_holders[0]['license_code']
                br['uci_id'] = racedb_license_holders[0]['uci_id']
                br['license_check'] = False
            else:
                br['license_check'] = False

            # If we cannot find the license holder in RaceDB, then we need to add them
            if not ccn_license_holders and not racedb_license_holders:
                yprint(f"  Cannot find: {first_name} {last_name} {dob} {gender} in RaceDB or CCN", file=sys.stdout)
            elif not racedb_license_holders:
                yprint(f"  Cannot find: {first_name} {last_name} {dob} {gender} in RaceDB", file=sys.stdout)
                self.racedb.new_license_holder(first_name=first_name, last_name=last_name, gender=gender, dob=dob, msg='Not found')

            # Normalize category label via per-format CatMap mapping
            label = br['Category Entered / Merchandise Ordered']
            print(f"  label: {label} license_check: {br['license_check']}", file=sys.stdout)
            canonical = label
            if self.catmap:
                entry = self.catmap.lookup_label(label)
                if entry and isinstance(entry, (list, tuple)) and entry:
                    canonical = entry[0]

            # If canonical is not an allowed category code, treat as a purchase
            if self.allowed_codes and canonical not in self.allowed_codes:
                print('  Purchased: %s' % (canonical), file=sys.stdout)
                self.racedb.add_purchase(first_name=first_name, last_name=last_name, purchase=canonical)
                continue

            br['requested_category'] = canonical
            self.registrations.append(br)

            #print('Category entered: %s' % br['Category Entered / Merchandise Ordered'], file=sys.stdout)
            #if i > 20:
            #    break


        print(f"Processed {len(self.registrations)} registrations", file=sys.stdout)
        print(f"  Found in RaceDB: {self.stats['racedb_found']}", file=sys.stdout)
        print(f"  Found in CCN: {self.stats['ccn_found']}", file=sys.stdout)
        print(f"  Found in both: {self.stats['both_found']}", file=sys.stdout)
        print()
        print()
        print()

    def process_registrations(self):

        for i, br in enumerate(self.registrations):

            print('-----------------------------------')

            first_name = br['First Name']
            last_name = br['Last Name']
            dob = br['Date of Birth']
            gender = br['Gender']
            age = br.get('Age on 12/31/2025', None)
            uci_id = br.get('UCI ID', None)
            if not age:
                age = br.get('Age on 12/31/2024', None)
            license_number = br.get('license_number', None)
            license_categories = br['licenses']
            requested_category = br['requested_category']
            license_type = br.get('license_type', None)
            license_check = br.get('license_check', False)
            purchases = self.racedb.purchases.get((last_name, first_name), [])

            print(f"Processing: {last_name}, {first_name}, {dob}, {gender},", file=sys.stdout)
            print(f"  Age: {age} Purchases: {purchases}", file=sys.stdout)

            print(f"  License_categories: {license_categories}", file=sys.stderr)
            if license_categories:
                road = license_categories.get('Road', None)
                cyclocross = license_categories.get('Cyclocross', None)
                print(f'  CCN Licenses: Road: {road} Cyclocross: {cyclocross}', file=sys.stderr)
            else:
                licenses = []
            allowed_categories, licenses = self.catmap.get_event_category(license_categories, gender, age, )
            print('  Allowed Categories:', allowed_categories, file=sys.stderr)
            print('  Licenses:', licenses, file=sys.stderr)
            print(f"  Requested: {requested_category}", file=sys.stderr)

            #self.license_check
            #no_license_check = 0
            #club_license_check = 1
            #regional_license_check = 2
            #regional_champion_license_check = 3
            #self.license_check = LicenseCheck.level_for_race_class(comp.get('race_class_name') if isinstance(comp, dict) else None)
        
            check_allowed = self.license_check in [LicenseCheck.LicenseCheckLevel.regional_license_check, LicenseCheck.LicenseCheckLevel.regional_champion_license_check]

            if requested_category not in allowed_categories and check_allowed:

                yprint('  Requested [%s] CATEGORY NOT ALLOWED' % (requested_category), file=sys.stderr)
                self.racedb.add_registration(first_name=first_name, last_name=last_name, uci_id=uci_id, gender=gender,
                                             category=requested_category, license_number=license_number, license_type=license_type, license_check=False,
                                             note=f"Purchases {purchases}\nCATEGORY NOT ALLOWED [{requested_category}]\nAllowed{allowed_categories}\nLicense: {licenses}",
                                             allowed=False)
                        
            else:
                print('  Requested [%s] CATEGORY ALLOWED' % (requested_category), file=sys.stderr)
                self.racedb.add_registration(first_name=first_name, last_name=last_name, uci_id=uci_id, gender=gender,
                                             category=requested_category, license_number=license_number, 
                                             license_type=license_type, license_check=license_check,
                                             note=f"Purchases {purchases}\nALLOWED [{requested_category}]\nLicense: {licenses}",
                                             allowed=True)



epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""
def main():
    parser = argparse.ArgumentParser(description="RaceDB update license holders from xlsx.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--csvfile', type=str, default=None, help='BikeReg CSV file')
    parser.add_argument('--template_date', type=str, help='Copy the competition from this date.')
    parser.add_argument('--start_date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--category_format', type=str, help='CategoryFormat name (e.g., lmcx2018)')
    parser.add_argument('--new_name', type=str, help='Name of the competition.')
    parser.add_argument('--bibs', action='store_true', help='Generate bib numbers.')
    parser.add_argument('--stderr', "--debug", action='store_true', help='Enable stderr output.')
    parser.add_argument("--stderrdup", action='store_true', help='Send stderr to stdout.')
    #parser.add_argument('--replace', action='store_true', help='Replace existing competition.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    csvfile = args.csvfile         
    template_date = args.template_date
    start_date = args.start_date
    category_format = args.category_format
    new_name = args.new_name
    bibs = args.bibs

    #if False:
    #    os.environ['LESS'] += f"--quit-if-one-screen"


    #host = host.removeprefix("https://").removeprefix("http://").split(":")[0]
    # 1. Process the BikeReg CSV file
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')

        sql = RaceDBSQL(host)
        racedb = RaceDB(host=host, username=username, password=password,)

        # Determine categories from either start_date (competition) or category_format
        categories = []
        fmt_name = None
        if start_date:
            comp, categories = sql.find_competition_categories(date=start_date)
            if not comp:
                print(f"Error: competition not found for start_date {start_date}", file=sys.stderr)
                sys.exit(1)
            print(
                f"Using categories from competition '{comp.get('name')}' on {comp.get('start_date')} "
                f"(discipline: {comp.get('discipline_name')}, class: {comp.get('race_class_name')})",
                file=sys.stdout,
            )
            fmt_record = (
                sql.find_category_format_by_id(comp.get('category_format_id')) if isinstance(comp, dict) else None
            )
            fmt_name = fmt_record.get('name') if fmt_record else None
        #elif category_format:
        #    fmt_name = category_format
        #    fmt, categories = sql.find_categories_for_format_name(category_format)
        #    if not fmt:
        #        print(f"Error: category_format '{category_format}' not found", file=sys.stderr)
        #        sys.exit(1)
        #    print(f"Using categories from format '{fmt.get('name')}'", file=sys.stdout)
        else:
            print("Error: must specify either --start_date or --category_format", file=sys.stderr)
            sys.exit(1)
        print(f"Categories: {categories}", file=sys.stdout)

        # Optionally show a quick summary of fetched categories
        if categories:
            codes = [ (c.get('code'), c.get('gender')) for c in categories ]
            print(f"Loaded {len(categories)} categories: {codes}", file=sys.stdout)

        ccn = GetCCN()

        # Instantiate organizer category alias map for the selected format
        catmap = CatMap(fmt_name) if fmt_name else None

        # Optionally show configured alias mappings
        if categories and catmap:
            for k, v in catmap.map.items():
                print(f"  Alias: '{k}' => '{v}'", file=sys.stdout)

        bikereg = GetBikeReg(
            racedb=racedb,
            sql=sql,
            ccn=ccn,
            catmap=catmap,
            comp=comp,
            username=username,
            password=password,
            csvfile=csvfile,
        )
        # Provide allowed category codes for purchase detection
        if categories:
            bikereg.allowed_codes = {c.get('code') for c in categories if isinstance(c, dict) and c.get('code')}
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')
        gprint('0. ---------------------------------')

    #if False:
    #    os.environ['LESS'] += f"--quit-if-one-screen"

    # 1. Process the BikeReg CSV file
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. Processing BikeReg CSV file:', csvfile, file=sys.stdout)
        gprint('1. ---------------------------------')
        bikereg.process_bikereg()
        gprint('1. ---------------------------------')
        gprint('1. Finished Processing BikeReg CSV file:', csvfile, file=sys.stdout)
        gprint('1. ---------------------------------')

    #exit()
    # 2. Process the registrations
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. Processing Registrations:', csvfile, file=sys.stdout)
        gprint('2. ---------------------------------')
        bikereg.process_registrations()
        gprint('2. ---------------------------------')
        gprint('2. Finished Processing Registrations:', csvfile, file=sys.stdout)
        gprint('2. ---------------------------------')

    #exit()
    # XXX
    #exit()
    # #3. Upload the license holders
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. Uploading License Holders', file=sys.stdout)
        gprint('3. ---------------------------------')
        racedb.upload_license_holders()
        gprint('3. ---------------------------------')
        gprint('3. Finished Uploading License Holders', csvfile, file=sys.stdout)
        gprint('3. ---------------------------------')
        #upload.login_and_upload()

    # 4. Create a new competition using older date as template
    if template_date:
        with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
            gprint('4. ---------------------------------')
            gprint('4. ---------------------------------')
            gprint('4. ---------------------------------')
            gprint('4. Finding Competition', file=sys.stdout)
            gprint('4. ---------------------------------')
            create_competition_from_template(sql=sql, racedb=racedb, template_date=template_date, start_date=start_date, new_name=new_name, replace=True, bib=bib)
            gprint('4. ---------------------------------')
            gprint('4. Copying Competition', file=sys.stdout)
            gprint('4. ---------------------------------')
            gprint('4. Finished Copying Competition', file=sys.stdout)
            gprint('4. ---------------------------------')
            #upload.login_and_upload()


    # 5. Upload the registrations
    if start_date:
        with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
            gprint('5. ---------------------------------')
            gprint('5. ---------------------------------')
            gprint('5. ---------------------------------')
            gprint('5. Uploading Registrations', file=sys.stdout)
            gprint('5. ---------------------------------')
            try:
                print(f"Looking for competition with start date: {start_date}")
                competition = sql.find_competition(new_name, start_date)
            except TypeError as e:
                print(f"Competition not found start date: {start_date}")
                exit(1)

            print('5. competition:', competition, file=sys.stdout)
            #upload_prereg(racedb, competition['id'], csvfile)
            racedb.upload_registrations(competition['id'], upload=True, bibs=bibs)
            gprint('5. ---------------------------------')
            gprint('5. Finished Uploading Registrations', file=sys.stdout)
            gprint('5. ---------------------------------')
            #upload.login_and_upload()
    else:
        # Just create the registratiuons.xlsx file
        racedb.upload_registrations(None, upload=False)

if __name__ == "__main__":
    main()
    exit(0)
