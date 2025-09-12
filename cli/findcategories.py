#!/usr/bin/env python3

import sys
import os
import csv
import json
import io
from collections import OrderedDict
import re

# Required DB access for category validation
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from libs.racedbsql import RaceDBSQL


def _decode_csv_bytes(data: bytes) -> str:
    """Decode CSV bytes using a set of likely encodings, preferring UTF-8.
    Falls back to cp1252/latin-1 for CCN exports with characters like 'é'.
    """
    encodings = [
        'utf-8-sig',
        'utf-8',
        'cp1252',  # Windows-1252
        'latin-1',
    ]
    last_err = None
    for enc in encodings:
        try:
            return data.decode(enc)
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err or UnicodeDecodeError('utf-8', data, 0, 1, 'unable to decode')


def _sniff_dialect(sample_text: str) -> csv.Dialect:
    """Sniff CSV dialect; prefer comma or tab. Provide safe fallback."""
    sniffer = csv.Sniffer()
    sample = sample_text[:8192]
    try:
        dialect = sniffer.sniff(sample, delimiters=",\t;")
        return dialect
    except Exception:
        # Simple heuristic: choose delimiter with higher count
        c_comma = sample.count(',')
        c_tab = sample.count('\t')
        delim = '\t' if c_tab > c_comma else ','
        # Create a simple dialect dynamically with chosen delimiter
        Fallback = type(
            'FallbackDialect',
            (csv.Dialect,),
            dict(
                delimiter=delim,
                quotechar='"',
                escapechar=None,
                doublequote=True,
                skipinitialspace=False,
                lineterminator='\n',
                quoting=csv.QUOTE_MINIMAL,
            ),
        )
        return Fallback()


def read_unique_labels(csv_path: str, column: str):
    """Return sorted unique labels from the target CSV column.
    Handles UTF-8 and CP1252 encodings, comma or tab delimiters, and ignores trailing summaries.
    """
    path = csv_path

    try:
        with open(path, 'rb') as fb:
            raw = fb.read()
        text = _decode_csv_bytes(raw)
        dialect = _sniff_dialect(text)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if column not in (reader.fieldnames or []):
            print(
                f"Error: CSV missing required column '{column}'. Found: {reader.fieldnames}",
                file=sys.stderr,
            )
            sys.exit(2)

        values = set()
        for row in reader:
            # Stop/ignore lines from summary tails which often have free-form text
            first_vals = [v for v in row.values() if v]
            if first_vals:
                first_cell = str(first_vals[0]).strip().lower()
                if first_cell.startswith('complete registrations for') or first_cell.startswith('filters'):
                    break

            label = (row.get(column) or '').strip()
            if label:
                values.add(label)

    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(4)

    return sorted(values)


def write_merged_catmap(
    format_name: str,
    labels: list[str],
    allowed_codes: set[str] | None = None,
    output_path: str | None = None,
) -> tuple[OrderedDict, list[str]]:
    """Merge labels into catmap/<format>.json as { label: [normalized_category, gender] } mapping.

    - Creates the file if it does not exist.
    - If an older structured file is found (with label_aliases), converts it to a simple mapping.
    - Does not overwrite existing keys; adds missing ones with extracted (category, gender).
    Returns the merged OrderedDict mapping and writes it to disk.
    """
    if output_path:
        base_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
        os.makedirs(base_dir, exist_ok=True)
        target = os.path.abspath(output_path)
    else:
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
            cat = f"FIX {cat}"
        proposed[lbl] = [cat, gen]

    # Merge labels (preserve existing values)
    merged = OrderedDict()
    new_keys = sorted(set(labels) - set(existing.keys()))
    for k in sorted(set(existing.keys()) | set(labels)):
        if k in existing:
            merged[k] = existing[k]
        else:
            merged[k] = proposed.get(k, ["", ""])  # fallback if any

    # Write back with pretty object formatting and inline array values
    def _dump_inline_arrays(mapping: OrderedDict, fp):
        fp.write('{' + "\n")
        items = list(mapping.items())
        for idx, (k, v) in enumerate(items):
            # v expected to be [category, gender]
            cat = v[0] if isinstance(v, (list, tuple)) and len(v) > 0 else ""
            gen = v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ""
            line = (
                "  "
                + json.dumps(k, ensure_ascii=False)
                + ": [ "
                + json.dumps(cat, ensure_ascii=False)
                + ", "
                + json.dumps(gen, ensure_ascii=False)
                + " ]"
            )
            if idx < len(items) - 1:
                line += ","
            fp.write(line + "\n")
        fp.write('}' + "\n")

    with open(target, "w", encoding="utf-8") as f:
        _dump_inline_arrays(merged, f)

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
    if not gender:
        gender = "Open"
    return normalized, gender


def main():
    # Modes:
    # - One positional arg (CSV): emit mapping to stdout.
    # - Two positional args (format, CSV): merge into catmap/<format>.json and report added keys.
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Extract categories from registration CSV (BikeReg or CCN) and optionally "
            "merge into a mapping with validation. Two-arg modes supported: "
            "(1) format_name CSV -> merges into catmap/<format_name>.json; "
            "(2) CSV output.json -> merges or creates output.json."
        )
    )
    parser.add_argument("arg1", help="CSV path (mode 2) or category_format (mode 1)")
    parser.add_argument("arg2", nargs="?", help="CSV path (mode 1) or output JSON path (mode 2)")
    grp = parser.add_mutually_exclusive_group(required=False)
    grp.add_argument("--bikereg", action="store_true", help="CSV is from BikeReg (uses 'Category Entered / Merchandise Ordered')")
    grp.add_argument("--ccnreg", action="store_true", help="CSV is from CCN (uses 'Category')")
    parser.add_argument("--host", default="localhost", help="DB host for category validation")
    parser.add_argument("--name", default=None, help="Competition name for validation")
    parser.add_argument("--date", default=None, help="Competition date (YYYY-MM-DD) for validation")
    parser.add_argument("--format", dest="fmt", default=None, help="Category format name for validation when not merging")

    args = parser.parse_args()

    # Determine source CSV column for category labels
    if args.bikereg:
        category_column = 'Category Entered / Merchandise Ordered'
    elif args.ccnreg:
        category_column = 'Category'
    else:
        # argparse ensures one is provided; this is a guard
        print("Error: one of --bikereg or --ccnreg is required", file=sys.stderr)
        sys.exit(2)

    # Work out mode and determine validation source
    csv_first_mode = False
    merge_mode = args.arg2 is not None
    if merge_mode:
        # Heuristic: if arg1 points to an existing file, treat as CSV-first mode
        if os.path.isfile(args.arg1):
            csv_first_mode = True

    # Load allowed category codes from DB if possible, based on mode
    allowed_codes = None
    if RaceDBSQL is None:
        print("Warning: RaceDBSQL not available; skipping validation", file=sys.stderr)
    else:
        try:
            db = RaceDBSQL(host=args.host)
            if merge_mode:
                if csv_first_mode:
                    # Validation by --format or --name/--date in this mode
                    if args.fmt:
                        print(f"Merge mode (CSV, output): validate by --format = {args.fmt}", file=sys.stderr)
                        _fmt, cats = db.find_categories_for_format_name(args.fmt)
                        allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                        print(f"Loaded {len(allowed_codes)} categories for format {args.fmt}", file=sys.stderr)
                    elif args.name or args.date:
                        print(
                            f"Merge mode (CSV, output): validate by competition --name={args.name} --date={args.date}",
                            file=sys.stderr,
                        )
                        _comp, cats = db.find_competition_categories(name=args.name, date=args.date)
                        allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                        print(f"Loaded {len(allowed_codes)} categories from competition", file=sys.stderr)
                    else:
                        print("Warning: no --format or --name/--date provided; skipping validation", file=sys.stderr)
                else:
                    # Original mode: validate by format name (arg1)
                    print(f"Merge mode (format, CSV): validate by format name = {args.arg1}", file=sys.stderr)
                    _fmt, cats = db.find_categories_for_format_name(args.arg1)
                    allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                    print(f"Loaded {len(allowed_codes)} categories for format {args.arg1}", file=sys.stderr)
            else:
                if args.fmt:
                    print(f"One-arg mode: validate by format name --format = {args.fmt}", file=sys.stderr)
                    _fmt, cats = db.find_categories_for_format_name(args.fmt)
                    allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                    print(f"Loaded {len(allowed_codes)} categories for format {args.fmt}", file=sys.stderr)
                elif args.name or args.date:
                    print(f"One-arg mode: validate by competition name/date --name={args.name} --date={args.date}", file=sys.stderr)
                    _comp, cats = db.find_competition_categories(name=args.name, date=args.date)
                    allowed_codes = {c.get('code') for c in cats if isinstance(c, dict) and c.get('code')}
                    print(f"Loaded {len(allowed_codes)} categories from competition", file=sys.stderr)
                else:
                    print("Warning: no --format or --name/--date provided; skipping validation", file=sys.stderr)
        except Exception as e:
            print(f"Warning: failed to fetch categories: {e}", file=sys.stderr)

    print(f"Allowed codes: {sorted(allowed_codes) if allowed_codes is not None else 'None'}", file=sys.stderr)
    if args.arg2 is None:
        # One-arg mode: output mapping to stdout
        labels = read_unique_labels(args.arg1, category_column)
        mapping = OrderedDict()
        for label in labels:
            cat, gen = extract_category_gender(label)
            if allowed_codes is not None and cat not in allowed_codes:
                cat = f"FIX {cat}"
            mapping[label] = [cat, gen]
        json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    else:
        # Two-arg merge modes
        if csv_first_mode:
            # Mode 2: CSV then output JSON path
            csv_path, output_path = args.arg1, args.arg2
            if not output_path:
                print("Error: output JSON path (arg2) is required in CSV-first mode", file=sys.stderr)
                sys.exit(2)
            labels = read_unique_labels(csv_path, category_column)
            # Format name for bookkeeping; if an explicit output path is used, allow a generic name
            fmt_name = os.path.splitext(os.path.basename(output_path))[0] or "categories"
            merged, added = write_merged_catmap(fmt_name, labels, allowed_codes=allowed_codes, output_path=output_path)
            print(f"Added {len(added)} keys to {os.path.abspath(output_path)}")
            for k in added:
                print(k)
            return
        else:
            # Mode 1: format then CSV (original behavior)
            format_name, csv_path = args.arg1, args.arg2
            labels = read_unique_labels(csv_path, category_column)
            merged, added = write_merged_catmap(format_name, labels, allowed_codes=allowed_codes)
            target_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "catmap", f"{format_name}.json"))
            print(f"Added {len(added)} keys to {target_path}")
            for k in added:
                print(k)
            return


if __name__ == '__main__':
    main()
