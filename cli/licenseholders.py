#!/usr/bin/env python3

import sys
import os
import autopage, argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from libs.racedb import RaceDB
from libs.racedbsql import RaceDBSQL

def upload_licensholders(racedb, filename,):
    next_path = "RaceDB/LicenseHolders/LicenseHoldersImportExcel/"
    racedb.upload_file(next_path, tableCheck=True, 
                files= { 'excel_file': open(filename, 'rb'), },
                data={
                    "set_team_all_disciplines": "on",
                    "update_license_codes": "on",
                    "ok-submit": "OK",
                },
                )

epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""
def main():
    parser = argparse.ArgumentParser(description="RaceDB update license holders from xlsx.", epilog=epilog)
    parser.add_argument('--host', type=str, default='localhost', help='database host')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--xlsx', type=str, default='', help='License Holder XLSX file for upload')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)


    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    filename = args.xlsx       # e.g. /path/to/file.xlsx

    sql = RaceDBSQL(host=host, )
    racedb = RaceDB(host=host, username=username, password=password)

    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        upload_licensholders(racedb, filename,)

if __name__ == "__main__":
    main()
    exit(0)


