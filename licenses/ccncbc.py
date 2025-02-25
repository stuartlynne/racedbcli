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
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL
from libs.upload import upload_file

#from findsql import find_competition
#from login import session_login
#from upload import upload_file

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

# Class to accumulate license holders, then to create and upload an XLSX file 
class UploadLicenseHolders:
    def __init__(self, host=None, racedb=None, username=None, password=None, ): 
        self.host = host
        self.racedb = racedb
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

        self.racedb.upload_file(next_path, tableCheck=True,
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "set_team_all_disciplines": "on",
                "update_license_codes": "on",
                "ok-submit": "OK",
            },)

        #session = session_login(self.host, self.username, self.password)
        #upload_file(session, self.host, next_path, tableCheck=True, 
        #    #files= { 'excel_file': open(file_path, 'rb'), },
        #    #files={'excel_file': ('license_holders.xlsx', xlsx_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        #    files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
        #    data={
        #        "set_team_all_disciplines": "on",
        #        "update_license_codes": "on",
        #        "ok-submit": "OK",
        #    },)


# a class to parse the membership data from the Cycling BC provided xlsx file.
# The first and last name are used to fetch the membership data from the Cycling BC API and local RaceDB.
#
class GetLicenseholders:
    def __init__(self, upload=None, sql=None, host=None, username=None, password=None, xlsfile=None):
        self.upload = upload
        self.sql = sql
        self.host = host
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
                license_holder = self.sql.find_uci_id(uci_id)
                if license_holder:
                    self.check_license_holder(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                          license_holder=license_holder, person=person, msg="uci id",)
                else:
                    license_holders = self.sql.find_name(first_name, last_name)
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
            if count > 100:
                break

        # Sort the list of dicts by last name, then by first name
        #sorted_data = sorted(all_data, key=lambda x: (x["last_name"], x["first_name"]))

        # Output the results
        #for item in sorted_data:
        #    print(item)

def find_jan01(sql):
    # Find all license holders with a DoB of Jan 1
    print("------------------------------------------------------")
    print("------------------------------------------------------")
    print("------------------------------------------------------")
    print("license holders with DoB of Jan 1")
    license_holders = sql.find_jan01()
    for license_holder in license_holders:
        print(license_holder)

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

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    xlsfile = args.xlsx         
    
    sql = RaceDBSQL(host=host, )
    racedb = RaceDB(host=host, username=username, password=password)

    #host = host.removeprefix("https://").removeprefix("http://").split(":")[0]
    sql = RaceDBSQL(host)
    racedb = RaceDB(host=host, username=username, password=password)
    upload = UploadLicenseHolders(host=host, racedb=racedb, username=username, password=password,)
    getlicenseholders = GetLicenseholders(upload=upload, sql=sql, host=host, username=username, password=password, xlsfile=xlsfile)

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        getlicenseholders.process_cbc()
        upload.login_and_upload()
        return
        find_jan01(sql)

if __name__ == "__main__":
    main()
    exit(0)


