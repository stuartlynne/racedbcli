#!/usr/bin/env python3

import sys
import os
import io
import json
import pandas as pd
from libs.login import session_login
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
        self.registration_data = []
        print('RaceDB:', self.base_url, self.username, self.password, file=sys.stdout)
        self.session = session_login(self.base_url, self.username, self.password)


    def add_purchase(self, first_name=None, last_name=None, purchase=None):
        lastfirst = (last_name, first_name)
        if lastfirst not in self.purchases:
            self.purchases[lastfirst] = []
        self.purchases[lastfirst].append(purchase)
        print(f"Adding purchase for {first_name} {last_name}: {self.purchases[lastfirst]}", file=sys.stdout)

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
            'Note': note,
            'Comments': comments,
        })

    # create new license holder, DoB jan 1, Year based on age from CCN, gender male
    #def new_license_holder(self, first_name, last_name, uci_id, license_number, team):
    def new_license_holder(self, first_name=None, last_name=None, uci_id=None, dob=None, gender=None, age=25,):
        print(f"No license holder found for {first_name} {last_name}.", file=sys.stdout)
        license_number = team = None
        #if person:
        #    license_number = person["license_number"]
        #    team = person["team"]
        fixflag = False
        if not dob:
            dob = f"01-01-{2025 - age}"
        if not gender:
            gender = "M"
        self.append_license_holders_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                 license_number=license_number, team=team, dob=dob, gender=gender,
                 comments="New license holder", note="FIX AGE AND GENDER!")

    # update license holder with new data based on last, first names and DoB
    def update_license_holder(self, first_name=None, last_name=None, dob=None, gender=None, uci_id=None, license_number=None, team=None, msg=None):
        print(f"Updating license holder for {first_name} {last_name}.", file=sys.stdout)
        self.append_license_holders_data(first_name=first_name, last_name=last_name, uci_id=uci_id, 
                         license_number=license_number, team=team, dob=dob, gender=gender, comments=f"Update {msg}")

    def create_license_holders_xlsx_file(self, data, file_path=None):
        create_xlsx_file(file_path, self.LicenseHolderHeaders, data)


    def create_license_holders_xlsx_in_memory(self, data):
        output = io.BytesIO()
        df = pd.DataFrame(data, columns=self.LicenseHolderHeaders)
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def upload_license_holders(self,):

        print('License holder data:', self.license_holder_data, file=sys.stdout)
        if True:
            xlsx_file = self.create_license_holders_xlsx_file(self.license_holder_data, file_path="license_holders.xlsx")

        xlsx_file = self.create_license_holders_xlsx_in_memory(self.license_holder_data)

        next_path = "RaceDB/LicenseHolders/LicenseHoldersImportExcel/"

        self.upload_file(next_path, tableCheck=True, 
            #files= { 'excel_file': open(file_path, 'rb'), },
            #files={'excel_file': ('license_holders.xlsx', xlsx_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "set_team_all_disciplines": "on",
                "update_license_codes": "on",
                "ok-submit": "OK",
            },)

    def add_registration(self, first_name=None, last_name=None, uci_id=None, license_number=None, license_check=False, 
                         gender=None, license_type=None, category=None, note=None, ):
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
        print('Registration data: ', self.registration_data[-1], file=sys.stdout)
        pass

    def create_registrations_xlsx_file(self, data, file_path=None):
        create_xlsx_file(file_path, self.RegistrationHeaders, data)


    def create_registrations_xlsx_in_memory(self, data):
        output = io.BytesIO()
        df = pd.DataFrame(data, columns=self.RegistrationHeaders)
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        return output

    def upload_registrations(self, competition_id=None, upload=False):

        if True:
            xlsx_file = self.create_registrations_xlsx_file(self.registration_data, file_path="registrations.xlsx")
        if not upload:
            return
        xlsx_file = self.create_registrations_xlsx_in_memory(self.registration_data)

        next_path = f"RaceDB/Competitions/CompetitionDashboard/{competition_id}/UploadPrereg/{competition_id}/"

        self.upload_file(next_path, tableCheck=True, 
            files={'excel_file': ('license_holders.xlsx', xlsx_file, )},
            data={
                "clear_existing": "on",
                "ok-submit": "OK",
            },)

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
