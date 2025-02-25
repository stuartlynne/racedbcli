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
from libs.upload import upload_file

epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""

def upload_prereg(racedb, competition_id, filename):
    next_path = f"RaceDB/Competitions/CompetitionDashboard/{competition_id}/UploadPrereg/{competition_id}/"
    racedb.upload_file(next_path, preCheck=True,
            files={'excel_file': open(filename, 'rb')},
            data = { 'clear_existing': 'on', 'ok-submit': 'OK'},
            )



def main():
    parser = argparse.ArgumentParser(description="Import RaceDB competition pre-registration xlsx file.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--start_date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--name', type=str, help='Name of the competition.')

    parser.add_argument('--xlsx', type=str, default='', help='Pre-Registration Data XLSX file for upload')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
          
    host = args.host   # e.g. http://192.168.250.51:9080
    username = args.username   # e.g. super
    password = args.password   # e.g. super
    filename = args.xlsx  # e.g. /path/to/file.xlsx
    start_date = args.start_date

    sql = RaceDBSQL(host=host, )
    racedb = RaceDB(host=host, username=username, password=password)
    

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=autopage.line_buffer_from_input()) as sys.stdout:
        try:
            print(f"Looking for competition with start date: {start_date}")
            competition = sql.find_competition(None, start_date)
        except TypeError as e:
            print(f"Competition not found start date: {start_date}")
            exit(1)

        print('Competition: ', competition, file=sys.stdout)
        upload_prereg(racedb, competition['id'], filename)

if __name__ == "__main__":
    main()
    exit(0)

