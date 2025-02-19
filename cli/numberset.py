#!/usr/bin/env python3

import sys
import os
#import argparse
import autopage, argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from login import session_login
from upload import upload_file
from findsql import find_uci_id
from download import download_file
from savefile import save_file

def login_and_upload(
    base_url,
    username,
    password,
    file_path=None,
    numberset_id=None,
):
    next_path = "RaceDB/LicenseHolders/LicenseHoldersImportExcel/"

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

    if file_path:
        upload_path = f"RaceDB/NumberSets/NumberSetEdit/{numberset_id}/NumberSetManage/{numberset_id}/NumberSetUploadExcel/{numberset_id}/"
        upload_file(session, base_url, upload_path, preCheck=True, 
                    files= { 'excel_file': open(file_path, 'rb'), },
                    data={
                        'ok-submit': 'Ok'
                    },)
    else:
        download_path = f"RaceDB/NumberSets/NumberSetEdit/{numberset_id}/NumberSetManage/{numberset_id}/"
        final_response = download_file(session, base_url, download_path, 
                    data={
                        "search_text": '',
                        'search_bib': '',
                        'excel-export-submit': 'Export to Excel'
                    },)
        if not final_response:
            print("No response from download_file", file=sys.stderr)
            return
        
        # 4) Determine filename from 'Content-Disposition' if present
        save_file(final_response, filename=None)


epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""
def main():
    parser = argparse.ArgumentParser(description="RaceDB update license holders from xlsx.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--numberset', type=str, default=None, help='Number Set name')
    parser.add_argument('--xlsx', type=str, default=None, help='License Holder XLSX file for upload')

    args = parser.parse_args()
    
    base_url = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    numberset = args.numberset  # e.g. LMCX2022
    file_path = args.xlsx       # e.g. /path/to/file.xlsx

    host = base_url.removeprefix("https://").removeprefix("http://").split(":")[0]

    try:
        conn, cur, numberset_id, numberset_name, numberset_description, numberset_sponsor = find_numberset(host, numberset)
    except TypeError as e:
        print(f"Numberset not found: {name} {date}")
        exit(1)

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        login_and_upload(
            base_url=base_url,
            username=username,
            password=password,
            file_path=file_path,
            numberset_id=numberset_id,
        )

if __name__ == "__main__":
    main()
    exit(0)


