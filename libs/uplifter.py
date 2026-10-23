import csv
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


BASE_URL = "https://upliftercycling.com"
DEFAULT_REPORT = "Complete Registration w/ Membership Info"
PURCHASE_REPORT = "Purchased Products w/ registration information"


class UplifterError(RuntimeError):
    pass


def eprint(*args):
    print(*args, file=sys.stderr)


def load_env(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw_line in p.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def normalize_name(value):
    return " ".join((value or "").lower().split())


class UplifterReports:
    def __init__(self, base_url=BASE_URL, username=None, password=None, env_file=".ccn.env"):
        env = load_env(env_file)
        self.base_url = base_url.rstrip("/")
        self.username = username or env.get("LOGIN") or os.getenv("CCN_LOGIN") or os.getenv("LOGIN")
        self.password = password or env.get("PASSWORD") or os.getenv("CCN_PASSWORD") or os.getenv("PASSWORD")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=UTF-8",
                "Referer": f"{self.base_url}/#!/login/",
            }
        )

    def request_json(self, method, path_or_url, **kwargs):
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.base_url, path_or_url)
        response = self.session.request(method, url, **kwargs)
        eprint(f"{method.upper()} {url} -> {response.status_code}")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise UplifterError(f"{exc}: {response.text[:500]}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise UplifterError(f"Expected JSON from {url}, got {response.text[:500]!r}") from exc

    def login(self):
        if not self.username or not self.password:
            raise UplifterError("Set LOGIN/PASSWORD in .ccn.env or pass Uplifter credentials")

        login_url = urljoin(self.base_url, "/en/rest/v2/users/login/")
        payload = {
            "username": self.username,
            "password": self.password,
            "accepted_cookie_policy": True,
        }
        response = self.session.post(login_url, json=payload, timeout=30)
        eprint(f"POST {login_url} -> {response.status_code}")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise UplifterError(f"Login failed: {exc}: {response.text[:500]}") from exc

        csrf = self.session.cookies.get("csrftoken")
        if csrf:
            self.session.headers["X-CSRFToken"] = csrf

        user = self.request_json("GET", "/en/rest/v2/users/session_user/", timeout=30)
        if user.get("is_anonymous") or not user.get("is_organizer"):
            raise UplifterError(
                "Login succeeded but session is not an organizer account: "
                f"id={user.get('id')} is_anonymous={user.get('is_anonymous')} "
                f"is_organizer={user.get('is_organizer')}"
            )
        eprint(f"Logged in as organizer id={user.get('id')} email={user.get('email')}")
        return user

    def search_events(self, *, event_id=None, event_name=None):
        params = {
            "page": 1,
            "sort_type": "unnatural",
            "application": "management_tools",
            "access_level": "view",
            "page_size": 50,
        }
        if event_id:
            params["event"] = event_id
        elif event_name:
            params["name"] = event_name
        else:
            raise UplifterError("search_events requires event_id or event_name")

        data = self.request_json(
            "GET",
            "/en/rest/v2/listing_app/event-listings/",
            params=params,
            timeout=30,
        )
        results = data.get("results") or []
        if event_id:
            matches = [
                result
                for result in results
                if str((result.get("event") or {}).get("id")) == str(event_id)
            ]
        else:
            wanted = normalize_name(event_name)
            matches = [
                result
                for result in results
                if normalize_name((result.get("event") or {}).get("name") or result.get("name"))
                == wanted
            ]
        if not matches:
            raise UplifterError(f"No matching event found. Available matches: {self._event_summaries(results)}")
        if len(matches) > 1:
            raise UplifterError(f"Multiple matching events found: {self._event_summaries(matches)}")

        result = matches[0]
        event = result.get("event") or {}
        event_info = {
            "listing_id": result.get("id"),
            "event_id": event.get("id"),
            "name": event.get("name") or result.get("name"),
            "slug": event.get("slug") or result.get("slug"),
            "starts": result.get("event_starts"),
            "ends": result.get("event_ends"),
        }
        if not event_info["event_id"] or not event_info["slug"]:
            raise UplifterError(f"Matched event is missing event id or slug: {event_info}")
        return event_info

    @staticmethod
    def _event_summaries(results):
        return [
            {
                "listing_id": result.get("id"),
                "event_id": (result.get("event") or {}).get("id"),
                "name": (result.get("event") or {}).get("name") or result.get("name"),
                "slug": (result.get("event") or {}).get("slug") or result.get("slug"),
                "starts": result.get("event_starts"),
            }
            for result in results
        ]

    def get_report_dashboard(self, event_id):
        params = {
            "object_id": event_id,
            "object_type": "event",
            "access_level": "view",
            "standalone": "1",
        }
        return self.request_json(
            "GET",
            "/en/rest/v2/report/report/report_dashboard_data/",
            params=params,
            timeout=30,
        )

    @staticmethod
    def iter_report_types(report_data):
        for group in report_data.get("report_type_groups", []):
            for report_type in group.get("report_types", []):
                yield group, report_type

    def find_report_type(self, report_data, wanted_name=DEFAULT_REPORT):
        wanted = normalize_name(wanted_name).replace("w/ ", "w/")
        for group, report_type in self.iter_report_types(report_data):
            name = report_type.get("name", "")
            normalized = normalize_name(name).replace("w/ ", "w/")
            if normalized == wanted:
                return group, report_type
        available = [rt.get("name", "") for _, rt in self.iter_report_types(report_data)]
        raise UplifterError(f"Report {wanted_name!r} not found. Available: {available}")

    @staticmethod
    def print_report_summary(report_type):
        last_report = report_type.get("last_report") or {}
        eprint(f"Report: {report_type.get('name')} id={report_type.get('id')}")
        eprint(f"  update_link={report_type.get('update_link')}")
        eprint(f"  last_report_id={last_report.get('id')}")
        eprint(f"  finished_at={last_report.get('finished_at')}")
        eprint(f"  is_beeing_generated={last_report.get('is_beeing_generated')}")
        for report_file in last_report.get("report_files") or []:
            eprint(f"  file format={report_file.get('format')} url={report_file.get('url')}")

    def update_report(self, report_type, timeout_seconds):
        update_link = report_type.get("update_link")
        if not update_link:
            raise UplifterError("Selected report has no update_link")
        data = self.request_json("GET", update_link, timeout=60)
        task_uuid = data.get("task_uuid") or data.get("task_id")
        if not task_uuid:
            raise UplifterError(f"Update response did not contain task_uuid: {data}")
        eprint(f"Update started: task_uuid={task_uuid}")

        deadline = time.monotonic() + timeout_seconds
        task_url = f"/en/rest/v2/task_app/tasks/{task_uuid}/"
        while time.monotonic() < deadline:
            try:
                task = self.request_json("GET", task_url, timeout=30)
            except UplifterError as exc:
                cause = exc.__cause__
                if not (
                    isinstance(cause, requests.HTTPError)
                    and cause.response is not None
                    and cause.response.status_code == 404
                ):
                    raise
                # A queued task may not have a TaskResult until the worker starts.
                eprint("  task result not available yet; waiting")
                task = {}
            state = task.get("state")
            eprint(f"  task state={state}")
            if state == "SUCCESS":
                return task
            if state == "FAILURE":
                raise UplifterError(f"Report update failed: {task}")
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        raise UplifterError(f"Timed out waiting for report update task {task_uuid}")

    @staticmethod
    def select_report_file(report_type, file_format):
        last_report = report_type.get("last_report") or {}
        files = last_report.get("report_files") or []
        wanted = file_format.upper()
        for report_file in files:
            if (report_file.get("format") or "").upper() == wanted:
                return report_file
        raise UplifterError(f"No {wanted} report file found in last_report: {files}")

    def download_report_file(self, report_file, output=None):
        url = report_file.get("url")
        if not url:
            raise UplifterError(f"Report file missing url: {report_file}")
        response = self.session.get(url, timeout=120)
        eprint(f"GET {url} -> {response.status_code}")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise UplifterError(f"Download failed: {exc}: {response.text[:500]}") from exc

        output_path = Path(output) if output else Path(url.split("/")[-1].split("?")[0])
        output_path.write_bytes(response.content)
        eprint(f"Wrote {len(response.content)} bytes to {output_path}")
        return output_path, response

    def fetch_purchase_report(self, event_id, output="ccn_purchases.csv", update=False,
                              timeout_seconds=300):
        """Download purchases using the already authenticated event session."""
        dashboard = self.get_report_dashboard(event_id)
        _, report_type = self.find_report_type(dashboard, PURCHASE_REPORT)
        if update or not (report_type.get("last_report") or {}).get("report_files"):
            self.update_report(report_type, timeout_seconds)
            dashboard = self.get_report_dashboard(event_id)
            _, report_type = self.find_report_type(dashboard, PURCHASE_REPORT)
        self.print_report_summary(report_type)
        report_file = self.select_report_file(report_type, "csv")
        path, _ = self.download_report_file(report_file, output)
        return path

    def fetch_registration_report(
        self,
        *,
        event_id=None,
        event_name=None,
        report=DEFAULT_REPORT,
        file_format="csv",
        output=None,
        update=False,
        timeout_seconds=300,
        slug=None,
    ):
        self.login()
        event_info = self.search_events(event_id=event_id, event_name=event_name)
        if slug and slug != event_info["slug"]:
            raise UplifterError(f"--slug {slug!r} does not match discovered slug {event_info['slug']!r}")

        report_page = (
            f"{self.base_url}/management/tools/#!/dashboard/{event_info['event_id']}/event/report"
            f"?slug={event_info['slug']}"
        )
        eprint(
            "Event: "
            f"id={event_info['event_id']} name={event_info['name']!r} "
            f"slug={event_info['slug']!r} listing_id={event_info['listing_id']}"
        )
        eprint(f"Report page: {report_page}")

        report_data = self.get_report_dashboard(event_info["event_id"])
        _, report_type = self.find_report_type(report_data, report)
        self.print_report_summary(report_type)

        if update:
            self.update_report(report_type, timeout_seconds)
            report_data = self.get_report_dashboard(event_info["event_id"])
            _, report_type = self.find_report_type(report_data, report)
            self.print_report_summary(report_type)

        report_file = self.select_report_file(report_type, file_format)
        output_path, response = self.download_report_file(report_file, output)
        if file_format.lower() == "csv":
            eprint(f"CSV rows: {csv_row_count(output_path)}")
        return output_path, event_info, report_type, response


def csv_row_count(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return sum(1 for _ in csv.DictReader(f))
