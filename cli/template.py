#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
#import argparse
import autopage, argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
#from login import session_login
#from upload import upload_file
#from findsql import find_competition
#from download import download_file
#from savefile import save_file

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL
#from libs.download import download_file
#from libs.upload import upload_file
#from libs.savefile import save_file
#from pager import open_pager, close_pager, PagerContext

# https://racedb.wimsey.online/RaceDB/Competitions/CompetitionDashboard/395/   

def download_template(racedb, competition_id, filename=None):

    download_path = f"RaceDB/Competitions/CompetitionExport/{competition_id}/"

    final_response = racedb.download_file(download_path, 
            data = {
                'export_as_template': 'on',
                'remove_ftp_info': 'on',
                'excel-export-submit': 'Export to Excel',
                },
                )
    if not final_response:
        print("No response from download_file", file=sys.stderr)
        return
    
    # 4) Determine filename from 'Content-Disposition' if present
    filename = racedb.save_file(final_response, filename)
    print(f"Saved to {filename}")


epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""

def main():
    parser = argparse.ArgumentParser(description="Import RaceDB competition pre-registration xlsx file.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--name', type=str, help='Name of the competition.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    #parser.add_argument('--xlsx', type=str, default='', help='Pre-Registration Data XLSX file for upload')

    args = parser.parse_args()
    
          
    host = args.host   # e.g. http://192.168.250.51:9080
    username = args.username   # e.g. super
    password = args.password   # e.g. super
    name = args.name
    date = args.date
    date = args.date
    #file_path = args.xlsx  # e.g. /path/to/file.xlsx

    #host = base_url.removeprefix("https://").removeprefix("http://").split(":")[0]


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

        filename = f"{competition['name']}_{competition['start_date']}.gz".replace(" ", "_")
        download_template(racedb, competition['id']) 
        

if __name__ == "__main__":
    main()
    exit(0)

