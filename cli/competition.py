#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
import io
import json
import gzip
#import argparse
import autopage, argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from login import session_login
from upload import upload_file
from findsql import find_competition
from download import download_file
#from pager import open_pager, close_pager, PagerContext

# create competition
# Check if a competition exists with the specified name and date, if not create 
# a new competition with the specified name and date using a previous competiton
# as a template.

# https://racedb.wimsey.online/RaceDB/Competitions/CompetitionDashboard/395/   
# http://192.168.250.51:9080/RaceDB/Competitions/CompetitionImport/


import json
import gzip
import io
import requests

def dict_to_gzip_filelike(data_dict):
    """
    Converts a Python dictionary to gzipped JSON in memory
    and returns a file-like object (BytesIO).
    """
    # Convert dictionary to JSON string
    data_str = json.dumps(data_dict)
    
    # Compress JSON string to gzipped bytes
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
        gz.write(data_str.encode('utf-8'))
    
    # Reset the pointer to the beginning of the buffer
    buffer.seek(0)
    return buffer

# Example usage:
# 1. Create (or have) the Python dictionary
#data_dict = {"foo": "bar", "nested": {"x": 1, "y": 2}}

# 2. Get a file-like object for gzipped JSON
#gz_filelike = dict_to_gzip_filelike(data_dict)

# 3. Include that object in the 'files' dictionary
#    The key is the form field name. 
#    The value is a tuple of (filename, fileobj, content_type).
#files = {
#    'json_file': ('data.json.gz', gz_filelike, 'application/gzip'),
#}

# 4. Send via a POST request
#url = "https://example.com/your-upload-endpoint"
#response = requests.post(url, files=files)
#
#print(response.status_code)
#print(response.text)



def login_and_create(
    racedb,
    username,
    password,
    competition_id,
    start_date,
    new_name,
    replace,
):
    download_path = f"RaceDB/Competitions/CompetitionExport/{competition_id}/"
    upload_path = f"RaceDB/Competitions/CompetitionImport/"
    
    """
    1) Logs into RaceDB (Django) by:
       - GETing the login form to retrieve the CSRF cookie + token.
       - POSTing username, password, next, plus that CSRF token.
    2) Download template, unzip and return JSON
    3) Update JSON with new date and name
    4) Uploads a file with the new CSRF token from the upload form.
    5) Extracts the <pre> text from the server's response.
    """
    print('Create: {racedb} template competition_id: {competition_id} start_date: {start_date} new_name: {new_name}')

    # 1 
    session = session_login(racedb, username, password)

    # 2
    final_response = download_file(session, racedb, download_path, 
            data = {
                'export_as_template': 'on',
                'remove_ftp_info': 'on',
                'ok-submit': 'OK',
                },)

    # save response into BytesIO 
    buffer = io.BytesIO(final_response.content)
    buffer.seek(0)
    upload_file(session, racedb, upload_path, preCheck=True,
                files={'json_file': ('json.gz', buffer, 'application/gzip')},
                data={
                    'name': new_name,
                    'start_date': start_date,
                    'replace': 'on' if replace else 'off',
                    'import_as_template': 'on',
                    'ok-submit': 'OK',
                },)

    return

    with gzip.GzipFile(fileobj=io.BytesIO(final_response.content), mode='rb') as f:
        decompressed = f.read()
        jsondata = json.loads(decompressed)

    for d in jsondata:
        if d['model'] != 'core.competition':
            continue
        d['fields']['date'] = start_date
        d['fields']['name'] = new_name
    
    # 4
    gz_filelike = dict_to_gzip_filelike(jsondata)
    upload_file(session, racedb, upload_path, filename=None, 
                #files={'file': ('json_file', json.dumps(jsondata), 'application/json')},
                files={'file': gz_filelike, },
                data={
                    'name': new_name,
                    'start_date': start_date,
                    'replace': 'on' if replace else 'off',
                    'import_as_template': 'on',
                    'ok-submit': 'OK',
                },)


epilog = """
The environment variables RACEDB_USERNAME and RACEDB_PASSWORD will be used 
if to set the authentication username and secret.
"""

def main():
    parser = argparse.ArgumentParser(description="Import RaceDB competition pre-registration xlsx file.", epilog=epilog)
    parser.add_argument('--host', type=str, default='http://localhost:8000/', help='RaceDB Server URL')
    parser.add_argument('--username', type=str, default=None, help='authentication username')
    parser.add_argument('--password', type=str, default=None, help='authentication password')
    parser.add_argument('--template_date', type=str, help='Copy the competition from this date.')
    parser.add_argument('--start_date', type=str, help='Start date of the competition in YYYY-MM-DD format.')
    parser.add_argument('--new_name', type=str, help='Name of the competition.')
    parser.add_argument('--replace', type=bool, default=False, help='Replace existing competition')
                

    #parser.add_argument('--xlsx', type=str, default='', help='Pre-Registration Data XLSX file for upload')

    args = parser.parse_args()
    
          
    racedb = args.host   # e.g. http://192.168.250.51:9080
    username = args.username   # e.g. super
    password = args.password   # e.g. super
    template_date = args.template_date
    new_name = args.new_name
    start_date = args.start_date
    #file_path = args.xlsx  # e.g. /path/to/file.xlsx

    # 1. If competition exists and replace flag is not set then exit
    # 2. Find the competition to copy and Download the previous competition, unzip and return JSON
    # 3. Update JSON with new date and name
    # 4. Compress JSON and Upload to create a new competition, possibly with replace: On

    dbHost = racedb.removeprefix("https://").removeprefix("http://").split(":")[0]
    new_name = None
    print(f"DBHost: {dbHost} new_name: {new_name} start_date: {start_date}")

    os.environ['LESS'] += f" -F --quit-if-one-screen"
    with autopage.AutoPager(line_buffering=True, reset_on_exit=False) as sys.stdout:
        competition_id = None
        try:
            conn, cur, competition_id, competition_name, competition_long_name, competition_start_date = find_competition(dbHost, None, start_date)
        except TypeError as e:
            print(f"Competition not found: {start_date}")

        if competition_id:
            print(f"Competition: {competition_start_date} {competition_name} already exists.")
            exit(0)

        conn, cur, competition_id, competition_name, competition_long_name, competition_start_date = find_competition(dbHost, None, template_date)

        if not competition_id:
            print("Competition: {template_date} not found.")
            exit(1)

        print(f"Competition ID: {competition_id} Name: {competition_name} Long Name: {competition_long_name} Date: {start_date}")

        #filename = f"{competition_name}-{date}.gz".replace(" ", "_")


        login_and_create(
            racedb=racedb,
            username=username,
            password=password,
            start_date=start_date,
            new_name=new_name,
            competition_id=competition_id,
            replace=args.replace,
        )

if __name__ == "__main__":
    main()
    exit(0)

