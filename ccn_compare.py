#!/usr/bin/env python3
"""Plot CCN/Uplifter registration pace against previous events."""

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from libs.uplifter import UplifterError, UplifterReports


DEFAULT_PREVIOUS_GLOB = "uplifter/*.csv"
DEFAULT_CURRENT = "ccn_event.csv"
DEFAULT_OUTPUT = "ccn_compare.png"


class CompareError(RuntimeError):
    pass


def eprint(*args):
    print(*args, file=sys.stderr)


def decode_csv(path):
    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1", errors="replace")


def rows_from_ccn_csv(path):
    text = decode_csv(path)
    lines = text.splitlines()
    header_index = None
    for i, line in enumerate(lines):
        if "Reg ID" in line and "Reg Creation Date" in line:
            header_index = i
            break
    if header_index is None:
        raise CompareError(f"{path}: cannot find CCN header row with Reg Creation Date")

    reader = csv.DictReader(lines[header_index:])
    for row in reader:
        if not any(row.values()):
            continue
        first = str(row.get("Reg ID") or "").strip().lower()
        if first.startswith(("complete registration", "complete registrations", "filters", "event:", "standalone:", "statuses:")):
            break
        yield row


def parse_creation_date(value):
    value = (value or "").strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def event_name_from_rows(rows):
    for row in rows:
        event = (row.get("Event") or "").strip()
        if event:
            return event
    return None


def event_date_from_filename(path):
    # Uplifter report files normally start with the report generation date.
    # This is only a fallback when the event listing lookup is unavailable.
    match = re.match(r"([A-Za-z]{3})-(\d{1,2})-(\d{4})-", Path(path).name)
    if not match:
        return None
    return datetime.strptime("-".join(match.groups()), "%b-%d-%Y").date()


def get_event_date(path, rows, uplifter=None):
    event_name = event_name_from_rows(rows)
    if uplifter and event_name:
        try:
            info = uplifter.search_events(event_name=event_name)
            starts = info.get("starts")
            if starts:
                return datetime.fromisoformat(starts[:19]).date(), event_name, "uplifter"
        except UplifterError as exc:
            eprint(f"{path}: Uplifter event lookup failed for {event_name!r}: {exc}")

    fallback = event_date_from_filename(path)
    if fallback:
        return fallback, event_name or Path(path).stem, "filename"
    raise CompareError(f"{path}: cannot determine event date")


def series_from_csv(path, uplifter=None, complete_only=True, carry_to_event_day=True):
    rows = list(rows_from_ccn_csv(path))
    event_date, event_name, date_source = get_event_date(path, rows, uplifter=uplifter)
    buckets = Counter()
    skipped = Counter()

    for row in rows:
        status = (row.get("Status") or "").strip()
        if complete_only and status != "Complete":
            skipped["status"] += 1
            continue
        creation_date = parse_creation_date(row.get("Reg Creation Date"))
        if not creation_date:
            skipped["creation_date"] += 1
            continue
        days_before = (event_date - creation_date).days
        buckets[days_before] += 1

    if not buckets:
        raise CompareError(f"{path}: no rows with usable Reg Creation Date")

    # At N days before the event, cumulative total is everything created at N
    # or more days before the event.
    min_day = min(min(buckets), 0) if carry_to_event_day else min(buckets)
    max_day = max(buckets)
    running = 0
    points = []
    for day in range(max_day, min_day - 1, -1):
        running += buckets.get(day, 0)
        points.append((day, running))

    label = event_name or Path(path).stem
    if date_source == "filename":
        label = f"{label} (date from filename)"
    return {
        "path": Path(path),
        "label": label,
        "event_date": event_date,
        "date_source": date_source,
        "points": points,
        "count": sum(buckets.values()),
        "skipped": dict(skipped),
        "latest_days_before": min(buckets),
    }


def plot_series(series_list, output):
    fig, ax = plt.subplots(figsize=(11, 7))
    for series in series_list:
        x = [p[0] for p in series["points"]]
        y = [p[1] for p in series["points"]]
        ax.plot(x, y, marker="o", markersize=3, linewidth=2, label=f"{series['label']} ({series['count']})")

    ax.set_title("CCN/Uplifter Registration Pace")
    ax.set_xlabel("Days before event")
    ax.set_ylabel("Total complete registrations")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize="small")
    ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(output, dpi=150)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", default=DEFAULT_CURRENT, help="Current CCN/Uplifter CSV")
    parser.add_argument(
        "--previous-glob",
        default=DEFAULT_PREVIOUS_GLOB,
        help="Glob for previous event CSV files",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output PNG")
    parser.add_argument("--all-statuses", action="store_true", help="Count rows even when Status is not Complete")
    parser.add_argument("--no-uplifter-lookup", action="store_true", help="Do not login to Uplifter for event dates")
    args = parser.parse_args(argv)

    paths = sorted(Path().glob(args.previous_glob))
    current = Path(args.current)
    if current.exists():
        paths.append(current)
    else:
        raise CompareError(f"Current CSV not found: {current}")
    if not paths:
        raise CompareError(f"No CSV files matched {args.previous_glob!r}")

    uplifter = None
    if not args.no_uplifter_lookup:
        try:
            uplifter = UplifterReports()
            uplifter.login()
        except UplifterError as exc:
            eprint(f"Uplifter login unavailable, falling back to filename dates: {exc}")
            uplifter = None

    series_list = []
    for path in paths:
        is_current = path == current
        series = series_from_csv(
            path,
            uplifter=uplifter,
            complete_only=not args.all_statuses,
            carry_to_event_day=not is_current,
        )
        series_list.append(series)
        eprint(
            f"{path}: event_date={series['event_date']} source={series['date_source']} "
            f"count={series['count']} latest_days_before={series['latest_days_before']} "
            f"skipped={series['skipped']}"
        )

    plot_series(series_list, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CompareError, UplifterError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
