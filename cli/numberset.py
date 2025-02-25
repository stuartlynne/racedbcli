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


def upload_numberset(racedb, numberset_id, file_path):
    upload_path = f"RaceDB/NumberSets/NumberSetEdit/{numberset_id}/NumberSetManage/{numberset_id}/NumberSetUploadExcel/{numberset_id}/"
    racedb.upload_file(upload_path, preCheck=True, 
                files= { 'excel_file': open(file_path, 'rb'), },
                data={
                    'ok-submit': 'Ok'
                },)
    pass

def download_numberset(racedb, numberset_id):
       
    print(f"Downloading numberset {numberset_id}")
    download_path = f"RaceDB/NumberSets/NumberSetEdit/{numberset_id}/NumberSetManage/{numberset_id}/"
    final_response = racedb.download_file(download_url=download_path, 
                data={
                    "search_text": '',
                    'search_bib': '',
                    'excel-export-submit': 'Export to Excel'
                },)
    if not final_response:
        print("No response from download_file", file=sys.stderr)
        return
    
    # 4) Determine filename from 'Content-Disposition' if present
    racedb.save_file(final_response, filename=None)

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

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    host = args.host        # e.g. http://192.168.250.51:9080
    username = args.username    # e.g. super
    password = args.password    # e.g. super
    numberset = args.numberset  # e.g. LMCX2022
    file_path = args.xlsx       # e.g. /path/to/file.xlsx

    sql = RaceDBSQL(host=host, )
    racedb = RaceDB(host=host, username=username, password=password)

    try:
        numberset = sql.find_numberset(numberset)
    except TypeError as e:
        print(f"Numberset not found: {name} {date}")
        exit(1)

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        if file_path:
            upload_numberset(racedb, numberset['id'], file_path)
        else:
            download_numberset(racedb, numberset['id'])

if __name__ == "__main__":
    main()
    exit(0)


