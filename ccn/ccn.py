#!/usr/bin/env python3

import sys
import os

if __name__ == "__main__":
    # Prefer this repository's packages over unrelated installed packages.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import json
import autopage, argparse
import traceback
#import argparse
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
import time
from urllib.parse import urljoin
from libs.autopageex import AutoPagerEx
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL
from libs.ccn import GetCCN
# from libs.categorymap import CategoryMap  # legacy
from libs.catmap import CatMap
from libs.lib import gprint, yprint
from libs.ccncsv import CCNRegCSV
from libs.ccnpurchases import read_purchases, match_purchases
from libs.mcpconfig import load_mcp_host
from libs.uplifter import DEFAULT_REPORT, UplifterError, UplifterReports
from cli.competition import create_competition_from_template

# This script will process a ccnreg CSV file to load into RaceDB competition.
#
# 1. Process the ccnreg CSV file
# 2. Process the registrations
# 3. Upload the license holders
# 4. Create a new competition using older date as template
# 5. Upload the registrations
# 


class GetCCNReg:
    def __init__(self, racedb=None, ccn=None, sql=None, catmap=None, comp=None, username=None, password=None, csvfile=None):
        self.racedb = racedb
        self.ccn = ccn
        self.sql = sql
        self.catmap = catmap
        self.comp = comp
        self.username = username
        self.password = password
        self.csvfile = csvfile
        self.ccnregcsv = CCNRegCSV(csvfile)
        self.registrations = []
        self.source_registrations = []
        self.allowed_codes = None

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

        
    def process_ccncsv(self):
        for i, br in self.ccnregcsv.get_next():
            self.source_registrations.append(br)
            print(f"Processing[{i}]: {br}", file=sys.stderr)
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
                for i, licenseholder in enumerate(racedb_license_holders):
                    info = [ licenseholder[k] for k in ['last_name', 'first_name', 'license_code', 'uci_id',] ]
                    print(f"  RaceDB[{i}] {info} {by}", file=sys.stdout)



            #if racedb_license_holders:
            #    racedb_license_holder = racedb_license_holders[0]

            ccn_license_holders = self.ccn.get_license_holders(first_name, last_name, )
            if ccn_license_holders and len(ccn_license_holders) == 1:
                ccn_license_holder = ccn_license_holders[0]
                print('  CCN License Holder:', ccn_license_holder, file=sys.stderr)
                licenses = ccn_license_holder['licenses']
                road = licenses.get('Road', None)
                cyclocross = licenses.get('Cyclocross', None)
                print(f'  CCN: {ccn_license_holder["uci_id"]} {ccn_license_holder["license_number"]} {road} {cyclocross}', file=sys.stdout)
                license_categories = ccn_license_holder['licenses']
            else:
                license_categories = {}

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
            else:
                br['license_check'] = False

            # If we cannot find the license holder in RaceDB, then we need to add them
            if not ccn_license_holders and not racedb_license_holders:
                yprint(f"  Cannot find: {first_name} {last_name} {dob} {gender} in RaceDB or CCN", file=sys.stdout)
                self.racedb.new_license_holder(first_name=first_name, last_name=last_name, gender=gender, dob=dob, msg='Not found')

            # Normalize category with CatMap; treat unknowns as purchases
            label = br.get('Category', None)
            canonical = label
            if self.catmap and isinstance(label, str):
                entry = self.catmap.lookup_label(label)
                if entry and isinstance(entry, (list, tuple)) and entry:
                    canonical = entry[0]

            if self.allowed_codes and canonical not in self.allowed_codes:
                print('  Purchased: %s' % (canonical), file=sys.stdout)
                self.racedb.add_purchase(first_name=first_name, last_name=last_name, purchase=canonical)
                continue

            br['requested_category'] = canonical
            print(f"  Category: {label} -> requested: {canonical}", file=sys.stderr)
            self.registrations.append(br)

            #print('Category entered: %s' % br['Category Entered / Merchandise Ordered'], file=sys.stdout)
            #if i > 20:
            #    break

        print()
        print()
        print()

    def process_registrations(self, purchase_notes=None):

        for i, br in enumerate(self.registrations):

            print('[{i}]-----------------------------------')
            #print('br:', br, file=sys.stderr)

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
            requested_category = br.get('requested_category', br.get('Category'))
            license_type = br.get('license_type', None)
            license_check = br.get('license_check', False)
            purchases = self.racedb.purchases.get((last_name, first_name), [])
            kmh = None

            print(f"Processing[{i}]: {last_name}, {first_name}, {dob}, {gender},", file=sys.stdout)
            #print(f"  Age: {age} Purchases: {purchases}", file=sys.stdout)

            print(f"  License_categories: {license_categories}", file=sys.stderr)
            if license_categories:
                licenses = license_categories.get('Road', None)
                #cyclocross = license_categories.get('Cyclocross', None)
                #print(f'  CCN Licenses: Road: {road} Cyclocross: {cyclocross}', file=sys.stderr)
            else:
                licenses = []

            #allowed_categories, licenses = self.catmap.get_event_category(license_categories, gender, age, )
            #print('  Allowed Categories:', allowed_categories, file=sys.stderr)
            print('  Licenses:', licenses, file=sys.stderr)
            print(f"  Requested: {requested_category}", file=sys.stderr)

            if isinstance(requested_category, str) and requested_category.startswith("Time Trial"):
                kmh = self.catmap.estimate_tt_kmh(
                    license_categories=license_categories,
                    gender=gender,
                    discipline='Road',
                ) if self.catmap else None
                print(f"  TT kmh estimate: {kmh}", file=sys.stderr)

            print('  Requested [%s] CATEGORY ALLOWED' % (requested_category), file=sys.stderr)
            note=f"ALLOWED [{requested_category}] LICENSE {licenses}"
            if purchases and len(purchases) > 0:
                note = f"PURCHASED [{', '.join(purchases)}] {note}"
            product_notes = (purchase_notes or {}).get(br.get('Reg ID'), [])
            if product_notes:
                note = f"{'; '.join(product_notes)}; {note}"
            self.racedb.add_registration(first_name=first_name, last_name=last_name, uci_id=uci_id, gender=gender,
                                         dob=dob,
                                         category=requested_category, license_number=license_number, 
                                         license_type=license_type, license_check=license_check, kmh=kmh,
                                         note=note,
                                         allowed=True,
                                         waiver=False)



epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""
def main():
    parser = argparse.ArgumentParser(description="RaceDB update license holders from xlsx.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--csvfile', type=str, default=None, help='CCN CSV file')
    parser.add_argument('--event-id', '--event_id', help='Uplifter event id; downloads the CCN registration CSV.')
    parser.add_argument('--event-name', '--event_name', help='Exact Uplifter event name; downloads the CCN registration CSV.')
    parser.add_argument('--uplifter-env-file', default='.ccn.env', help='Uplifter credentials env file.')
    parser.add_argument('--uplifter-username', default=os.getenv("CCN_LOGIN") or os.getenv("LOGIN"), help='Uplifter login username.')
    parser.add_argument('--uplifter-password', default=os.getenv("CCN_PASSWORD") or os.getenv("PASSWORD"), help='Uplifter login password.')
    parser.add_argument('--uplifter-report', default=DEFAULT_REPORT, help='Uplifter report name to download.')
    parser.add_argument('--uplifter-output', default='ccn_event.csv', help='Downloaded Uplifter CSV output path.')
    parser.add_argument('--purchases-csv', help='Purchased Products report to accompany --csvfile.')
    parser.add_argument('--uplifter-purchases-output', default='ccn_purchases.csv', help='Downloaded Uplifter purchases CSV output path.')
    parser.add_argument('--uplifter-update', action='store_true', help='Regenerate registration and purchase reports before downloading.')
    parser.add_argument('--uplifter-timeout', type=int, default=300, help='Seconds to wait for --uplifter-update.')
    parser.add_argument('--template_date', type=str, help='Copy the competition from this date.')
    parser.add_argument('--start_date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--new_name', type=str, help='Name of the competition.')
    parser.add_argument('--category_format', type=str, help='CategoryFormat name (e.g., lmcx2018)')
    parser.add_argument('--bibs', action='store_true', help='Generate bib numbers.')
    parser.add_argument('--teams', action='store_true', help='Update participants team.')
    parser.add_argument('--waiver', action='store_true', help='Mark waivers as signed in registration upload.')
    parser.add_argument('--stderr', "--debug", action='store_true', help='Enable stderr output.')
    parser.add_argument("--stderrdup", action='store_true', help='Send stderr to stdout.')
    parser.add_argument("--mcp-host", "--mcp_host", help='Named host in ~/.mcp.json; sets --host and --mcp-url.')
    parser.add_argument("--mcp-url", "--mcp_url", default=os.getenv("RACEDB_MCP_URL"), help='RaceDB MCP streamable HTTP URL for direct registration upsert.')
    parser.add_argument("--mcp-token", "--mcp_token", default=os.getenv("RACEDB_MCP_TOKEN") or os.getenv("CONTEXTFORGE_TOKEN"), help='Bearer token for RaceDB MCP, if required.')
    parser.add_argument("--mcp-dry-run", "--mcp_dry_run", action='store_true', help='Dry-run direct MCP registration upserts.')
    #parser.add_argument('--replace', action='store_true', help='Replace existing competition.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    explicit_mcp_url = any(arg == "--mcp-url" or arg == "--mcp_url" or arg.startswith("--mcp-url=") or arg.startswith("--mcp_url=") for arg in sys.argv[1:])
    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    csvfile = args.csvfile         
    template_date = args.template_date
    start_date = args.start_date
    new_name = args.new_name
    bibs = args.bibs

    if args.mcp_host:
        try:
            mcp_config = load_mcp_host(args.mcp_host)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        host = mcp_config["racedb_url"]
        if not explicit_mcp_url:
            args.mcp_url = mcp_config.get("mcp_url")
        print(f"Using MCP host [{args.mcp_host}]: racedb_url={host} mcp_url={args.mcp_url}", file=sys.stderr)

    ccn_event_sources = [bool(csvfile), bool(args.event_id), bool(args.event_name)]
    if sum(ccn_event_sources) != 1:
        print("Error: specify exactly one input source: --csvfile, --event-id, or --event-name", file=sys.stderr)
        sys.exit(1)

    purchases_csv = args.purchases_csv
    if purchases_csv and not args.csvfile:
        parser.error('--purchases-csv requires --csvfile; event downloads fetch purchases automatically')
    if (args.event_id or args.event_name) and os.path.abspath(args.uplifter_output) == os.path.abspath(args.uplifter_purchases_output):
        parser.error('Registration and purchase report output paths must differ')

    if args.event_id or args.event_name:
        try:
            uplifter = UplifterReports(
                username=args.uplifter_username,
                password=args.uplifter_password,
                env_file=args.uplifter_env_file,
            )
            csvfile, event_info, _, _ = uplifter.fetch_registration_report(
                event_id=args.event_id,
                event_name=args.event_name,
                report=args.uplifter_report,
                file_format='csv',
                output=args.uplifter_output,
                update=args.uplifter_update,
                timeout_seconds=args.uplifter_timeout,
            )
            csvfile = str(csvfile)
            purchases_csv = uplifter.fetch_purchase_report(
                event_info['event_id'], output=args.uplifter_purchases_output,
                update=args.uplifter_update, timeout_seconds=args.uplifter_timeout,
            )
            print(
                f"Uplifter event {event_info['event_id']}: wrote registration CSV to {csvfile}",
                file=sys.stderr,
            )
        except UplifterError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        product_purchases = list(read_purchases(purchases_csv)) if purchases_csv else []
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    #host = host.removeprefix("https://").removeprefix("http://").split(":")[0]

    sql = RaceDBSQL(host)
    racedb = RaceDB(host=host, username=username, password=password,)

    # Determine categories from either start_date (competition) or category_format
    categories = []
    fmt_name = None
    comp = None
    if start_date:
        comp, categories = sql.find_competition_categories(date=start_date)
        if not comp:
            print(f"Error: competition not found for start_date {start_date}", file=sys.stderr)
            sys.exit(1)
        fmt_record = sql.find_category_format_by_id(comp.get('category_format_id')) if isinstance(comp, dict) else None
        fmt_name = fmt_record.get('name') if fmt_record else None
    elif args.category_format:
        fmt_name = args.category_format
        fmt, categories = sql.find_categories_for_format_name(fmt_name)

    # Instantiate CatMap for selected format (if any)
    catmap = CatMap(fmt_name) if fmt_name else None

    ccn = GetCCN()

    ccnreg = GetCCNReg(racedb=racedb, sql=sql, ccn=ccn, catmap=catmap, comp=comp, username=username, password=password, csvfile=csvfile)
    if categories:
        ccnreg.allowed_codes = {c.get('code') for c in categories if isinstance(c, dict) and c.get('code')}

    #if False:
    #    os.environ['LESS'] += f"--quit-if-one-screen"

    # 1. Process the ccnreg CSV file
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. ---------------------------------')
        gprint('1. Processing ccnreg CSV file:', csvfile, file=sys.stdout)
        gprint('1. ---------------------------------')
        ccnreg.process_ccncsv()
        purchase_notes, purchase_warnings = match_purchases(ccnreg.source_registrations, product_purchases)
        print(f"Uplifter purchases: {len(product_purchases)} product rows, "
              f"{len(purchase_notes)} registration rows annotated, "
              f"{len(purchase_warnings)} unmatched/ambiguous rows", file=sys.stderr)
        for warning in purchase_warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        gprint('1. ---------------------------------')
        gprint('1. Finished Processing ccnreg CSV file:', csvfile, file=sys.stdout)
        gprint('1. ---------------------------------')

    # 2. Process the registrations
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. Processing Registrations:', csvfile, file=sys.stdout)
        gprint('2. ---------------------------------')
        ccnreg.process_registrations(purchase_notes=purchase_notes)
        gprint('2. ---------------------------------')
        gprint('2. Finished Processing Registrations:', csvfile, file=sys.stdout)
        gprint('2. ---------------------------------')

    # XXX
    # #3. Upload the license holders
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. Uploading License Holders', file=sys.stdout)
        gprint('3. ---------------------------------')
        # XXX
        #racedb.upload_license_holders(teams=teams)
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
            racedb.upload_registrations(
                competition['id'],
                upload=True,
                bibs=bibs,
                teams=args.teams,
                waiver=args.waiver,
                mcp_url=args.mcp_url,
                mcp_token=args.mcp_token,
                mcp_dry_run=args.mcp_dry_run,
            )
            gprint('5. ---------------------------------')
            gprint('5. Finished Uploading Registrations', file=sys.stdout)
            gprint('5. ---------------------------------')
            #upload.login_and_upload()
    else:
        # Just create the registratiuons.xlsx file
        racedb.upload_registrations(None, upload=False, waiver=args.waiver)

if __name__ == "__main__":
    main()
    exit(0)
