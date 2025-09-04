#!/usr/bin/env python3

import sys
import os
import csv
import json
from collections import OrderedDict
import re


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

    # Prepare proposed values for new labels
    proposed = {lbl: list(extract_category_gender(lbl)) for lbl in labels}

    # Merge labels (preserve existing values)
    merged = OrderedDict()
    for k in sorted(set(existing.keys()) | set(labels)):
        if k in existing:
            merged[k] = existing[k]
        else:
            merged[k] = proposed.get(k, ["", ""])  # fallback if any

    # Write back
    with open(target, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return merged


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
    # 1) One arg (CSV): emit mapping to stdout (original behavior)
    # 2) Two args (format, CSV): merge into catmap/<format>.json and print merged mapping to stdout
    if len(sys.argv) == 2:
        labels = read_unique_labels(sys.argv[1])
        mapping = OrderedDict((label, list(extract_category_gender(label))) for label in labels)
        json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    elif len(sys.argv) == 3:
        format_name, csv_path = sys.argv[1], sys.argv[2]
        labels = read_unique_labels(csv_path)
        merged = write_merged_catmap(format_name, labels)
        # Informative message only; JSON is written to file
        sys.stderr.write(f"Merged {len(labels)} labels into catmap/{format_name}.json (total {len(merged)} keys)\n")
        return
    else:
        print(f"Usage:\n  {sys.argv[0]} <bikereg.csv>\n  {sys.argv[0]} <format_name> <bikereg.csv>", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
