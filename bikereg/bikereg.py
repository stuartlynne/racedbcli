#!/usr/bin/env python3

import sys
import os
import io
import json
import csv
import re
import autopage, argparse
from enum import Enum
import traceback
#import argparse
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
import time
from datetime import datetime, timezone
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
    LOGIN_URL_CANDIDATES = [
        "https://www.bikereg.com/api/director/PromoterLogin?escaped=false",
        "https://www.bikereg.com/api/director/PromoterLogin",
    ]
    REG_URL = "https://www.bikereg.com/api/director/EventEntries?escaped=false"
    CSV_HEADERS = [
        "Last Name",
        "First Name",
        "Gender",
        "Date of Birth",
        "UCI Code",
        "Category Entered",
        "Team",
        "Phone",
        "Email",
        "Emergency Phone",
        "State",
        "City",
        "ZIP",
        "Emergency Contact",
        "Transaction Type",
        "MerchSummary",
    ]
    TRANSACTION_LABEL_MAP = {"0": "Reg", "1": "Merch", "Reg": "Reg", "Merch": "Merch"}

    def __init__(
        self,
        racedb=None,
        ccn=None,
        sql=None,
        catmap=None,
        comp=None,
        username=None,
        password=None,
        csvfile=None,
        event_id=None,
        bikereg_username=None,
        bikereg_password=None,
        discipline=None,
    ):
        self.racedb = racedb
        self.ccn = ccn
        self.sql = sql
        self.catmap = catmap
        self.comp = comp
        self.username = username
        self.password = password
        self.csvfile = csvfile
        self.event_id = event_id
        self.source_label = csvfile
        if event_id is not None:
            self.csvfile = self.fetch_event_to_temp_csv(
                event_id=event_id,
                username=bikereg_username,
                password=bikereg_password,
            )
            self.source_label = f"event_id={event_id}"
        self.bikeregcsv = BikeRegCSV(self.csvfile)
        self.registrations = []
        self.discipline = discipline

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

    @staticmethod
    def format_dob(value):
        if value in (None, ""):
            return ""
        s = str(value).strip()
        m = re.match(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$", s)
        if m:
            try:
                dt = datetime.fromtimestamp(int(m.group(1)) / 1000.0, tz=timezone.utc)
                return f"{dt.month}/{dt.day}/{dt.year}"
            except (ValueError, OSError):
                return s
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return f"{dt.month}/{dt.day}/{dt.year}"
        except ValueError:
            pass
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
        if m:
            return f"{int(m.group(1))}/{int(m.group(2))}/{m.group(3)}"
        return s

    @staticmethod
    def clean_text(v):
        if v in (None, ""):
            return ""
        s = str(v).strip()
        s = s.replace("\u00a0", "&nbsp;")
        s = re.sub(r"&(?!#?[a-zA-Z0-9]+;)", "&amp;", s)
        return s

    def _api_login(self, session, username, password, timeout=15):
        creds = {"username": username, "password": password}
        for login_url in self.LOGIN_URL_CANDIDATES:
            response = session.post(login_url, json=creds, timeout=timeout)
            print(f"BikeReg login URL: {login_url} -> {response.status_code}", file=sys.stderr)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                continue
            login_data = payload.get("PromoterLoginV2Result") or payload.get("PromoterLoginResult") or payload
            if isinstance(login_data, dict):
                token = login_data.get("authToken") or login_data.get("token")
                if token:
                    return token
        raise RuntimeError("Could not obtain auth token from BikeReg API login endpoints.")

    @staticmethod
    def _extract_entries(payload):
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        def _extract_from_obj(obj):
            if isinstance(obj, list):
                return obj
            if isinstance(obj, str):
                try:
                    parsed = json.loads(obj)
                except ValueError:
                    return []
                return _extract_from_obj(parsed)
            if not isinstance(obj, dict):
                return []
            for nested_key in ("entries", "eventEntries", "rows", "items"):
                rows = _extract_from_obj(obj.get(nested_key))
                if rows:
                    return rows
            return []

        for key in (
            "EventEntriesV2Result",
            "EventEntriesResult",
            "GetEventEntriesV2Result",
            "GetEventEntriesResult",
            "eventEntries",
            "entries",
            "result",
        ):
            rows = _extract_from_obj(payload.get(key))
            if rows:
                return rows
        for key, value in payload.items():
            if key.lower().endswith("result"):
                rows = _extract_from_obj(value)
                if rows:
                    return rows
        return []

    @staticmethod
    def _is_removed_registration(row):
        category = str(row.get("CategoryName", "")).strip().lower()
        return category == "removed registration"

    def _get_entry_key_info(self, row):
        user_info = row.get("UserInfo") if isinstance(row.get("UserInfo"), dict) else {}
        return {
            "confirmation": str(row.get("ConfirmationNumber", "")).strip(),
            "eid": str(row.get("EID", "")).strip(),
            "race_id": str(row.get("RaceID", "")).strip(),
            "identity": (
                str(user_info.get("LastName", "")).strip().lower(),
                str(user_info.get("FirstName", "")).strip().lower(),
                str(user_info.get("DOB", "")).strip(),
                str(user_info.get("Email", "")).strip().lower(),
            ),
            "identity_weak": (
                str(user_info.get("LastName", "")).strip().lower(),
                str(user_info.get("FirstName", "")).strip().lower(),
                str(user_info.get("DOB", "")).strip(),
            ),
        }

    @staticmethod
    def _merch_item_text(row):
        category = str(row.get("CategoryName", "")).strip()
        qty = row.get("Quantity")
        try:
            qty_int = int(qty)
        except (TypeError, ValueError):
            qty_int = 1
        label = category or "Merch"
        return f"({qty_int}) {label}"

    @staticmethod
    def _parse_last_modified(row):
        value = row.get("LastModified")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return float("-inf")
            m = re.match(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$", v)
            if m:
                try:
                    return float(int(m.group(1)))
                except ValueError:
                    return float("-inf")
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp() * 1000.0
            except ValueError:
                return float("-inf")
        return float("-inf")

    def _choose_better_reg(self, existing, candidate):
        if self._is_removed_registration(existing) and not self._is_removed_registration(candidate):
            return candidate
        if not self._is_removed_registration(existing) and self._is_removed_registration(candidate):
            return existing
        if self._parse_last_modified(candidate) > self._parse_last_modified(existing):
            return candidate
        return existing

    def _row_to_csv_dict(self, row):
        user_info = row.get("UserInfo") if isinstance(row.get("UserInfo"), dict) else {}
        txn_raw = str(row.get("TransactionType", ""))
        txn_type = self.TRANSACTION_LABEL_MAP.get(txn_raw, txn_raw)
        return {
            "Last Name": self.clean_text(user_info.get("LastName", "")),
            "First Name": self.clean_text(user_info.get("FirstName", "")),
            "Gender": self.clean_text(user_info.get("Gender", "")),
            "Date of Birth": self.format_dob(user_info.get("DOB", "")),
            "UCI Code": self.clean_text(user_info.get("UCIID", "")),
            "Category Entered": self.clean_text(row.get("CategoryName", "")),
            "Team": self.clean_text(user_info.get("Team", "")),
            "Phone": self.clean_text(user_info.get("Phone", "")),
            "Email": self.clean_text(user_info.get("Email", "")),
            "Emergency Phone": self.clean_text(user_info.get("EmergencyContactPhone", "")),
            "State": self.clean_text(user_info.get("State", "")),
            "City": self.clean_text(user_info.get("City", "")),
            "ZIP": self.clean_text(user_info.get("ZIP", "")),
            "Emergency Contact": self.clean_text(user_info.get("EmergencyContactName", "")),
            "Transaction Type": txn_type,
            "MerchSummary": "",
        }

    def _merge_entries_for_csv(self, entries):
        reg_rows = {}
        reg_order = []
        merch_by_person = {}

        for row in entries:
            if not isinstance(row, dict):
                continue
            txn = self.TRANSACTION_LABEL_MAP.get(str(row.get("TransactionType", "")), str(row.get("TransactionType", "")))
            key_info = self._get_entry_key_info(row)
            person_key = ("identity",) + key_info["identity"]
            if txn == "Reg":
                if self._is_removed_registration(row):
                    continue
                if person_key not in reg_rows:
                    reg_rows[person_key] = row
                    reg_order.append(person_key)
                else:
                    reg_rows[person_key] = self._choose_better_reg(reg_rows[person_key], row)

        reg_by_confirmation = {}
        reg_by_eid = {}
        reg_by_race_id = {}
        reg_by_identity_weak = {}
        for person_key in reg_order:
            row = reg_rows[person_key]
            key_info = self._get_entry_key_info(row)
            if key_info["confirmation"]:
                reg_by_confirmation.setdefault(key_info["confirmation"], set()).add(person_key)
            if key_info["eid"]:
                reg_by_eid.setdefault(key_info["eid"], set()).add(person_key)
            if key_info["race_id"]:
                reg_by_race_id.setdefault(key_info["race_id"], set()).add(person_key)
            reg_by_identity_weak.setdefault(("identity_weak",) + key_info["identity_weak"], set()).add(person_key)

        for row in entries:
            if not isinstance(row, dict):
                continue
            txn = self.TRANSACTION_LABEL_MAP.get(str(row.get("TransactionType", "")), str(row.get("TransactionType", "")))
            if txn != "Merch":
                continue

            key_info = self._get_entry_key_info(row)
            candidates = []
            strong_person_key = ("identity",) + key_info["identity"]
            weak_person_key = ("identity_weak",) + key_info["identity_weak"]

            if strong_person_key in reg_rows:
                candidates = [strong_person_key]
            elif weak_person_key in reg_by_identity_weak and len(reg_by_identity_weak[weak_person_key]) == 1:
                candidates = list(reg_by_identity_weak[weak_person_key])
            elif key_info["eid"] and key_info["eid"] in reg_by_eid and len(reg_by_eid[key_info["eid"]]) == 1:
                candidates = list(reg_by_eid[key_info["eid"]])
            elif key_info["race_id"] and key_info["race_id"] in reg_by_race_id and len(reg_by_race_id[key_info["race_id"]]) == 1:
                candidates = list(reg_by_race_id[key_info["race_id"]])
            elif (
                key_info["confirmation"]
                and key_info["confirmation"] in reg_by_confirmation
                and len(reg_by_confirmation[key_info["confirmation"]]) == 1
            ):
                candidates = list(reg_by_confirmation[key_info["confirmation"]])

            if candidates:
                merch_by_person.setdefault(candidates[0], []).append(self._merch_item_text(row))

        merged = []
        for person_key in reg_order:
            out = self._row_to_csv_dict(reg_rows[person_key])
            out["MerchSummary"] = ", ".join(merch_by_person.get(person_key, []))
            merged.append(out)
        return merged

    def fetch_event_to_temp_csv(self, event_id, username, password):
        if not username or not password:
            raise ValueError(
                "BikeReg credentials are required with --event-id. "
                "Use --bikereg-username/--bikereg-password or env BIKEREG_USERNAME/BIKEREG_PASSWORD."
            )

        with requests.Session() as session:
            token = self._api_login(session, username, password)
            response = session.post(
                self.REG_URL,
                json={"token": token, "eventID": event_id},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, str):
                payload = json.loads(payload)
            entries = self._extract_entries(payload)
            merged_rows = self._merge_entries_for_csv(entries)

        path = os.path.abspath("bikereg_event.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(
            f"BikeReg API event {event_id}: wrote {len(merged_rows)} merged registration rows to {path}",
            file=sys.stdout,
        )
        return path

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

    def check_a_or_b(self, a, b):
        if a == b and a is not None:
            return True
        if (a is None) != (b is None):
            return True
        return False
        
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
            purchase = br.get('MerchSummary', None)
            self.racedb.add_purchase(first_name=first_name, last_name=last_name, purchase=purchase)

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
                yprint(f"  Found: {first_name} {last_name} {dob} {gender} in RaceDB and CCN", file=sys.stdout)
                uciIdFlag = not self.check_a_or_b(ccn_license_holders[0]["uci_id"], racedb_license_holders[0]["uci_id"] )
                licenseNumberFlag =  not self.check_a_or_b(ccn_license_holders[0]["license_number"], racedb_license_holders[0]["license_code"])
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
                yprint(f"  Found: {first_name} {last_name} {dob} {gender} in RaceDB", file=sys.stdout)
                br['license_number'] = racedb_license_holders[0]['license_code']
                br['uci_id'] = racedb_license_holders[0]['uci_id']
                br['license_check'] = False
            else:
                yprint(f"  NOT Found: {first_name} {last_name} {dob} {gender} in RaceDB or CCN", file=sys.stdout)
                br['license_check'] = False
                self.racedb.new_license_holder(first_name=first_name, last_name=last_name, gender=gender, dob=dob, msg='Not found')

            # If we cannot find the license holder in RaceDB, then we need to add them
            #if not ccn_license_holders and not racedb_license_holders:
            #    yprint(f"  Cannot find: {first_name} {last_name} {dob} {gender} in RaceDB or CCN", file=sys.stdout)
            #elif not racedb_license_holders:
            #    yprint(f"  Cannot find: {first_name} {last_name} {dob} {gender} in RaceDB", file=sys.stdout)
            #    self.racedb.new_license_holder(first_name=first_name, last_name=last_name, gender=gender, dob=dob, msg='Not found')

            # Normalize category label via per-format CatMap mapping
            #label = br['Category Entered / Merchandise Ordered']
            label = br['Category Entered']
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
            allowed_categories, licenses = self.catmap.get_event_category(license_categories=license_categories, gender=gender, 
                                                                          age=age, discipline=self.discipline) 
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
                                             note=f"Purchases {purchases}\nBR ALLOWED [{requested_category}]\nLicense: {licenses}",
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
    parser.add_argument('--event-id', '--event_id', type=int, default=None, help='BikeReg Event ID (fetch from API instead of --csvfile)')
    parser.add_argument('--bikereg-username', '--bikereg_username', type=str, default=os.getenv("BIKEREG_USERNAME"), help='BikeReg API username')
    parser.add_argument('--bikereg-password', '--bikereg_password', type=str, default=os.getenv("BIKEREG_PASSWORD"), help='BikeReg API password')
    parser.add_argument('--template-date', '--template_date', type=str, help='Copy the competition from this date.')
    parser.add_argument('--start-date', '--start_date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--category-format', '--category_format', type=str, help='CategoryFormat name (e.g., lmcx2018)')
    parser.add_argument('--new-name', '--new_name', type=str, help='Name of the competition.')
    parser.add_argument('--bibs', action='store_true', help='Generate bib numbers.')
    parser.add_argument('--stderr', "--debug", action='store_true', help='Enable stderr output.')
    parser.add_argument("--stderrdup", action='store_true', help='Send stderr to stdout.')
    parser.add_argument("--stop-after-bikereg", "--stop_after_bikereg", action='store_true', help='Stop of fetching bikereg data.')
    parser.add_argument("--stop-after-reg", "--stop_after_reg", action='store_true', help='Stop of registration parsing.')
    parser.add_argument("--stop-after-licenseholders", "--stop_after_licenseholders", action='store_true', help='Stop of license holder upload.')
    parser.add_argument("--cyclocross", action='store_true', help='Use cyclocross license data.')
    parser.add_argument("--road", action='store_true', help='Use road license data.')
    #parser.add_argument('--replace', action='store_true', help='Replace existing competition.')



    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    csvfile = args.csvfile         
    event_id = args.event_id
    template_date = args.template_date
    start_date = args.start_date
    category_format = args.category_format
    new_name = args.new_name
    bibs = args.bibs
    stop_after_bikereg = args.stop_after_bikereg
    stop_after_reg = args.stop_after_reg
    stop_after_licenseholders = args.stop_after_licenseholders
    road = args.road
    cyclocross = args.cyclocross
    if road and cyclocross:
        print("Error: cannot specify both --road and --cyclocross", file=sys.stderr)
        sys.exit(1)
    if not road and not cyclocross:
        road = True
    if csvfile and event_id is not None:
        print("Error: specify only one input source: --csvfile or --event-id", file=sys.stderr)
        sys.exit(1)
    if not csvfile and event_id is None:
        print("Error: must specify one input source: --csvfile or --event-id", file=sys.stderr)
        sys.exit(1)

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
            event_id=event_id,
            bikereg_username=args.bikereg_username,
            bikereg_password=args.bikereg_password,
            discipline='Cyclocross' if cyclocross else 'Road',  
        )
        source_label = bikereg.source_label
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
        gprint('1. Processing BikeReg input:', source_label, file=sys.stdout)
        gprint('1. ---------------------------------')
        bikereg.process_bikereg()
        gprint('1. ---------------------------------')
        gprint('1. Finished Processing BikeReg input:', source_label, file=sys.stdout)
        gprint('1. ---------------------------------')
    if stop_after_bikereg:
        exit()

    #exit()
    # 2. Process the registrations
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. ---------------------------------')
        gprint('2. Processing Registrations:', source_label, file=sys.stdout)
        gprint('2. ---------------------------------')
        bikereg.process_registrations()
        gprint('2. ---------------------------------')
        gprint('2. Finished Processing Registrations:', source_label, file=sys.stdout)
        gprint('2. ---------------------------------')

    if stop_after_reg:
        exit()

    # #3. Upload the license holders
    with AutoPagerEx(stderr=args.stderr, stderrdup=args.stderrdup, line_buffering=autopage.line_buffer_from_input()) as (sys.stdout, sys.stderr):
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. ---------------------------------')
        gprint('3. Uploading License Holders', file=sys.stdout)
        gprint('3. ---------------------------------')
        racedb.upload_license_holders()
        gprint('3. ---------------------------------')
        gprint('3. Finished Uploading License Holders', source_label, file=sys.stdout)
        gprint('3. ---------------------------------')
        #upload.login_and_upload()

    if stop_after_licenseholders:
        exit()

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
