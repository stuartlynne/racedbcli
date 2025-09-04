#!/usr/bin/env python3

import sys
import os
import csv
import json
from collections import OrderedDict


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


def write_merged_catmap(format_name: str, labels: list[str]) -> OrderedDict:
    """Merge labels into catmap/<format>.json as { label: canonical } mapping.

    - Creates the file if it does not exist.
    - If an older structured file is found (with label_aliases), converts it to a simple mapping.
    - Does not overwrite existing keys; adds missing ones with empty string values.
    Returns the merged OrderedDict mapping.
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
                existing = data
            elif isinstance(data, dict) and "label_aliases" in data:
                # Not reached due to previous branch; kept for clarity
                existing = {a[0]: (a[2] if len(a) > 2 else "") for a in data.get("label_aliases", []) if a}
            else:
                # Convert known structure with label_aliases to mapping if present
                if isinstance(data, dict) and "label_aliases" in data:
                    existing = {a[0]: (a[2] if len(a) > 2 else "") for a in data.get("label_aliases", []) if a}
                else:
                    existing = {}
        except Exception:
            existing = {}

    # Merge labels
    merged = OrderedDict()
    for k in sorted(existing.keys() | set(labels)):
        merged[k] = existing.get(k, "")

    # Write back
    with open(target, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return merged


def main():
    # Modes:
    # 1) One arg (CSV): emit mapping to stdout (original behavior)
    # 2) Two args (format, CSV): merge into catmap/<format>.json and print merged mapping to stdout
    if len(sys.argv) == 2:
        labels = read_unique_labels(sys.argv[1])
        mapping = OrderedDict((label, "") for label in labels)
        json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    elif len(sys.argv) == 3:
        format_name, csv_path = sys.argv[1], sys.argv[2]
        labels = read_unique_labels(csv_path)
        merged = write_merged_catmap(format_name, labels)
        json.dump(merged, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    else:
        print(f"Usage:\n  {sys.argv[0]} <bikereg.csv>\n  {sys.argv[0]} <format_name> <bikereg.csv>", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
