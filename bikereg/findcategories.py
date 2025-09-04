#!/usr/bin/env python3

import sys
import os
import csv
import json
from collections import OrderedDict
import re

# Required DB access for category validation
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from libs.racedbsql import RaceDBSQL


COLUMN = 'Category Entered / Merchandise Ordered'


def read_unique_labels(csv_path: str):
    """Return sorted unique labels from the target CSV column."""
    path = csv_path

    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if COLUMN not in (reader.fieldnames or []):
                print(
                    f"Error: CSV missing required column '{COLUMN}'. Found: {reader.fieldnames}",
                    file=sys.stderr,
                )
                sys.exit(2)

            values = set()
            for row in reader:
                label = (row.get(COLUMN) or '').strip()
                if label:
                    values.add(label)

    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(4)

    return sorted(values)


def write_merged_catmap(format_name: str, labels: list[str], allowed_codes: set[str] | None = None) -> tuple[OrderedDict, list[str]]:
    """Merge labels into catmap/<format>.json as { label: [normalized_category, gender] } mapping.

    - Creates the file if it does not exist.
    - If an older structured file is found (with label_aliases), converts it to a simple mapping.
    - Does not overwrite existing keys; adds missing ones with extracted (category, gender).
    Returns the merged OrderedDict mapping and writes it to disk.
    """
    base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "catmap"))
    os.makedirs(base_dir, exist_ok=True)
    target = os.path.join(base_dir, f"{format_name}.json")

    existing = {}
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if "label_aliases" in data:
                    # Convert old structure to simple mapping
                    existing = {a[0]: (a[2] if len(a) > 2 else "") for a in data.get("label_aliases", []) if a}
                else:
                    existing = data
            else:
                existing = {}
        except Exception:
            existing = {}

    # Prepare proposed values for new labels with optional validation against allowed codes
    proposed = {}
    for lbl in labels:
        cat, gen = extract_category_gender(lbl)
        if allowed_codes is not None and cat not in allowed_codes:
            cat = f"{cat} FIX"
        proposed[lbl] = [cat, gen]

    # Merge labels (preserve existing values)
    merged = OrderedDict()
    new_keys = sorted(set(labels) - set(existing.keys()))
    for k in sorted(set(existing.keys()) | set(labels)):
        if k in existing:
            merged[k] = existing[k]
        else:
            merged[k] = proposed.get(k, ["", ""])  # fallback if any

    # Write back
    with open(target, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return merged, new_keys


def extract_category_gender(label: str) -> tuple[str, str]:
    """Extract a normalized (category, gender) from an organizer label.

    Gender detection (case-insensitive): Men, Male, Boys -> Men; Women, Female, Girls -> Women; Open, O -> Open; M -> Men; F -> Women.
    Removes detected gender token from the label, then normalizes spaces and punctuation.
    Returns (normalized_category, gender_str_or_empty).
    """
    text = label or ""
    src = text
    gender = ""

    # 1) Handle possessive first (Men's / Women's)
    if re.search(r"\bmen'?s\b", text, flags=re.IGNORECASE):
        gender = "Men"
        text = re.sub(r"\bmen'?s\b", "", text, flags=re.IGNORECASE)
    elif re.search(r"\bwomen'?s\b", text, flags=re.IGNORECASE):
        gender = "Women"
        text = re.sub(r"\bwomen'?s\b", "", text, flags=re.IGNORECASE)
    else:
        # 2) Prefer word tokens Men/Women/Male/Female/Boys/Girls
        word_map = {
            "men": "Men",
            "male": "Men",
            "boys": "Men",
            "women": "Women",
            "female": "Women",
            "girls": "Women",
        }
        m = re.search(r"\b(men|male|boys|women|female|girls)\b", text, flags=re.IGNORECASE)
        if m:
            gender = word_map[m.group(1).lower()]
            start, end = m.span()
            text = (text[:start] + text[end:]).strip()
        else:
            # 3) Single-letter tokens M/F
            m = re.search(r"\b(m|f)\b", text, flags=re.IGNORECASE)
            if m:
                gender = "Men" if m.group(1).lower() == "m" else "Women"
                start, end = m.span()
                text = (text[:start] + text[end:]).strip()
            else:
                # 4) Open tokens
                m = re.search(r"\b(open|o)\b", text, flags=re.IGNORECASE)
                if m:
                    gender = "Open"
                    start, end = m.span()
                    text = (text[:start] + text[end:]).strip()

    # If we determined Men/Women, also remove stray 'Open' tokens remaining
    if gender in ("Men", "Women"):
        text = re.sub(r"\b(open|o)\b", "", text, flags=re.IGNORECASE)

    # Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)
    # Normalize spaces around slashes and commas
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    # Clean stray spaces before punctuation
    text = re.sub(r"\s+([,/])", r" \1", text)

    normalized = text.strip()
    # Remove surrounding parentheses if they contain the whole string
    mpar = re.fullmatch(r"\((.*)\)", normalized)
    if mpar:
        normalized = mpar.group(1).strip()
    return normalized, gender


def main():
    # Modes:
    # - One positional arg (CSV): emit mapping to stdout.
    # - Two positional args (format, CSV): merge into catmap/<format>.json and report added keys.
    import argparse

    parser = argparse.ArgumentParser(description="Extract BikeReg categories and optionally merge into catmap with validation.")
    parser.add_argument("arg1", help="CSV path, or category_format when merging")
    parser.add_argument("arg2", nargs="?", help="CSV path when merging")
    parser.add_argument("--host", default="localhost", help="DB host for category validation")
    parser.add_argument("--name", default=None, help="Competition name for validation")
    parser.add_argument("--date", default=None, help="Competition date (YYYY-MM-DD) for validation")
    parser.add_argument("--format", dest="fmt", default=None, help="Category format name for validation when not merging")

    args = parser.parse_args()

    # Load allowed category codes from DB if possible
    allowed_codes = None
    if RaceDBSQL is None:
        print("Warning: RaceDBSQL not available; skipping validation", file=sys.stderr)
    else:
        try:
            db = RaceDBSQL(host=args.host)
            if args.arg2 is not None:
                # Merge mode: validate by format name (arg1)
                fmt, cats = db.find_categories_for_format_name(args.arg1)
                allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                print(f"Loaded {len(allowed_codes)} categories for format {args.arg1}", file=sys.stderr)
            elif args.fmt:
                fmt, cats = db.find_categories_for_format_name(args.fmt)
                allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                print(f"Loaded {len(allowed_codes)} categories for format {args.fmt}", file=sys.stderr)
            elif args.name or args.date:
                comp, cats = db.find_competition_categories(name=args.name, date=args.date)
                allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                print(f"Loaded {len(allowed_codes)} categories from competition", file=sys.stderr)
        except Exception as e:
            print(f"Warning: failed to fetch categories: {e}", file=sys.stderr)

    print(f"Allowed codes: {sorted(allowed_codes) if allowed_codes is not None else 'None'}", file=sys.stderr)
    if args.arg2 is None:
        # One-arg mode: output mapping to stdout
        labels = read_unique_labels(args.arg1)
        mapping = OrderedDict()
        for label in labels:
            cat, gen = extract_category_gender(label)
            if allowed_codes is not None and cat not in allowed_codes:
                cat = f"{cat} FIX"
            mapping[label] = [cat, gen]
        json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    else:
        # Two-arg merge mode
        format_name, csv_path = args.arg1, args.arg2
        labels = read_unique_labels(csv_path)
        merged, added = write_merged_catmap(format_name, labels, allowed_codes=allowed_codes)
        print(f"Added {len(added)} keys to catmap/{format_name}.json")
        for k in added:
            print(k)
        return


if __name__ == '__main__':
    main()
