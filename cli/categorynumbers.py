#!/usr/bin/env python3

import sys
import os
import argparse
from typing import Dict, List, Tuple, Optional
import re

# repo root for libs import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from libs.racedbsql import RaceDBSQL  # type: ignore


def find_competition(db: RaceDBSQL, name: Optional[str], date: Optional[str]):
    comp, _ = db.find_competition_categories(name=name, date=date)
    if not comp:
        raise SystemExit("Competition not found (use --name or --date)")
    return comp


def fetch_categorynumbers(db: RaceDBSQL, competition_id: int) -> List[Dict]:
    q = (
        "SELECT cn.id AS cn_id, cn.range_str, c.code AS category_code "
        "FROM core_categorynumbers cn "
        "JOIN core_categorynumbers_categories cnc ON cnc.categorynumbers_id = cn.id "
        "JOIN core_category c ON c.id = cnc.category_id "
        "WHERE cn.competition_id = %s "
        "ORDER BY c.code, cn.id"
    )
    db.cur_execute("Fetch categorynumbers", q, (competition_id,), debug=False)
    return db.cur.fetchall() or []


def get_code_to_id(db: RaceDBSQL, format_id: int) -> Dict[str, int]:
    q = "SELECT id, code FROM core_category WHERE format_id = %s;"
    db.cur_execute("Fetch categories for format", q, (format_id,), debug=False)
    rows = db.cur.fetchall() or []
    mapping: Dict[str, int] = {}
    for r in rows:
        cid = r.get("id") if isinstance(r, dict) else r[0]
        code = r.get("code") if isinstance(r, dict) else r[1]
        mapping[str(code)] = int(cid)
    return mapping


def fetch_categories_for_format(db: RaceDBSQL, format_id: int) -> List[Dict]:
    q = "SELECT id, code, sequence FROM core_category WHERE format_id = %s ORDER BY sequence, code;"
    db.cur_execute("Fetch all categories in format", q, (format_id,), debug=False)
    return db.cur.fetchall() or []


def sanitize_filename(name: str) -> str:
    # Replace spaces with underscores and remove invalid characters
    s = name.replace(" ", "_")
    # Allow letters, digits, underscore, hyphen, dot
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    return s or "competition"


def normalize_ranges(range_list: List[str]) -> str:
    parts = [p.strip() for p in range_list if str(p).strip()]
    # keep order but deduplicate
    seen = set()
    norm = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            norm.append(p)
    return ",".join(norm)


def download_xlsx(db: RaceDBSQL, comp: Dict, output_path: str) -> None:
    try:
        from openpyxl import Workbook
    except Exception as e:
        raise SystemExit(f"openpyxl not available: {e}")

    rows = fetch_categorynumbers(db, comp["id"])
    # Track codes we wrote from existing categorynumbers
    present_codes = []

    wb = Workbook()
    ws = wb.active
    # No header per example; write rows as Category, Range1, Range2, ...
    for r in rows:
        code = r.get("category_code") if isinstance(r, dict) else r[2]
        range_str = r.get("range_str") if isinstance(r, dict) else r[1]
        ranges = [p.strip() for p in str(range_str or "").split(",") if p.strip()]
        ws.append([code] + ranges)
        present_codes.append(code)

    # Ensure a line for each category in the format, even if no ranges
    all_cats = fetch_categories_for_format(db, comp["category_format_id"])
    for cat in all_cats:
        code = cat.get("code") if isinstance(cat, dict) else cat[1]
        if code not in present_codes:
            ws.append([code])

    wb.save(output_path)
    print(f"Wrote {ws.max_row} rows to {output_path}")


def upload_xlsx(db: RaceDBSQL, comp: Dict, input_path: str, replace: bool = False, dry_run: bool = False) -> None:
    try:
        from openpyxl import load_workbook
    except Exception as e:
        raise SystemExit(f"openpyxl not available: {e}")

    wb = load_workbook(input_path)
    ws = wb.active

    # Build code->ranges mapping (normalized) and group by ranges
    range_to_codes: Dict[str, List[str]] = {}
    for row in ws.iter_rows(values_only=True):
        if not row or not row[0]:
            continue
        code = str(row[0]).strip()
        ranges = [str(c).strip() for c in row[1:] if c is not None and str(c).strip()]
        if not ranges:
            continue
        norm = normalize_ranges(ranges)
        range_to_codes.setdefault(norm, []).append(code)

    if replace:
        # Delete existing links and numbers for this competition
        db.cur_execute(
            "Delete existing core_categorynumbers_categories",
            "DELETE FROM core_categorynumbers_categories WHERE categorynumbers_id IN (SELECT id FROM core_categorynumbers WHERE competition_id = %s);",
            (comp["id"],),
            debug=False,
        )
        db.cur_execute(
            "Delete existing core_categorynumbers",
            "DELETE FROM core_categorynumbers WHERE competition_id = %s;",
            (comp["id"],),
            debug=False,
        )

    # Fetch category code -> id map
    code_to_id = get_code_to_id(db, comp["category_format_id"])

    inserted_cn = 0
    inserted_links = 0
    for range_str, codes in range_to_codes.items():
        # Create or find existing numbers row for this competition and range_str
        db.cur_execute(
            "Find existing numbers row",
            "SELECT id FROM core_categorynumbers WHERE competition_id = %s AND range_str = %s;",
            (comp["id"], range_str),
            debug=False,
        )
        row = db.cur.fetchone()
        if row:
            cn_id = row.get("id") if isinstance(row, dict) else row[0]
        else:
            db.cur_execute(
                "Insert numbers row",
                "INSERT INTO core_categorynumbers (range_str, competition_id) VALUES (%s, %s) RETURNING id;",
                (range_str, comp["id"]),
                debug=False,
            )
            r = db.cur.fetchone()
            cn_id = r.get("id") if isinstance(r, dict) else r[0]
            inserted_cn += 1

        # Link to categories
        for code in codes:
            cat_id = code_to_id.get(code)
            if not cat_id:
                print(f"Warning: unknown category code '{code}' for this format — skipping", file=sys.stderr)
                continue
            # Avoid duplicate link
            db.cur_execute(
                "Check existing link",
                "SELECT 1 FROM core_categorynumbers_categories WHERE categorynumbers_id = %s AND category_id = %s;",
                (cn_id, cat_id),
                debug=False,
            )
            if db.cur.fetchone():
                continue
            db.cur_execute(
                "Insert numbers link",
                "INSERT INTO core_categorynumbers_categories (categorynumbers_id, category_id) VALUES (%s, %s);",
                (cn_id, cat_id),
                debug=False,
            )
            inserted_links += 1

    if dry_run:
        db.conn.rollback()
        print(
            f"[DRY-RUN] Would insert {inserted_cn} numbers rows and {inserted_links} links for competition {comp['name']}"
        )
    else:
        db.conn.commit()
        print(
            f"Inserted {inserted_cn} numbers rows and {inserted_links} links for competition {comp['name']}"
        )


def main():
    ap = argparse.ArgumentParser(description="Download or upload competition category number ranges to/from XLSX")
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", default="localhost", help="Database host")
    common.add_argument("--name", default=None, help="Competition name")
    common.add_argument("--date", default=None, help="Competition date (YYYY-MM-DD)")

    dl = sub.add_parser("download", parents=[common], help="Download category numbers to XLSX")
    dl.add_argument("--output", required=False, help="Output XLSX path (defaults to sanitized competition name)")

    ul = sub.add_parser("upload", parents=[common], help="Upload category numbers from XLSX")
    ul.add_argument("--input", required=True, help="Input XLSX path")
    ul.add_argument("--replace", action="store_true", help="Replace all existing numbers for the competition")
    ul.add_argument("--dry-run", action="store_true", help="Validate and show changes without writing")

    args = ap.parse_args()

    db = RaceDBSQL(host=args.host)
    comp = find_competition(db, args.name, args.date)

    if args.cmd == "download":
        out = args.output or f"{sanitize_filename(comp.get('name','competition'))}.xlsx"
        download_xlsx(db, comp, out)
    elif args.cmd == "upload":
        upload_xlsx(db, comp, args.input, replace=args.replace, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
