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

class GetCCN:
    def __init__(self, ):
        os.makedirs('.data', exist_ok=True)

    # name of cache file for cycling bc membership data from CCN
    def dataname(self, first_name, last_name, ):
      return f'.data/{last_name}_{first_name}.json'.lower().replace(' ', '_').replace("'", "")

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
            if "results" in data and len(data["results"]):
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
    def extract_data(self, data=None):
        license_holders = []
        #print(f"Extracting data for {data}", file=sys.stdout)
        for count, result in enumerate(data.get("results", [])):
            #print('-----------------------------------')
            #print('Result: ', result)
            #print('-----------------------------------')
            for membership in result.get("lookup_identity_memberships", []):
                person = {
                    "first_name": membership["identity_snapshot"]["first_name"],
                    "last_name": membership["identity_snapshot"]["last_name"],
                    "age": membership["identity_snapshot"]["age"],

                    "membership": membership["membership_organization"]["name"],

                    "uci_id": next((num["generated_number_value"] for num in membership["generated_numbers"] if num["number_title"] == "UCI ID"), None),
                    "license_number": next((num["generated_number_value"] for num in membership["generated_numbers"] if num["number_title"] in ["License Number", "Provincial Membership Number"]), None),

                    "license_type": membership["purchased_groups"][0]["name"] if membership.get("purchased_groups") else None,

                    "licenses": {
                        s[0]: s[1:] for s in [
                            node["name"].split(" :: ") for group in membership.get("purchased_groups", []) 
                            for node in group.get("nodes", [])
                        ]
                    },


                }
                person['UCI License'] = person['license_type'].startswith('UCI RACE')
            #print('-----------------------------------')
            #print('Person: ', person)
            #print('-----------------------------------')
            license_holders.append(person)
        #print('-----------------------------------')
        #for person in license_holders:
        #    print('-----------------------------------')
        #    print('Person: ', person)
        #    print('-----------------------------------')
        #    #print(f"Person: {person
        #print('-----------------------------------')
        return license_holders

    def get_license_holders(self, first_name, last_name,):
        # Read the XLSX file and iterate through rows
        license_holders = self.fetch_membership_data(first_name, last_name)
        #print("License Holders: ", license_holders)
        data = self.extract_data(license_holders)

        return data

if __name__ == "__main__":
    getccn = GetCCN()
    for first_name, last_name in [
        ("Brett", "Boniface"), # single
        ("Albert", "Chan"), # multiple
    ]:
        license_holders = getccn.get_license_holders(first_name, last_name)
        for license_holder in license_holders:
            print(f"License Holder: {license_holder}")
    exit(0)
