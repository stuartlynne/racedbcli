#!/usr/bin/env python3

import sys
import argparse

try:
    from libs.racedbsql import RaceDBSQL
except Exception as e:
    print(f"Failed to import RaceDBSQL from libs: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Lookup Categories by CategoryFormat name and list code, gender, description."
        )
    )
    parser.add_argument(
        "format_name",
        help="CategoryFormat name to search (exact match; use quotes if spaces)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Database host (e.g., localhost or 192.168.1.10)",
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    db = RaceDBSQL(host=args.host)

    # 1) Find the CategoryFormat by name
    q_fmt = "SELECT id, name, description FROM core_categoryformat WHERE name = %s;"
    try:
        db.cur_execute(
            f"Find category format by name '{args.format_name}'",
            q_fmt,
            (args.format_name,),
            debug=False,
        )
        fmt = db.cur.fetchone()
    except Exception as e:
        print(f"Query failed: {e}", file=sys.stderr)
        sys.exit(2)

    if not fmt:
        print(f"No core_categoryformat found with name '{args.format_name}'.", file=sys.stderr)
        sys.exit(3)

    fmt_id = fmt["id"] if isinstance(fmt, dict) else fmt[0]
    fmt_name = fmt["name"] if isinstance(fmt, dict) else fmt[1]
    fmt_desc = fmt["description"] if isinstance(fmt, dict) else fmt[2]

    print(f"CategoryFormat: id={fmt_id} name='{fmt_name}' desc='{fmt_desc}'")

    # 2) Find Categories for this format_id
    q_cat = (
        "SELECT code, gender, description FROM core_category WHERE format_id = %s ORDER BY sequence, code;"
    )
    try:
        db.cur_execute(
            f"Find categories for format_id {fmt_id}", q_cat, (fmt_id,), debug=False
        )
        rows = db.cur.fetchall()
    except Exception as e:
        print(f"Category query failed: {e}", file=sys.stderr)
        sys.exit(4)

    if not rows:
        print("No categories found for this format.")
        return

    # Output: code, gender, description
    for r in rows:
        # r may be a dict (RealDictCursor) as configured in RaceDBSQL
        if isinstance(r, dict):
            code, gender, desc = r.get("code"), r.get("gender"), r.get("description")
        else:
            code, gender, desc = r
        print(f"{code}\t{gender}\t{desc}")


if __name__ == "__main__":
    main()

