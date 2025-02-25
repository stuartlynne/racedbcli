#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
#import argparse
import autopage, argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL

def download_partipants(racedb, competition_id, filename=None):
    download_path = f"RaceDB/Competitions/CompetitionDashboard/{competition_id}/Participants/{competition_id}/"

    final_response = racedb.download_file(download_url=download_path, 
            data = {
                'event': "-1.0",
                'name_text': "",
                'gender': "2",
                'category': "-1",
                'bib': "",
                'rfid_text': "",
                'eligible': "2",
                'license_checked': "2",
                'paid': "2",
                'confirmed': "2",
                'team_text': "",
                'role_type': "0",
                'city_text': "",
                'state_prov_text': "",
                'nationality_text': "",
                'complete': "2",
                'has_events': "2",
                'export-excel-submit': 'Export to Excel',
                },
                )
    if not final_response:
        print("No response from download_file", file=sys.stderr)
        return
    
    filename = racedb.save_file(final_response, filename)
    print(f"Saved to {filename}")


epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""

def main():
    parser = argparse.ArgumentParser(description="Get participants for a competition.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--name', type=str, help='Name of the competition.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)


    args = parser.parse_args()
    
          
    host = args.host   # e.g. http://192.168.250.51:9080
    username = args.username   # e.g. super
    password = args.password   # e.g. super
    date = args.date
    name = args.name
    #file_path = args.xlsx  # e.g. /path/to/file.xlsx

    sql = RaceDBSQL(host=host, )
    racedb = RaceDB(host=host, username=username, password=password)

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        try:
            print(f"Looking for competition with start date: {date} name: {name}")
            competition = sql.find_competition(name, date)
        except TypeError as e:
            print(f"Exception: {e}")
            print(f"Competition not found start date: {date}")
            exit(1)

        filename = f"{competition['name']}-{competition['start_date']}.xlsx".replace(" ", "_")
        download_partipants(racedb, competition['id'], filename)  

if __name__ == "__main__":
    main()
    exit(0)

