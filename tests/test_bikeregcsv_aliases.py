import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from libs.bikeregcsv import BikeRegCSV


class AliasTests(unittest.TestCase):
    def read_alias(self, alias):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registrations.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['Last Name', 'First Name', 'Date of Birth', 'Gender', 'UCI Code'])
                writer.writerow(['Chambers', 'Kristine', '8/10/1977', 'X', '123'])
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                reader = BikeRegCSV(str(path))
                if alias is not None:
                    reader.aliases = {'chambers, kristine, 1977-08-10': alias}
                return list(reader.get_next())[0][1]

    def test_configured_chambers_override(self):
        row = self.read_alias(None)
        self.assertEqual(row['Gender'], 'F')
        self.assertEqual(row['UCI Code'], '123')

    def test_legacy_alias(self):
        row = self.read_alias(['Chambers', 'Kris', '1977-08-10', '456'])
        self.assertEqual(row['First Name'], 'Kris')
        self.assertEqual(row['UCI Code'], '456')
        self.assertIsNone(row['Gender'])

    def test_optional_gender(self):
        for gender in (None, ''):
            self.assertIsNone(self.read_alias(['Chambers', 'Kristine', '1977-08-10', '', gender])['Gender'])
        self.assertEqual(self.read_alias(['Chambers', 'Kristine', '1977-08-10', '', ' m '])['Gender'], 'M')

    def test_invalid_alias_rejected(self):
        for alias in (['Chambers'], ['Chambers', 'Kristine', '1977-08-10', '', 'bad']):
            with self.assertRaises(ValueError):
                self.read_alias(alias)
