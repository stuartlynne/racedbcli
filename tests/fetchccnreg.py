#!/usr/bin/env python3
"""Fetch a CCN/Uplifter event registration report."""

import argparse
import os
import sys

if __name__ == "__main__":
    # Prefer this repository's libs over unrelated installed packages.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.uplifter import DEFAULT_REPORT, UplifterError, UplifterReports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://upliftercycling.com")
    event_group = parser.add_mutually_exclusive_group(required=True)
    event_group.add_argument("--event-id", help="Uplifter event id, e.g. 23433")
    event_group.add_argument("--event-name", help='Exact event name, e.g. "Trout Cross 2026"')
    parser.add_argument("--slug", help="Optional slug override/debug check")
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--format", choices=("csv", "xlsx"), default="csv")
    parser.add_argument("--env-file", default=".ccn.env")
    parser.add_argument("--username", default=os.getenv("CCN_LOGIN") or os.getenv("LOGIN"))
    parser.add_argument("--password", default=os.getenv("CCN_PASSWORD") or os.getenv("PASSWORD"))
    parser.add_argument("--update", action="store_true", help="Regenerate report and wait before downloading")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds to wait for --update")
    parser.add_argument("--output", help="Output filename; defaults to server report filename")
    parser.add_argument("--purchases-output", default="ccn_purchases.csv", help="Companion purchases CSV output")
    parser.add_argument("--list", action="store_true", help="List all available report rows and exit")
    args = parser.parse_args(argv)
    if args.output and os.path.abspath(args.output) == os.path.abspath(args.purchases_output):
        parser.error("Registration and purchase report output paths must differ")

    try:
        uplifter = UplifterReports(
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            env_file=args.env_file,
        )
        uplifter.login()
        event_info = uplifter.search_events(event_id=args.event_id, event_name=args.event_name)
        if args.slug and args.slug != event_info["slug"]:
            raise UplifterError(
                f"--slug {args.slug!r} does not match discovered slug {event_info['slug']!r}"
            )
        print(
            f"Event: id={event_info['event_id']} name={event_info['name']!r} "
            f"slug={event_info['slug']!r} listing_id={event_info['listing_id']}",
            file=sys.stderr,
        )
        report_data = uplifter.get_report_dashboard(event_info["event_id"])
        if args.list:
            for group, report_type in uplifter.iter_report_types(report_data):
                last_report = report_type.get("last_report") or {}
                print(
                    f"{group.get('name')}: {report_type.get('id')} "
                    f"{report_type.get('name')} updated={last_report.get('finished_at')}"
                )
            return 0

        _, report_type = uplifter.find_report_type(report_data, args.report)
        uplifter.print_report_summary(report_type)
        if args.update:
            uplifter.update_report(report_type, args.timeout)
            report_data = uplifter.get_report_dashboard(event_info["event_id"])
            _, report_type = uplifter.find_report_type(report_data, args.report)
            uplifter.print_report_summary(report_type)

        report_file = uplifter.select_report_file(report_type, args.format)
        output_path, _ = uplifter.download_report_file(report_file, args.output)
        purchases_path = uplifter.fetch_purchase_report(
            event_info["event_id"], output=args.purchases_output,
            update=args.update, timeout_seconds=args.timeout,
        )
        print(output_path)
        print(purchases_path)
        return 0
    except UplifterError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
