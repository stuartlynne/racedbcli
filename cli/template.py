#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
#import argparse
import autopage, argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from login import session_login
from upload import upload_file
from findsql import find_competition
from download import download_file
from savefile import save_file
#from pager import open_pager, close_pager, PagerContext

# https://racedb.wimsey.online/RaceDB/Competitions/CompetitionDashboard/395/   

def login_and_download(
    base_url,
    username,
    password,
    filename,
    competition_id,
):
    #next_path = f"RaceDB/NumberSets/NumberSetManage/{competition_id}/NumberSetUploadExcel/{competition_id}/"
    download_path = f"RaceDB/Competitions/CompetitionExport/{competition_id}/"

    """
    1) Logs into RaceDB (Django) by:
       - GETing the login form to retrieve the CSRF cookie + token.
       - POSTing username, password, next, plus that CSRF token.
    2) Navigates to the next_path page (upload form).
    3) Parses the <form> action properly (handling blank or relative).
    4) Uploads a file with the new CSRF token from the upload form.
    5) Extracts the <pre> text from the server's response.
    """

    # 1 and 2
    session = session_login(base_url, username, password)

    # 3, 4, and 5
    final_response = download_file(session, base_url, download_path, 
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
    filename = save_file(final_response, filename)
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

    #parser.add_argument('--xlsx', type=str, default='', help='Pre-Registration Data XLSX file for upload')

    args = parser.parse_args()
    
          
    base_url = args.host   # e.g. http://192.168.250.51:9080
    username = args.username   # e.g. super
    password = args.password   # e.g. super
    date = args.date
    #file_path = args.xlsx  # e.g. /path/to/file.xlsx

    host = base_url.removeprefix("https://").removeprefix("http://").split(":")[0]
    name = None
    print(f"Host: {host} Name: {name} Date: {date}")
    try:
        conn, cur, competition_id, competition_name, competition_long_name, competition_start_date = find_competition(host, name, date)
    except TypeError as e:
        print(f"Competition not found: {name} {date}")
        exit(1)

    filename = f"{competition_name}-{date}.gz".replace(" ", "_")


    LESS = os.environ.get('LESS','')
    os.environ['LESS'] = f"{LESS} -F"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        login_and_download(
            base_url=base_url,
            username=username,
            password=password,
            filename=filename,
            competition_id=competition_id,
        )

if __name__ == "__main__":
    main()
    exit(0)

