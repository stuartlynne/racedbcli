import unittest
from unittest.mock import Mock, patch

import requests

from libs.bikeregapi import fetch_event_entries


def response(status):
    result = requests.Response()
    result.status_code = status
    result._content = b"{}"
    result._content_consumed = True
    return result


class BikeRegRetryTests(unittest.TestCase):
    @patch("libs.bikeregapi.time.sleep")
    def test_transient_errors_then_success(self, sleep):
        session = Mock()
        session.post.side_effect = [response(502), response(503), response(200)]
        self.assertEqual(fetch_event_entries(session, "https://example.test", "secret", 1).status_code, 200)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    @patch("libs.bikeregapi.time.sleep")
    def test_exhaustion(self, sleep):
        session = Mock()
        session.post.side_effect = [response(504) for _ in range(4)]
        with self.assertRaises(requests.HTTPError):
            fetch_event_entries(session, "https://example.test", "secret", 1)
        self.assertEqual(session.post.call_count, 4)

    @patch("libs.bikeregapi.time.sleep")
    def test_no_retry_for_auth_error(self, sleep):
        session = Mock()
        session.post.return_value = response(401)
        with self.assertRaises(requests.HTTPError):
            fetch_event_entries(session, "https://example.test", "secret", 1)
        sleep.assert_not_called()

    @patch("libs.bikeregapi.time.sleep")
    def test_timeout_retry(self, sleep):
        session = Mock()
        session.post.side_effect = [requests.Timeout(), response(200)]
        self.assertEqual(fetch_event_entries(session, "https://example.test", "secret", 1).status_code, 200)


if __name__ == "__main__":
    unittest.main()
