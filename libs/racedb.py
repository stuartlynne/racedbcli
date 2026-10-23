#!/usr/bin/env python3

import sys
import os
import io
import json
import csv
import asyncio
import pandas as pd
from libs.login import session_login
from libs.lib import yprint
import xlsxwriter
from libs.createxlsx import create_xlsx_file
from bs4 import BeautifulSoup
from urllib.parse import urljoin

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from libs.download import download_file
from libs.upload import upload_file
from libs.savefile import save_file


def _bool_value(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _gender_name(value):
    if value in (0, "0"):
        return "Men"
    if value in (1, "1"):
        return "Women"
    if value in (2, "2"):
        return "Open"
    if value is None:
        return None
    text = str(value).strip()
    if text.upper().startswith("M"):
        return "Men"
    if text.upper().startswith(("F", "W")):
        return "Women"
    return text or None

class RaceDB:

    LicenseHolderHeaders = { 
                            "Last Name": 20, 
                            "First Name": 20, 
                            "License": 20, 
                            "UCI ID": 20, 
                            "DOB": 20, 
                            "Gender": 4, 
                            "Team": 20, 
                            "Road Team": 20, 
                            "Cyclocross Team": 20, 
                            "Note": 40, 
                            "Comments": 20
                            }
    RegistrationHeaders = { 
                           "Last Name": 20, 
                           "First Name": 20, 
                           "DOB": 12, 
                           "Gender": 5, 
                           "Age": 5, 
                           "UCI ID": 10, 
                           "License Check": 6, 
                           "License": 10, 
                           "Category": 20, 
                           "kmh": 6,
                           "Paid": 5,
                           "Waiver": 5,
                           "Note": 40, 
                           "Comments": 20,
                           }
    def __init__(self, host=None, username=None, password=None, ): 
        self.base_url = host
        self.username = username
        self.password = password
        self.license_holder_data = []
        self.purchases = {}
        self.purchase_counts = {}
        self.registration_data = []
        self.stats = {
                'registrations': 0,
                'license_check': 0,
                'license_missing': 0,
                'allowed': 0,
                'uci_id': 0,
                'men': 0,
                'women': 0,
                'unknown': 0,
                'tbd_category': 0,
        }
        print('RaceDB:', self.base_url, self.username, self.password, file=sys.stdout)
        self.session = session_login(self.base_url, self.username, self.password)



    def add_purchase(self, first_name=None, last_name=None, purchase=None):
        lastfirst = (last_name, first_name)
        if lastfirst not in self.purchases:
            self.purchases[lastfirst] = []
        self.purchases[lastfirst].append(purchase)
        purchase_key = str(purchase).strip() if purchase is not None else ""
        if purchase_key:
            self.purchase_counts[purchase_key] = self.purchase_counts.get(purchase_key, 0) + 1
        print(f"  Adding purchase for {first_name} {last_name}: {self.purchases[lastfirst]}", file=sys.stdout)
    def get_purchases(self, first_name=None, last_name=None):
        lastfirst = (last_name, first_name)
        return self.purchases.get(lastfirst, [])

    def append_license_holders_data(self, first_name=None, last_name=None, uci_id=None, license_number=None, 
                                    license_check=False, team=None, dob=None, gender='M', note=None, comments=None):
        self.license_holder_data.append({
            'Last Name': last_name,
            'First Name': first_name,
            'License': license_number,
            'License Check': license_check,
            'UCI ID': uci_id,
            'DOB': dob,
            'Gender': gender,
            'Team': team,
            'Road Team': team,
            'Cyclocross Team': team,
            'Note': note,
            'Comments': comments,
        })
        print('License holder data: ', self.license_holder_data[-1], file=sys.stderr)

    # create new license holder, DoB jan 1, Year based on age from CCN, gender male
    #def new_license_holder(self, first_name, last_name, uci_id, license_number, team):
    def new_license_holder(self, first_name=None, last_name=None, uci_id=None, dob=None, gender=None, age=25, license_number=None, team=None, msg=None):
        yprint(f"  RaceDB: will add {first_name} {last_name} {dob} - {msg}", file=sys.stdout)
        #if person:
        #    license_number = person["license_number"]
        #    team = person["team"]
        fixflag = False
        if not dob:
            dob = f"{2025 - age}-01-01"
            fixflag = True
        if not gender:
            gender = "M"
            fixflag = True
        self.append_license_holders_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                 license_number=license_number, team=team, dob=dob, gender=gender,
                 comments="New license holder", note="FIX AGE AND GENDER!" if fixflag else "")

    # update license holder with new data based on last, first names and DoB
    def update_license_holder(self, first_name=None, last_name=None, dob=None, gender=None, uci_id=None, license_number=None, team=None, msg=None):
        yprint(f"  Racedb: will update {first_name} {last_name} {uci_id} {license_number} - {msg}", file=sys.stdout)
        self.append_license_holders_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                         license_number=license_number, team=team, dob=dob, gender=gender, comments=f"Update {msg}")

    def create_license_holders_xlsx_file(self, data, file_path=None):
        create_xlsx_file(file_path, self.LicenseHolderHeaders, data)


    def create_license_holders_xlsx_in_memory(self, data, teams=False):
        output = io.BytesIO()
        df = pd.DataFrame(data, columns=self.LicenseHolderHeaders)
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def upload_license_holders(self, teams=False):

        print(f"License holder teams: {teams}", file=sys.stderr)
        print('License holder data:', self.license_holder_data, file=sys.stderr)
        if True:
            xlsx_file = self.create_license_holders_xlsx_file(self.license_holder_data, file_path="license_holders.xlsx")

        xlsx_file = self.create_license_holders_xlsx_in_memory(self.license_holder_data, teams=teams)

        next_path = "RaceDB/LicenseHolders/LicenseHoldersImportExcel/"

        self.upload_file(next_path, tableCheck=True, 
            #files= { 'excel_file': open(file_path, 'rb'), },
            #files={'excel_file': ('license_holders.xlsx', xlsx_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "set_team_all_disciplines": "on",
                "update_license_codes": "2",
                "ok-submit": "OK",
            },)

    def add_registration(self, first_name=None, last_name=None, dob=None, uci_id=None, license_number=None, license_check=False, 
                         gender=None, license_type=None, category=None, kmh=None, note=None, allowed=False, waiver=True):
        self.registration_data.append({
            'First Name': first_name,
            'Last Name': last_name,
            'DOB': dob,
            'License': license_number,
            'License Check': license_check,
            'UCI ID': uci_id,
            'Gender': gender,
            'kmh': kmh,
            'Paid': 'true',
            'Waiver': 'true' if _bool_value(waiver) else 'false',
            'Note': note,
            'Category': category,
        })
        self.stats['registrations'] += 1
        self.stats['license_check'] += 1 if license_check else 0
        self.stats['license_missing'] += 1 if not license_number or license_number == "" else 0
        self.stats['allowed'] += 1 if allowed else 0
        self.stats['uci_id'] += 1 if uci_id and uci_id != "" else 0
        self.stats['men'] += 1 if gender == 'M' else 0
        self.stats['women'] += 1 if gender == 'F' else 0
        self.stats['unknown'] += 1 if gender not in['M', 'F'] else 0
        self.stats['tbd_category'] += 1 if category == 'TBD' else 0
        if license_check:
            print('  Registration data: %s' % (
                [self.registration_data[-1][k] for k in ['First Name', 'Last Name', 'License', 'License Check', 
                 'UCI ID', 'Category', 'Note']]), 
                  file=sys.stdout)
        else:
            yprint('  Registration data: %s' % (
                [self.registration_data[-1][k] for k in ['First Name', 'Last Name', 'License', 'License Check', 
                 'UCI ID', 'Category', 'Note']]), 
                  file=sys.stdout)
        pass

    def create_registrations_xlsx_file(self, data, file_path=None, teams=False):
        registration_headers = self.RegistrationHeaders.copy()
        if teams:
            registration_headers['Team'] = 20
        create_xlsx_file(file_path, registration_headers, data)


    def create_registrations_xlsx_in_memory(self, data, teams=False):
        output = io.BytesIO()
        registration_headers = self.RegistrationHeaders.copy()
        if teams:
            registration_headers['Team'] = 20
        df = pd.DataFrame(data, columns=registration_headers)
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def create_unknowns_csv_file(self, file_path=None):
        file_path = file_path or "unknowns.csv"
        unknown_rows = [row for row in self.registration_data if row.get('Category') == 'TBD']
        fieldnames = list(self.RegistrationHeaders.keys())
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in unknown_rows:
                clean_row = {}
                for k in fieldnames:
                    value = row.get(k, '')
                    if isinstance(value, str):
                        value = value.replace('\r\n', ' | ').replace('\n', ' | ').replace('\r', ' | ')
                    clean_row[k] = value
                writer.writerow(clean_row)
        return file_path

    async def _mcp_call_tool(self, mcp_url, tool_name, arguments, mcp_token=None):
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as e:
            raise RuntimeError("MCP support requires `pip install mcp`") from e

        headers = {}
        if mcp_token:
            headers["Authorization"] = f"Bearer {mcp_token}"

        async with streamablehttp_client(mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)

    async def _mcp_sql_query(self, mcp_url, sql, mcp_token=None, limit=1000):
        result = await self._mcp_call_tool(
            mcp_url,
            "sql.query",
            {"sql": sql, "limit": limit},
            mcp_token=mcp_token,
        )
        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
        return {}

    def _mcp_result_json(self, result):
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return structured
        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
        return {}

    async def _mcp_sql_query_session(self, session, sql, limit=1000):
        result = await session.call_tool(
            "sql.query",
            arguments={"sql": sql, "limit": limit},
        )
        return self._mcp_result_json(result)

    async def _mcp_category_ids(self, mcp_url, competition_id, mcp_token=None):
        sql = f"""
            select c.id, c.code, c.gender, c.description
            from core_category c
            join core_competition comp on comp.category_format_id = c.format_id
            where comp.id = {int(competition_id)}
            order by c.sequence, c.id
        """
        data = await self._mcp_sql_query(mcp_url, sql, mcp_token=mcp_token)
        lookup = {}
        for row in data.get("rows", []):
            code = row.get("code")
            if code is None:
                continue
            lookup.setdefault(code, []).append(row)
        return lookup

    async def _mcp_category_ids_session(self, session, competition_id):
        sql = f"""
            select c.id, c.code, c.gender, c.description
            from core_category c
            join core_competition comp on comp.category_format_id = c.format_id
            where comp.id = {int(competition_id)}
            order by c.sequence, c.id
        """
        data = await self._mcp_sql_query_session(session, sql)
        lookup = {}
        for row in data.get("rows", []):
            code = row.get("code")
            if code is None:
                continue
            lookup.setdefault(code, []).append(row)
        return lookup

    def _select_mcp_category_id(self, category_lookup, category, gender):
        rows = category_lookup.get(category) or []
        if not rows:
            return None
        gender_code = 2
        if _gender_name(gender) == "Men":
            gender_code = 0
        elif _gender_name(gender) == "Women":
            gender_code = 1

        for row in rows:
            if row.get("gender") == gender_code:
                return row.get("id")
        for row in rows:
            if row.get("gender") == 2:
                return row.get("id")
        return rows[0].get("id")

    async def _upload_registrations_mcp_async(self, competition_id, mcp_url, mcp_token=None, bibs=False, dry_run=False):
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as e:
            raise RuntimeError("MCP support requires `pip install mcp`") from e

        headers = {}
        if mcp_token:
            headers["Authorization"] = f"Bearer {mcp_token}"

        stats = {
            "processed": 0,
            "created": 0,
            "changed": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
        }

        async with streamablehttp_client(mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                clear_result = await session.call_tool(
                    "competition.participants_clear",
                    arguments={
                        "competition_id": int(competition_id),
                        "dry_run": bool(dry_run),
                        "confirm": not bool(dry_run),
                    },
                )
                clear_data = self._mcp_result_json(clear_result)
                if getattr(clear_result, "isError", False):
                    raise RuntimeError(f"MCP participants clear failed: {clear_data or clear_result}")
                print(f"MCP participants clear {'dry-run ' if dry_run else ''}result: {clear_data}", file=sys.stderr)

                category_lookup = await self._mcp_category_ids_session(session, competition_id)

                for i, row in enumerate(self.registration_data):
                    category_id = self._select_mcp_category_id(category_lookup, row.get("Category"), row.get("Gender"))
                    if not category_id:
                        stats["skipped"] += 1
                        print(f"[{i}] MCP registration skipped, cannot find category: {row.get('Category')} {row.get('First Name')} {row.get('Last Name')}", file=sys.stderr)
                        continue

                    license_holder = {
                        "first_name": row.get("First Name"),
                        "last_name": row.get("Last Name"),
                        "gender": _gender_name(row.get("Gender")),
                        "date_of_birth": row.get("DOB"),
                        "license_code": row.get("License"),
                        "uci_id": row.get("UCI ID"),
                    }
                    participant_fields = {
                        "paid": _bool_value(row.get("Paid")),
                        "preregistered": True,
                        "confirmed": _bool_value(row.get("Waiver")),
                        "waiver": _bool_value(row.get("Waiver")),
                        "license_checked": _bool_value(row.get("License Check")),
                        "note": row.get("Note") or "",
                    }
                    if row.get("kmh") not in (None, ""):
                        participant_fields["est_kmh"] = row.get("kmh")

                    print(f"[{i}] MCP registration: {row.get('First Name')} {row.get('Last Name')} category={row.get('Category')} category_id={category_id} license={row.get('License')} uci_id={row.get('UCI ID')}", file=sys.stdout)

                    arguments = {
                        "competition_id": int(competition_id),
                        "license_holder": license_holder,
                        "category_id": int(category_id),
                        "participant_fields": participant_fields,
                        "auto_bib": bool(bibs),
                        "dry_run": bool(dry_run),
                    }
                    try:
                        result = await session.call_tool("participant.registration_upsert", arguments=arguments)
                    except Exception as e:
                        stats["failed"] += 1
                        print(
                            f"[{i}] MCP registration failed: {row.get('First Name')} {row.get('Last Name')} "
                            f"category={row.get('Category')} category_id={category_id}: {e}",
                            file=sys.stderr,
                        )
                        continue

                    stats["processed"] += 1
                    data = self._mcp_result_json(result)
                    if getattr(result, "isError", False):
                        stats["failed"] += 1
                        print(
                            f"[{i}] MCP registration error: {row.get('First Name')} {row.get('Last Name')} "
                            f"category={row.get('Category')} category_id={category_id}: {data or result}",
                            file=sys.stderr,
                        )
                        continue
                    if data.get("participant_created"):
                        stats["created"] += 1
                    elif data.get("category_changed") or data.get("placeholder_reused") or data.get("before") != data.get("after"):
                        stats["changed"] += 1
                    else:
                        stats["unchanged"] += 1
        return stats

    def upload_registrations_mcp(self, competition_id=None, mcp_url=None, mcp_token=None, bibs=False, dry_run=False):
        if not competition_id:
            raise ValueError("competition_id is required for MCP registration upload")
        if not mcp_url:
            raise ValueError("mcp_url is required for MCP registration upload")
        return asyncio.run(
            self._upload_registrations_mcp_async(
                competition_id=competition_id,
                mcp_url=mcp_url,
                mcp_token=mcp_token,
                bibs=bibs,
                dry_run=dry_run,
            )
        )

    def upload_registrations(self, competition_id=None, upload=False, bibs=False, teams=False, event_name=None,
                             waiver=False,
                             mcp_url=None, mcp_token=None, mcp_dry_run=False):

        if waiver:
            for row in self.registration_data:
                row['Waiver'] = 'true'
        if True:
            xlsx_file = self.create_registrations_xlsx_file(self.registration_data, file_path="registrations.xlsx", teams=teams)
        if self.stats['tbd_category']:
            tbd_name = f"{event_name}_tbds.csv" if event_name else "tbds.csv"
            self.create_unknowns_csv_file(file_path=tbd_name)
        if not upload:
            return
        print(f"Bibs: {bibs}, teams: {teams}", file=sys.stderr)
        if mcp_url:
            stats = self.upload_registrations_mcp(
                competition_id=competition_id,
                mcp_url=mcp_url,
                mcp_token=mcp_token,
                bibs=bibs,
                dry_run=mcp_dry_run,
            )
            print(
                f"MCP registrations {'dry-run ' if mcp_dry_run else ''}processed: {stats['processed']}, "
                f"created: {stats['created']}, changed: {stats['changed']}, "
                f"unchanged: {stats['unchanged']}, skipped: {stats['skipped']}, failed: {stats['failed']}",
                file=sys.stdout,
            )
            return

        xlsx_file = self.create_registrations_xlsx_in_memory(self.registration_data, teams=teams)

        next_path = f"RaceDB/Competitions/CompetitionDashboard/{competition_id}/UploadPrereg/{competition_id}/"

        self.upload_file(next_path, tableCheck=True, 
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "assign_bibs_option": "2" if bibs else "0",
                "clear_existing": "on",
                "ok-submit": "OK",
            },)

        print("*20")
        print("Registration stats:", file=sys.stdout)
        for stat, value in self.stats.items():
            if stat == 'tbd_category':
                continue
            print(f"  {stat}: {value}", file=sys.stdout)
        print(f"  TBDs: {self.stats['tbd_category']}", file=sys.stdout)
        print("Merchandise purchased:", file=sys.stdout)
        for key in sorted(self.purchase_counts.keys()):
            print(f"  {key}: {self.purchase_counts[key]}", file=sys.stdout)

    def new_competition(self, template_date=None, start_date=None, new_name=None, replace=True):

        try:
            existing_competition_id, existing_competition_name, competition_long_name, competition_start_date = self.racebsql.find_competition(None, start_date)
        except TypeError as e:
            print(f"Competition not found for {start_date}.", file=sys.stdout)

        try:
            template_competition_id, template_competition_name, competition_long_name, competition_start_date = self.racebsql.find_competition(None, template_date)
        except TypeError as e:
            print(f"Competition not found for {template_date}.", file=sys.stdout)


        pass

RaceDB.upload_file = upload_file
RaceDB.download_file = download_file
RaceDB.save_file = save_file
