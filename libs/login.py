import sys
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def session_login(base_url, username, password):

    print(f"=== Logging in to {base_url} as {username}", file=sys.stdout)

    if not username:
        username = os.environ.get("RACEDB_USERNAME")
    if not password: 
        password = os.environ.get("RACEDB_PASSWORD")
    if not username or not password:
        print("Username and password are required.", file=sys.stdout)
        return None

    session = requests.Session()
    # 1. GET the login form (to fetch CSRF cookie/token).
    login_url = f"{base_url.rstrip('/')}/RACEDB/Login/?next=/RaceDB/"
    print(f"=== GET to login page: {login_url}", file=sys.stdout)
    r_get_login = session.get(login_url)
    if r_get_login.status_code != 200:
        print("Could not load login page successfully.", file=sys.stdout)
        print(r_get_login.text, file=sys.stdout)
        return

    # Parse out the login form CSRF token
    soup_login = BeautifulSoup(r_get_login.text, "html.parser")
    csrf_input = soup_login.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input:
        print("Could not find 'csrfmiddlewaretoken' in the login form.", file=sys.stdout)
        return
    csrf_token_login = csrf_input.get("value")

    # 2. POST to the login endpoint
    login_post_url = f"{base_url.rstrip('/')}/RACEDB/Login/"
    login_data = {
        "csrfmiddlewaretoken": csrf_token_login,
        "username": username,
        "password": password,
        "next": "/RaceDB/",
    }
    headers_login = {"Referer": login_url}

    print(f"=== POST to login: {login_post_url}", file=sys.stdout)
    r_post_login = session.post(login_post_url, data=login_data, headers=headers_login)
    if r_post_login.status_code not in (200, 302):
        print("Login failed or unexpected status.", file=sys.stdout)
        print(r_post_login.text, file=sys.stdout)
        exit(1)

    print("=== Login successful.", file=sys.stdout)
    return session
