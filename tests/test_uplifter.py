"""Offline regression tests for asynchronous Uplifter report updates."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libs.uplifter import UplifterError, UplifterReports


def response(status, data):
    result = requests.Response()
    result.status_code = status
    result.url = "https://example.test/task/"
    result._content = json.dumps(data).encode()
    return result


class ReportPollingTests(unittest.TestCase):
    def setUp(self):
        self.client = UplifterReports.__new__(UplifterReports)
        self.client.base_url = "https://example.test"
        self.client.session = Mock()
        self.now = 0
        self.clock = patch("libs.uplifter.time.monotonic", side_effect=lambda: self.now)
        self.sleep = patch("libs.uplifter.time.sleep", side_effect=self.advance)
        self.clock.start()
        self.sleep.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.sleep.stop)

    def advance(self, seconds):
        self.now += seconds

    def update(self, *responses):
        self.client.session.request.side_effect = [
            response(200, {"task_uuid": "test-task"}), *responses
        ]
        return self.client.update_report({"update_link": "/update/"}, 10)

    def test_missing_result_then_success(self):
        result = self.update(
            response(404, {"detail": "No TaskResult matches the given query."}),
            response(200, {"state": "SUCCESS"}),
        )
        self.assertEqual(result["state"], "SUCCESS")
        self.assertEqual(self.now, 5)

    def test_missing_result_times_out(self):
        with self.assertRaisesRegex(UplifterError, "Timed out"):
            self.update(response(404, {}), response(404, {}))
        self.assertEqual(self.now, 10)

    def test_other_http_errors_are_not_retried(self):
        for status in (401, 403, 500):
            with self.subTest(status=status):
                with self.assertRaises(UplifterError):
                    self.update(response(status, {}))
                self.assertEqual(self.now, 0)

    def test_failed_task_stops(self):
        with self.assertRaisesRegex(UplifterError, "Report update failed"):
            self.update(response(200, {"state": "FAILURE"}))
        self.assertEqual(self.now, 0)

    def test_update_endpoint_404_is_not_retried(self):
        self.client.session.request.return_value = response(404, {})
        with self.assertRaises(UplifterError):
            self.client.update_report({"update_link": "/update/"}, 10)
        self.assertEqual(self.client.session.request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
