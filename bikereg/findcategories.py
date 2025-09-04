#!/usr/bin/env python3

import sys
import csv
import json
from collections import OrderedDict


COLUMN = 'Category Entered / Merchandise Ordered'


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <bikereg.csv>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

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

    # Sort unique values and create mapping label -> ""
    mapping = OrderedDict((label, "") for label in sorted(values))

    json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == '__main__':
    main()

