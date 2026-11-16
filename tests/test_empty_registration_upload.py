"""Empty imports must never clear an existing competition."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from libs.racedb import RaceDB


class EmptyUploadTest(unittest.TestCase):
    def setUp(self):
        self.db = RaceDB.__new__(RaceDB)
        self.db.registration_data = []
        self.db.create_registrations_xlsx_file = Mock()
        self.db.upload_file = Mock()

    def test_web_and_mcp_upload_stop_before_file_or_network(self):
        for url in (None, 'http://unused/mcp'):
            with self.assertRaisesRegex(ValueError, 'Refusing to upload zero'):
                self.db.upload_registrations(457, upload=True, mcp_url=url)
        self.db.create_registrations_xlsx_file.assert_not_called()
        self.db.upload_file.assert_not_called()

    def test_direct_mcp_upload_stops_before_session(self):
        with self.assertRaisesRegex(ValueError, 'Refusing to upload zero'):
            asyncio.run(self.db._upload_registrations_mcp_async(457, 'http://unused/mcp'))

    def test_nonempty_passes_guard(self):
        self.db.registration_data = [{'First Name': 'Test'}]
        self.db._require_registrations_for_upload()

    def test_local_empty_export_still_allowed(self):
        self.db.stats = {'tbd_category': 0}
        self.db.upload_registrations(upload=False)
        self.db.create_registrations_xlsx_file.assert_called_once()


if __name__ == '__main__':
    unittest.main()
