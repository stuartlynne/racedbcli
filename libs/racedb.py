#!/usr/bin/env python3

import sys
import os
import io
import json
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
                           "DOB": 20, 
                           "Gender": 5, 
                           "Age": 5, 
                           "UCI ID": 10, 
                           "License Check": 4, 
                           "License": 10, 
                           "Category": 20, 
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

    def add_registration(self, first_name=None, last_name=None, uci_id=None, license_number=None, license_check=False, 
                         gender=None, license_type=None, category=None, note=None, allowed=False):
        self.registration_data.append({
            'First Name': first_name,
            'Last Name': last_name,
            'License': license_number,
            'License Check': license_check,
            'UCI ID': uci_id,
            'Gender': gender,
            'Paid': 'true',
            'Waiver': 'true',
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
        registration_headers = self.RegistrationHeaders
        if teams:
            registrations_headers.insert(len(teams)-1, 'Team')
        create_xlsx_file(file_path, registration_headers, data)


    def create_registrations_xlsx_in_memory(self, data, teams=False):
        output = io.BytesIO()
        registration_headers = self.RegistrationHeaders
        if teams:
            registrations_headers.insert(len(teams)-1, 'Team')
        df = pd.DataFrame(data, columns=registration_headers)
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def upload_registrations(self, competition_id=None, upload=False, bibs=False, teams=False):

        if True:
            xlsx_file = self.create_registrations_xlsx_file(self.registration_data, file_path="registrations.xlsx", teams=teams)
        if not upload:
            return
        xlsx_file = self.create_registrations_xlsx_in_memory(self.registration_data, teams=teams)

        next_path = f"RaceDB/Competitions/CompetitionDashboard/{competition_id}/UploadPrereg/{competition_id}/"

        self.upload_file(next_path, tableCheck=True, 
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "assign_missing_bibs": "on" if bibs else "off",
                "clear_existing": "on",
                "ok-submit": "OK",
            },)

        print("*20")
        print("Registration stats:", file=sys.stdout)
        for stat, value in self.stats.items():
            print(f"  {stat}: {value}", file=sys.stdout)
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
