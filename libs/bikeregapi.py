"""Requests for BikeReg's read-only event export endpoint."""

import sys
import time

import requests


def fetch_event_entries(session, url, token, event_id):
    # This POST reads registrations; do not reuse retries for mutating requests.
    for attempt in range(4):
        try:
            response = session.post(
                url, json={"token": token, "eventID": event_id}, timeout=30
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            reason = type(exc).__name__
            if attempt == 3:
                raise
        else:
            if response.status_code not in (502, 503, 504) or attempt == 3:
                response.raise_for_status()
                return response
            reason = f"HTTP {response.status_code}"
            response.close()
        delay = 2 ** (attempt + 1)
        print(
            f"BikeReg event {event_id}: {reason}; retry {attempt + 1}/3 in {delay}s",
            file=sys.stderr,
        )
        time.sleep(delay)
