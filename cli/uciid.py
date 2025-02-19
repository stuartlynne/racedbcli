#!/usr/bin/env python3

import sys
import os
import io
import json
import autopage, argparse
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
import time
from urllib.parse import urljoin
from libs.login import session_login
from libs.upload import upload_file

# This program is used to fetch membership data from the Cycling BC API so 
# that we can update the license holders in the RaceDB database.
# Specifically the Cycling BC data is provides us with the correct:
#   - UCI ID 
#   - First and Last Name
#   - Current License Number
#   - Current Team Affiliation

# The program will read an XLSX file with the first and last names of the license holders,
# and then fetch the Cycling BC membership data for each license holder which will give
# us:
#   - UCI ID
#   - Age as of the data of the download
#   - current license number
#   - current team affiliation

# We can fetch the current license holder data from the RaceDB database using the UCI ID,
# and we need to verify that the data from the Cycling BC API matches.
# If the data does not match, we need to update the RaceDB database with the new data.

# If the data does not match, we need to update the RaceDB database with the new data.
# Create an XLSX file with the updated data that can be used to update the RaceDB database
# for license holders that need to be updated.

# 



# Class to connect to the database
# Get license holder data using the UCI ID
#
class RacedbSQL:

    def __init__(self, host):
        # Connect to PostgreSQL database
        conn = psycopg2.connect(
            dbname="racedb",
            user="postgres",
            password="5wHYUQ9qmttpq58EV4EG",
            host=host,
            port="5432"
        )
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.debug = False

    def log_debug(self, message):
        print(message, file=sys.stdout)

    def log_sql(self, query, params, debug=True):
        """Logs the fully expanded SQL query with parameters."""
        expanded_query = query % tuple(map(lambda x: f"'{x}'" if isinstance(x, str) else str(x), params)) if params else query
        if debug:
                self.log_debug(f"Executing SQL: {expanded_query}")


    def cur_execute(self, msg, query, params, debug=True):
        """Executes a query with parameters and logs the expanded query."""
        self.log_debug(msg)
        self.log_sql(query, params, debug=debug)
        self.cur.execute(query, params)

    def find_uci_id(self, uci_id=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            uci_id_query = "SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder WHERE uci_id = %s;"
            self.cur_execute(f'Find licenseholder by uciid {uci_id}', uci_id_query, (uci_id,), debug=self.debug)
            licenseholder = self.cur.fetchone()
            if licenseholder:
                print(f"SQL License Holder found: {licenseholder}", file=sys.stdout)
                return licenseholder
            print(f"No licenseholder found for {uci_id}.", file=sys.stdout)
            return None
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return None

    def find_name(self, first_name=None, last_name=None):
        try:
            # Connect to PostgreSQL database
            #conn, cur = connect_db(host)
            uci_id_query = "SELECT id, last_name, first_name, license_code, date_of_birth, gender, uci_id FROM core_licenseholder WHERE first_name = %s AND last_name = %s;"
            self.cur_execute(f'Find licenseholder by names {last_name}, {first_name}', uci_id_query, (first_name, last_name,), debug=self.debug)
            licenseholders = self.cur.fetchmany()
            #print(f"License Holders found: {licenseholders}", file=sys.stdout)
            
        except psycopg2.DatabaseError as error:
            print(f"Database error: {error}", file=sys.stdout)
        return licenseholders

class UploadLicenseHolders:
    def __init__(self, base_url=None, username=None, password=None, ): 
        self.base_url = base_url
        self.username = username
        self.password = password
        self.data = []


    def append_data(self, first_name=None, last_name=None, uci_id=None, license_number=None, team=None, dob=None, gender='M', note=None, comments=None):
        self.data.append({
            'Last Name': last_name,
            'First Name': first_name,
            'License': license_number,
            'UCI ID': uci_id,
            'DOB': dob,
            'Gender': gender,
            'Team': team,
            'Note': note,
            'Comments': comments,
        })

    # create new license holder, DoB jan 1, Year based on age from CCN, gender male
    #def new_license_holder(self, first_name, last_name, uci_id, license_number, team):
    def new_license_holder(self, first_name, last_name, uci_id, person,):
        print(f"No license holder found for {first_name} {last_name}.", file=sys.stdout)
        license_number = person["license_number"]
        team = person["team"]
        age = person["age"]
        dob = f"01-01-{2025 - age}"
        self.append_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                         license_number=license_number, team=team, dob=dob, comments="New license holder", note="FIX AGE AND GENDER!")

    # update license holder with new data based on last, first names and DoB
    def update_license_holder(self, first_name=None, last_name=None, dob=None, uci_id=None, license_number=None, team=None, msg=None):
        print(f"Updating license holder for {first_name} {last_name}.", file=sys.stdout)
        self.append_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                         license_number=license_number, team=team, dob=dob, comments=f"Update {msg}")


    def create_xlsx_file(self, data):
        file_path = "license_holders.xlsx"
        with open(file_path, "wb") as output:
            df = pd.DataFrame(data, columns=["Last Name", "First Name", "License", "UCI ID", "DOB", "Gender", "Team", "Note", "Comments"])
            df.to_excel(output, index=False, engine='xlsxwriter')
        return open(file_path, 'rb')


    def create_xlsx_in_memory(self, data):
        output = io.BytesIO()
        df = pd.DataFrame(data, columns=["Last Name", "First Name", "License", "UCI ID", "DOB", "Gender", "Team", "Note", "Comments"])
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def login_and_upload(self,):

        if True:
            xlsx_file = self.create_xlsx_file(self.data)
        xlsx_file = self.create_xlsx_in_memory(self.data)

        next_path = "RaceDB/LicenseHolders/LicenseHoldersImportExcel/"

        session = session_login(self.base_url, self.username, self.password)
        upload_file(session, self.base_url, next_path, tableCheck=True, 
            #files= { 'excel_file': open(file_path, 'rb'), },
            #files={'excel_file': ('license_holders.xlsx', xlsx_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "set_team_all_disciplines": "on",
                "update_license_codes": "on",
                "ok-submit": "OK",
            },)


class GetLicenseholders:
    def __init__(self, upload=None, racedb=None, base_url=None, username=None, password=None, xlsfile=None):
        self.upload = upload
        self.racedb = racedb
        self.base_url = base_url
        self.username = username
        self.password = password
        self.xlsfile = xlsfile
        os.makedirs('.data', exist_ok=True)

    # name of cache file for cycling bc membership data from CCN
    def dataname(self, first_name, last_name, ):
      return f'.data/{last_name}_{first_name}.json'.lower()

    # Function to fetch membership data from the API
    # If we have a cached copy, return that.
    # Save a cached copy of the data if found.
    def fetch_membership_data(self, first_name, last_name):
        # if cache file exists use it
        if os.path.exists(self.dataname(first_name, last_name)):
            # load data
            with open(self.dataname(first_name, last_name), 'r') as f:
                data = json.load(f)
            # XXX should check that this file is for the correct calendar year
            return data

        url = f"https://ccnbikes.com/en/rest/v2/membership_app/identity-memberships/lookup/?first_name={first_name}&last_name={last_name}&page=1&page_size=25&page_slug=cycling-bc-2025"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            data["timestamp"] = time.strftime("%Y-%m-%d")
            with open(self.dataname(first_name, last_name, ), 'w') as f:
                print(json.dumps(data, indent=4), file=f)
            return response.json()
        else:
            return None


    # check license holder
    #   - missing in RaceDB
    #   - license number does not match
    #   - uci id does not match
    def check_license_holder(self, first_name=None, last_name=None, uci_id=None, license_holder=None, person=None, msg=None):
        print(f"Checking: {first_name} {last_name} {uci_id} using {msg}", file=sys.stdout)
        print(f"  Person: {person}", file=sys.stdout)
        print(f"  License Holder: {license_holder}", file=sys.stdout)
        if not license_holder:
            self.upload.new_license_holder(first_name, last_name, uci_id, person)
            return
        if person["license_number"] != license_holder["license_code"]:
            self.upload.update_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                  dob=license_holder['date_of_birth'], license_number=person["license_number"], team=person["team"], msg="license number")
            return
        if person["uci_id"] != license_holder["uci_id"]:
            self.upload.update_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                  dob=license_holder['date_of_birth'], license_number=person["license_number"], team=person["team"], msg="uci id")

        

    # Function to extract relevant data from JSON
    # There may be multiple memberships for the first name and last name that are
    # actually different people, uci_id is the best way to identify a person.
    #
    # Find the matching data from the racedb database and return the data to
    # get DoB and gender, then verify that racedb data matches the CCN data.
    #`  - first name, last name
    #   - license number
    #   - team name (todo, will need additional sql queries)
    #
    def extract_data(self, first_name=None, last_name=None, team=None, data=None):
        for count, result in enumerate(data.get("results", [])):
            for membership in result.get("lookup_identity_memberships", []):
                person = {
                    "first_name": membership["identity_snapshot"]["first_name"],
                    "last_name": membership["identity_snapshot"]["last_name"],
                    "age": membership["identity_snapshot"]["age"],

                    "membership": membership["membership_organization"]["name"],

                    "uci_id": next((num["generated_number_value"] for num in membership["generated_numbers"] if num["number_title"] == "UCI ID"), None),
                    "license_number": next((num["generated_number_value"] for num in membership["generated_numbers"] if num["number_title"] in ["License Number", "Provincial Membership Number"]), None),

                    "license_type": membership["purchased_groups"][0]["name"] if membership.get("purchased_groups") else None,

                    "licenses": [node["name"] for group in membership.get("purchased_groups", []) for node in group.get("nodes", [])],

                    "team": team,
                }
                
                uci_id = person["uci_id"]
                license_holder = self.racedb.find_uci_id(uci_id)
                if license_holder:
                    self.check_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                          license_holder=license_holder, person=person, msg="uci id",)
                else:
                    license_holders = self.racedb.find_name(first_name, last_name)
                    if not license_holders:
                        self.check_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                          license_holder=None, person=person, msg="name not found",)
                    else:
                        for license_holder in license_holders:
                            self.check_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                                 license_holder=license_holder, person=person, msg='name found',)
                print('--------------------------------------------', file=sys.stdout)


    def process_cbc(self, ):
        # Read the XLSX file and iterate through rows
        xlsx_file = "members.xlsx"  # Update with your actual file path
        df = pd.read_excel(xlsx_file)


        all_data = []
        for count, (index, row) in enumerate(df.iterrows()):
            first_name, last_name, team = row["First Name"], row["Last Name"], row["Primary Club / Team"]
            print('Processing:', first_name, last_name, file=sys.stdout)
            data = self.fetch_membership_data(first_name, last_name)
            self.extract_data(first_name=first_name, last_name=last_name, team=team, data=data)
            #if data:
            #    all_data.extend(extract_data(host, first_name, last_name, team, data))
            if count > 10:
                break

        # Sort the list of dicts by last name, then by first name
        #sorted_data = sorted(all_data, key=lambda x: (x["last_name"], x["first_name"]))

        # Output the results
        #for item in sorted_data:
        #    print(item)


epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""
def main():
    parser = argparse.ArgumentParser(description="RaceDB update license holders from xlsx.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--xlsx', type=str, default=None, help='CBC membership xlsx file')

    args = parser.parse_args()
    
    base_url = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    xlsfile = args.xlsx         

    host = base_url.removeprefix("https://").removeprefix("http://").split(":")[0]
    racedb = RacedbSQL(host)
    upload = UploadLicenseHolders(base_url=base_url, username=username, password=password,)
    getlicenseholders = GetLicenseholders(upload=upload, racedb=racedb, base_url=base_url, username=username, password=password, xlsfile=xlsfile)

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        getlicenseholders.process_cbc()
        upload.login_and_upload()

if __name__ == "__main__":
    main()
    exit(0)


