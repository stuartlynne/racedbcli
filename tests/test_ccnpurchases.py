"""Offline receipt reconciliation and companion report download tests."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libs.ccnpurchases import match_purchases, read_purchases, receipt_id
from libs.uplifter import PURCHASE_REPORT, UplifterReports


def registration(reg_id='1', identity='10', receipt='55', first='Test'):
    return {'Reg ID': reg_id, 'Identity ID': identity, 'First Name': first,
            'Last Name': 'Rider', 'Receipt': f'https://ccnbikes.com/#!/receipt/{receipt}'}


class PurchaseTests(unittest.TestCase):
    def setUp(self):
        self.purchase = {'receipt': '55', 'product': 'Timing Chip > 1', 'quantity': 1}

    def test_same_rider_multiple_races(self):
        notes, warnings = match_purchases([registration(), registration('2')], [self.purchase])
        self.assertEqual(set(notes), {'1', '2'})
        self.assertEqual(notes['1'], notes['2'])
        self.assertIn('PURCHASED:', notes['1'][0])
        self.assertEqual(warnings, [])

    def test_family_requires_confirmation(self):
        notes, warnings = match_purchases(
            [registration(), registration('2', '20', first='Child')], [self.purchase])
        self.assertEqual(len(warnings), 1)
        self.assertIn('NEEDS CONFIRMATION', notes['1'][0])
        self.assertEqual(notes['1'], notes['2'])

    def test_unmatched_no_guess_by_name(self):
        notes, warnings = match_purchases([registration(receipt='99')], [self.purchase])
        self.assertEqual(notes, {})
        self.assertIn('Unmatched purchase', warnings[0])

    def test_multiple_products_and_quantities(self):
        second = dict(self.purchase, product='Extra tag', quantity=2)
        notes, _ = match_purchases([registration()], [self.purchase, second])
        self.assertEqual(len(notes['1']), 2)
        self.assertIn('(2) Extra tag', notes['1'][1])

    def test_csv_trailer_and_bad_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'purchases.csv'
            path.write_text('Store,Product Name,Quantity,Receipt Link\n'
                            'Chips,Timing Chip > 1,2,https://ccnbikes.com/#!/receipt/55\n'
                            '\nReport generated today\n\nFilters\n')
            rows = list(read_purchases(path))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['quantity'], 2)
            path.write_text('Product Name,Quantity\nChip,1\n')
            with self.assertRaises(ValueError):
                list(read_purchases(path))

    def test_receipt_hosts_and_invalid_links(self):
        self.assertEqual(receipt_id('https://upliftercycling.com/#!/receipt/55'), '55')
        self.assertIsNone(receipt_id(''))
        self.assertIsNone(receipt_id('https://example.test/55'))

    def test_registration_note_integration(self):
        from ccn.ccn import GetCCNReg
        importer = GetCCNReg.__new__(GetCCNReg)
        importer.racedb = Mock(purchases={})
        importer.registrations = [dict(registration(), **{
            'Date of Birth': '1990-01-01', 'Gender': 'M', 'licenses': {},
            'requested_category': 'Masters (40+)',
        })]
        notes, _ = match_purchases(importer.registrations, [self.purchase])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            importer.process_registrations(purchase_notes=notes)
        self.assertIn('PURCHASED: (1) Timing Chip > 1',
                      importer.racedb.add_registration.call_args.kwargs['note'])

    def test_download_refresh_and_existing_report(self):
        for update, exists in [(False, True), (True, True), (False, False)]:
            with self.subTest(update=update, exists=exists):
                client = UplifterReports.__new__(UplifterReports)
                report = {'name': PURCHASE_REPORT, 'last_report': {
                    'report_files': [{'format': 'CSV', 'url': 'https://example.test/p.csv'}]}}
                initial = report if exists else {'name': PURCHASE_REPORT}
                client.get_report_dashboard = Mock(return_value={})
                client.find_report_type = Mock(side_effect=[({}, initial), ({}, report)])
                client.update_report = Mock()
                client.print_report_summary = Mock()
                client.download_report_file = Mock(return_value=(Path('p.csv'), None))
                self.assertEqual(client.fetch_purchase_report(23594, update=update), Path('p.csv'))
                self.assertEqual(client.update_report.call_count, int(update or not exists))


if __name__ == '__main__':
    unittest.main()
