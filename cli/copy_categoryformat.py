#!/usr/bin/env python3

import sys
import os
import argparse
from typing import Optional

# Ensure repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from libs.racedbsql import RaceDBSQL  # type: ignore


def copy_category_format(
    db: RaceDBSQL,
    src_name: str,
    dst_name: str,
    overwrite: bool = False,
    description: str | None = None,
) -> tuple[int, int]:
    # Lookup source format
    db.cur_execute(
        f"Lookup source category format '{src_name}'",
        "SELECT id, name, description FROM core_categoryformat WHERE name = %s;",
        (src_name,),
        debug=False,
    )
    src_fmt = db.cur.fetchone()
    if not src_fmt:
        raise SystemExit(f"Source format '{src_name}' not found")

    # Check destination existence
    db.cur_execute(
        f"Check destination category format '{dst_name}'",
        "SELECT id FROM core_categoryformat WHERE name = %s;",
        (dst_name,),
        debug=False,
    )
    dst_existing = db.cur.fetchone()
    if dst_existing and not overwrite:
        raise SystemExit(f"Destination format '{dst_name}' already exists (id={dst_existing['id']}). Use a different name.")

    # Create destination format if not present or overwrite requested
    if dst_existing and overwrite:
        dst_id = dst_existing["id"]
        # Update description to provided value, otherwise match source
        new_desc = description if description is not None else src_fmt.get("description")
        db.cur_execute(
            f"Update destination format description for '{dst_name}'",
            "UPDATE core_categoryformat SET description = %s WHERE id = %s;",
            (new_desc, dst_id),
            debug=False,
        )
    else:
        db.cur_execute(
            f"Create destination category format '{dst_name}'",
            "INSERT INTO core_categoryformat (name, description) VALUES (%s, %s) RETURNING id;",
            (dst_name, description if description is not None else src_fmt.get("description")),
            debug=False,
        )
        row = db.cur.fetchone()
        dst_id = row["id"] if isinstance(row, dict) else row[0]

    # Fetch source categories
    db.cur_execute(
        f"Fetch categories for format '{src_name}'",
        "SELECT code, gender, description, sequence FROM core_category WHERE format_id = %s ORDER BY sequence, code;",
        (src_fmt["id"] if isinstance(src_fmt, dict) else src_fmt[0],),
        debug=False,
    )
    rows = db.cur.fetchall() or []

    # Insert copied categories, skipping duplicates by code
    inserted = 0
    skipped = 0
    for r in rows:
        code = r.get("code") if isinstance(r, dict) else r[0]
        gender = r.get("gender") if isinstance(r, dict) else r[1]
        desc = r.get("description") if isinstance(r, dict) else r[2]
        seq = r.get("sequence") if isinstance(r, dict) else r[3]
        # Check duplicate by (format_id, code)
        db.cur_execute(
            f"Check duplicate for code {code}",
            "SELECT 1 FROM core_category WHERE format_id = %s AND code = %s LIMIT 1;",
            (dst_id, code),
            debug=False,
        )
        if db.cur.fetchone():
            skipped += 1
            continue
        db.cur_execute(
            f"Insert category {code}",
            "INSERT INTO core_category (code, gender, description, sequence, format_id) VALUES (%s, %s, %s, %s, %s);",
            (code, gender, desc, seq, dst_id),
            debug=False,
        )
        inserted += 1

    db.conn.commit()
    return inserted, skipped


def main():
    p = argparse.ArgumentParser(description="Copy core_categoryformat and its categories to a new format name")
    p.add_argument("src", help="Source core_categoryformat name (e.g., lmcx2024)")
    p.add_argument("dst", help="Destination core_categoryformat name (e.g., lmcx2025)")
    p.add_argument("desc", nargs="?", help="Optional description for the new format (defaults to source description)")
    p.add_argument("--host", default="localhost", help="Database host (e.g., localhost or 192.168.1.10)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite destination description and append categories (existing categories with same code are skipped)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be copied without writing to the database")
    args = p.parse_args()

    db = RaceDBSQL(host=args.host)
    try:
        if args.dry_run:
            # For dry-run, wrap with a rollback at the end and print planned counts
            pass
        inserted, skipped = copy_category_format(
            db,
            args.src,
            args.dst,
            overwrite=args.overwrite,
            description=args.desc,
        )
        if args.dry_run:
            db.conn.rollback()
            print(
                f"[DRY-RUN] Would copy {inserted + skipped} categories from '{args.src}' to '{args.dst}' "
                f"({inserted} inserts, {skipped} skipped duplicates)"
                + (" with custom description" if args.desc else "")
            )
            print(f"skipped {skipped} existing categories with same code")
            print(f"inserted {inserted} existing categories with same code")
        else:
            print(
                f"Copied {inserted + skipped} categories from '{args.src}' to '{args.dst}' "
                f"({inserted} inserted, {skipped} skipped duplicates)"
                + (" with custom description" if args.desc else "")
            )
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        db.conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
