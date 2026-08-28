import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests


LOGIN_URL_CANDIDATES = [
    "https://www.bikereg.com/api/director/PromoterLogin?escaped=false",
    "https://www.bikereg.com/api/director/PromoterLogin",
]

DEFAULT_REG_URL = "https://www.bikereg.com/api/director/EventEntries?escaped=false"
CSV_HEADERS = [
    "Last Name",
    "First Name",
    "Gender",
    "Date of Birth",
    "UCI Code",
    "Category Entered",
    "Team",
    "Phone",
    "Email",
    "Emergency Phone",
    "State",
    "City",
    "ZIP",
    "Emergency Contact",
    "Transaction Type",
    "MerchSummary",
]
TRANSACTION_LABEL_MAP = {"0": "Reg", "1": "Merch", "Reg": "Reg", "Merch": "Merch"}


def clean_text(v):
    if v in (None, ""):
        return ""
    s = str(v).strip()
    # Match BikeReg CSV entity style used in downloaded participant files.
    s = s.replace("\u00a0", "&nbsp;")
    s = re.sub(r"&(?!#?[a-zA-Z0-9]+;)", "&amp;", s)
    return s


def login(session, username, password, timeout=15):
    creds = {"username": username, "password": password}

    for login_url in LOGIN_URL_CANDIDATES:
        try:
            response = session.post(login_url, json=creds, timeout=timeout)
            print(f"Login URL: {login_url} -> {response.status_code}")
        except requests.RequestException as exc:
            print(f"Login request failed for {login_url}: {exc}", file=sys.stderr)
            continue

        if response.status_code == 404:
            continue

        try:
            response.raise_for_status()
            full_response = response.json()
        except requests.RequestException as exc:
            print(f"Login error at {login_url}: {exc}", file=sys.stderr)
            continue
        except ValueError:
            print(f"Login at {login_url} returned non-JSON body.", file=sys.stderr)
            continue

        # Some endpoints return escaped JSON as a string, even with JSON content type.
        if isinstance(full_response, str):
            try:
                full_response = json.loads(full_response)
            except ValueError:
                print(f"Login at {login_url} returned JSON string that could not be parsed.", file=sys.stderr)
                continue

        if not isinstance(full_response, dict):
            print(f"Unexpected login response type: {type(full_response).__name__}", file=sys.stderr)
            continue

        login_data = (
            full_response.get("PromoterLoginV2Result")
            or full_response.get("PromoterLoginResult")
            or full_response
        )
        if not isinstance(login_data, dict):
            print(f"Unexpected login result payload type: {type(login_data).__name__}", file=sys.stderr)
            continue

        auth_token = login_data.get("authToken") or login_data.get("token")
        promoter_id = login_data.get("promoterID")
        if auth_token:
            return auth_token, promoter_id, login_url, login_data

        print(f"Login response missing auth token: {login_data}", file=sys.stderr)

    return None, None, None, None


def fetch_registrations(session, reg_url, auth_token, event_id, timeout=15):
    payload = {"token": auth_token, "eventID": event_id}
    response = session.post(reg_url, json=payload, timeout=timeout)
    response.raise_for_status()
    raw = response.json()
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def extract_entries(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    def _extract_from_obj(obj):
        if isinstance(obj, list):
            return obj
        if isinstance(obj, str):
            try:
                parsed = json.loads(obj)
            except ValueError:
                return []
            return _extract_from_obj(parsed)
        if not isinstance(obj, dict):
            return []

        for nested_key in ("entries", "eventEntries", "rows", "items"):
            nested = obj.get(nested_key)
            if isinstance(nested, (list, dict, str)):
                rows = _extract_from_obj(nested)
                if rows:
                    return rows
        return []

    # Handle the common wrapped response shapes.
    for key in (
        "EventEntriesV2Result",
        "EventEntriesResult",
        "GetEventEntriesV2Result",
        "GetEventEntriesResult",
        "eventEntries",
        "entries",
        "result",
    ):
        rows = _extract_from_obj(payload.get(key))
        if rows:
            return rows

    # Fallback: try any "*Result" key for providers that rename wrappers.
    for key, value in payload.items():
        if key.lower().endswith("result"):
            rows = _extract_from_obj(value)
            if rows:
                return rows
    return []


def summarize_entries(entries, max_sample=3):
    transaction_label_map = {
        "0": "Reg",
        "1": "Merch",
        "Reg": "Reg",
        "Merch": "Merch",
    }

    def normalize_transaction_type(value):
        raw = str(value)
        return raw, transaction_label_map.get(raw, raw)

    transaction_counts = {}
    transaction_labels = {}
    top_keys = set()
    user_info_keys = set()

    for row in entries:
        if not isinstance(row, dict):
            continue
        top_keys.update(row.keys())
        txn_raw, txn_label = normalize_transaction_type(row.get("TransactionType", "UNKNOWN"))
        transaction_counts[txn_raw] = transaction_counts.get(txn_raw, 0) + 1
        transaction_labels[txn_raw] = txn_label
        user_info = row.get("UserInfo")
        if isinstance(user_info, dict):
            user_info_keys.update(user_info.keys())

    reg_entries = []
    for r in entries:
        if not isinstance(r, dict):
            continue
        _, txn_label = normalize_transaction_type(r.get("TransactionType", "UNKNOWN"))
        if txn_label == "Reg":
            reg_entries.append(r)

    print(f"Entry rows: {len(entries)}")
    print("TransactionType counts (raw -> normalized):")
    for key in sorted(transaction_counts):
        print(f"  {key} ({transaction_labels.get(key, key)}): {transaction_counts[key]}")
    print(f"Participant rows (normalized TransactionType == Reg): {len(reg_entries)}")
    print(f"Top-level keys ({len(top_keys)}): {sorted(top_keys)}")
    print(f"UserInfo keys ({len(user_info_keys)}): {sorted(user_info_keys)}")

    if reg_entries:
        print(f"Sample Reg rows (max {max_sample}):")
        for row in reg_entries[:max_sample]:
            user_info = row.get("UserInfo") if isinstance(row.get("UserInfo"), dict) else {}
            first_name = user_info.get("FirstName") or user_info.get("firstName") or user_info.get("firstname")
            last_name = user_info.get("LastName") or user_info.get("lastName") or user_info.get("lastname")
            category = row.get("CategoryName")
            race_id = row.get("RaceID")
            print(f"  RaceID={race_id}, Name={first_name} {last_name}, Category={category}")


def row_to_csv_dict(row):
    user_info = row.get("UserInfo") if isinstance(row.get("UserInfo"), dict) else {}
    txn_raw = str(row.get("TransactionType", ""))
    txn_type = TRANSACTION_LABEL_MAP.get(txn_raw, txn_raw)

    return {
        "Last Name": clean_text(user_info.get("LastName", "")),
        "First Name": clean_text(user_info.get("FirstName", "")),
        "Gender": clean_text(user_info.get("Gender", "")),
        "Date of Birth": format_dob(user_info.get("DOB", "")),
        "UCI Code": clean_text(user_info.get("UCIID", "")),
        "Category Entered": clean_text(row.get("CategoryName", "")),
        "Team": clean_text(user_info.get("Team", "")),
        "Phone": clean_text(user_info.get("Phone", "")),
        "Email": clean_text(user_info.get("Email", "")),
        "Emergency Phone": clean_text(user_info.get("EmergencyContactPhone", "")),
        "State": clean_text(user_info.get("State", "")),
        "City": clean_text(user_info.get("City", "")),
        "ZIP": clean_text(user_info.get("ZIP", "")),
        "Emergency Contact": clean_text(user_info.get("EmergencyContactName", "")),
        "Transaction Type": txn_type,
        "MerchSummary": "",
    }


def format_dob(value):
    if value in (None, ""):
        return ""

    s = str(value).strip()
    # BikeReg commonly returns .NET JSON date format: /Date(1027137600000-0400)/
    m = re.match(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$", s)
    if m:
        try:
            dt = datetime.fromtimestamp(int(m.group(1)) / 1000.0, tz=timezone.utc)
            return f"{dt.month}/{dt.day}/{dt.year}"
        except (ValueError, OSError):
            return s

    # Already in ISO format.
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return f"{dt.month}/{dt.day}/{dt.year}"
    except ValueError:
        pass

    # Already slash-delimited. Normalize any leading zeroes.
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}/{m.group(3)}"

    return s


def get_entry_key(row):
    user_info = row.get("UserInfo") if isinstance(row.get("UserInfo"), dict) else {}
    confirmation = str(row.get("ConfirmationNumber", "")).strip()
    eid = str(row.get("EID", "")).strip()
    race_id = str(row.get("RaceID", "")).strip()
    return {
        "confirmation": confirmation,
        "eid": eid,
        "race_id": race_id,
        "identity": (
            str(user_info.get("LastName", "")).strip().lower(),
            str(user_info.get("FirstName", "")).strip().lower(),
            str(user_info.get("DOB", "")).strip(),
            str(user_info.get("Email", "")).strip().lower(),
        ),
        "identity_weak": (
            str(user_info.get("LastName", "")).strip().lower(),
            str(user_info.get("FirstName", "")).strip().lower(),
            str(user_info.get("DOB", "")).strip(),
        ),
    }


def merch_item_text(row):
    category = str(row.get("CategoryName", "")).strip()
    qty = row.get("Quantity")
    try:
        qty_int = int(qty)
    except (TypeError, ValueError):
        qty_int = 1
    label = category or "Merch"
    return f"({qty_int}) {label}"


def merge_entries_for_csv(entries):
    reg_rows = {}
    reg_order = []
    merch_by_person = {}

    def parse_last_modified(row):
        value = row.get("LastModified")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return float("-inf")
            m = re.match(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$", v)
            if m:
                try:
                    return float(int(m.group(1)))
                except ValueError:
                    return float("-inf")
            try:
                # Accept common ISO-ish timestamps.
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp() * 1000.0
            except ValueError:
                return float("-inf")
        return float("-inf")

    def is_removed_registration(row):
        category = str(row.get("CategoryName", "")).strip().lower()
        return category == "removed registration"

    def choose_better_reg(existing, candidate):
        # Prefer a non-removed category over a "Removed Registration" placeholder row.
        if is_removed_registration(existing) and not is_removed_registration(candidate):
            return candidate
        if not is_removed_registration(existing) and is_removed_registration(candidate):
            return existing

        # Otherwise use newest LastModified if available.
        if parse_last_modified(candidate) > parse_last_modified(existing):
            return candidate
        return existing

    # 1) Build canonical registration rows keyed by person identity so
    # multiple participants under one confirmation do not collapse.
    for row in entries:
        if not isinstance(row, dict):
            continue
        txn = TRANSACTION_LABEL_MAP.get(str(row.get("TransactionType", "")), str(row.get("TransactionType", "")))
        key_info = get_entry_key(row)
        person_key = ("identity",) + key_info["identity"]
        if txn == "Reg":
            if is_removed_registration(row):
                # Match BikeReg participant CSV behavior: drop removed registrations.
                continue
            if person_key not in reg_rows:
                reg_rows[person_key] = row
                reg_order.append(person_key)
            else:
                reg_rows[person_key] = choose_better_reg(reg_rows[person_key], row)

    # 2) Build indexes from canonical reg rows for merch linkage fallback.
    reg_by_confirmation = {}
    reg_by_eid = {}
    reg_by_race_id = {}
    reg_by_identity_weak = {}
    for person_key in reg_order:
        row = reg_rows[person_key]
        key_info = get_entry_key(row)
        if key_info["confirmation"]:
            reg_by_confirmation.setdefault(key_info["confirmation"], set()).add(person_key)
        if key_info["eid"]:
            reg_by_eid.setdefault(key_info["eid"], set()).add(person_key)
        if key_info["race_id"]:
            reg_by_race_id.setdefault(key_info["race_id"], set()).add(person_key)
        reg_by_identity_weak.setdefault(("identity_weak",) + key_info["identity_weak"], set()).add(person_key)

    # 3) Attach merch rows to canonical reg rows without relying on adjacency.
    for row in entries:
        if not isinstance(row, dict):
            continue
        txn = TRANSACTION_LABEL_MAP.get(str(row.get("TransactionType", "")), str(row.get("TransactionType", "")))
        if txn != "Merch":
            continue
        key_info = get_entry_key(row)

        candidates = []
        strong_person_key = ("identity",) + key_info["identity"]
        weak_person_key = ("identity_weak",) + key_info["identity_weak"]

        if strong_person_key in reg_rows:
            candidates = [strong_person_key]
        elif weak_person_key in reg_by_identity_weak and len(reg_by_identity_weak[weak_person_key]) == 1:
            candidates = list(reg_by_identity_weak[weak_person_key])
        elif key_info["eid"] and key_info["eid"] in reg_by_eid and len(reg_by_eid[key_info["eid"]]) == 1:
            candidates = list(reg_by_eid[key_info["eid"]])
        elif key_info["race_id"] and key_info["race_id"] in reg_by_race_id and len(reg_by_race_id[key_info["race_id"]]) == 1:
            candidates = list(reg_by_race_id[key_info["race_id"]])
        elif (
            key_info["confirmation"]
            and key_info["confirmation"] in reg_by_confirmation
            and len(reg_by_confirmation[key_info["confirmation"]]) == 1
        ):
            candidates = list(reg_by_confirmation[key_info["confirmation"]])

        if candidates:
            merch_by_person.setdefault(candidates[0], []).append(merch_item_text(row))

    merged = []
    for person_key in reg_order:
        out = row_to_csv_dict(reg_rows[person_key])
        items = merch_by_person.get(person_key, [])
        out["MerchSummary"] = ", ".join(items)
        merged.append(out)
    return merged


def write_csv(entries, csv_out):
    merged_rows = merge_entries_for_csv(entries)
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(merged_rows)
    return len(merged_rows)


def main():
    parser = argparse.ArgumentParser(description="Test BikeReg API login/fetch flow")
    parser.add_argument("--username", default=os.getenv("BIKEREG_USERNAME"))
    parser.add_argument("--password", default=os.getenv("BIKEREG_PASSWORD"))
    parser.add_argument("--event-id", type=int, default=74060)
    parser.add_argument("--reg-url", default=DEFAULT_REG_URL)
    parser.add_argument("--csv-out", help="Write entries to CSV using BikeReg-like headers")
    parser.add_argument("--dump-json", action="store_true", help="Print full JSON response")
    parser.add_argument("--max-sample", type=int, default=3, help="Number of sample Reg rows to print")
    args = parser.parse_args()

    if not args.username or not args.password:
        print("Set --username/--password or BIKEREG_USERNAME/BIKEREG_PASSWORD.", file=sys.stderr)
        return 2

    session = requests.Session()
    auth_token, promoter_id, login_url, login_data = login(session, args.username, args.password)
    if not auth_token:
        print("Could not obtain auth token from any known login endpoint.", file=sys.stderr)
        return 1

    print(f"Logged in via {login_url}. Promoter ID: {promoter_id}")
    print(f"Login payload keys: {sorted(login_data.keys())}")

    try:
        registrations = fetch_registrations(
            session=session,
            reg_url=args.reg_url,
            auth_token=auth_token,
            event_id=args.event_id,
        )
    except requests.RequestException as exc:
        print(f"Registration fetch failed at {args.reg_url}: {exc}", file=sys.stderr)
        return 1
    except ValueError:
        print(f"Registration fetch returned non-JSON body from {args.reg_url}", file=sys.stderr)
        return 1

    entries = extract_entries(registrations)
    print(f"Registrations response type: {type(registrations).__name__}")
    if isinstance(registrations, dict):
        print(f"Registrations top-level keys: {sorted(registrations.keys())}")
    if entries:
        summarize_entries(entries, max_sample=args.max_sample)
        if args.csv_out:
            count = write_csv(entries, args.csv_out)
            print(f"Wrote CSV: {args.csv_out} ({count} merged Reg rows)")
    else:
        print("Could not identify entry rows in response shape.")

    if args.dump_json:
        print(json.dumps(registrations, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
