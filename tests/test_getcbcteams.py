"""Offline checks for the affiliate table parser."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from getcbcteams import TABLE_NAMES, parse_page


def sample_page():
    parts = ["<p>This page was last updated on Aug 19, 2026</p>"]
    for index, name in enumerate(TABLE_NAMES):
        parts.append(f'<a href="#tab{index}">{name}</a><div id="tab{index}">')
        label = "Club" if index == 0 else "Team"
        parts.append(f"<table><thead><tr><th>Region</th><th>{label}</th>"
                     "<th>Website</th></tr></thead><tbody>")
        parts.append("<tr><td>Island</td><td></td><td></td></tr>")
        parts.append('<tr><td></td><td>A &amp; B</td><td>'
                     '<a href="www.example.com">Example</a></td></tr>')
        parts.append("</tbody></table></div>")
    return "".join(parts)


class AffiliateParserTests(unittest.TestCase):
    def test_combines_tabs_and_preserves_region_and_links(self):
        updated, headers, rows = parse_page(sample_page())
        self.assertEqual(str(updated), "2026-08-19")
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["Table"] for r in rows}, set(TABLE_NAMES))
        self.assertEqual(headers.count("Club / Team"), 1)
        for row in rows:
            self.assertEqual(row["Club / Team"], "A & B")
            self.assertEqual(row["Region"], "Island")
            self.assertEqual(row["Website"], "Example")
            self.assertEqual(row["Website URL"], "https://www.example.com")

    def test_missing_tab_does_not_silently_export_partial_data(self):
        with self.assertRaisesRegex(ValueError, "Missing table: UCI Teams"):
            parse_page(sample_page().replace("UCI Teams", "Other"))

    def test_requires_source_date(self):
        with self.assertRaisesRegex(ValueError, "last updated on"):
            parse_page(sample_page().replace("last updated on", "retrieved on"))


if __name__ == "__main__":
    unittest.main()
