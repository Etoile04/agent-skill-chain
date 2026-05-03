"""Unit tests for Feishu API endpoint wrappers."""

import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from endpoints import (
    FeishuClient,
    FeishuResponse,
    FeishuErrorType,
    UserInfo,
    MessageResult,
    CalendarEvent,
    _classify_error,
    _parse_response,
)

MOCK_TOKEN = "test-token-abc"


def _mock_response(data: dict, status: int = 200):
    """Create a context manager that mocks urlopen."""
    raw = json.dumps(data).encode("utf-8")
    cm = MagicMock()
    cm.read.return_value = raw
    cm.status = status
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _http_error(status: int, code: int = -1, msg: str = "error"):
    body = json.dumps({"code": code, "msg": msg}).encode("utf-8")
    err = HTTPError("https://example.com", status, "Error", {}, None)
    err.read = MagicMock(return_value=body)
    err.code = status
    err.fp = MagicMock()
    err.fp.read = MagicMock(return_value=body)
    return err


class TestFeishuResponse(unittest.TestCase):
    def test_success_response(self):
        resp = FeishuResponse(success=True, data={"key": "val"})
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, {"key": "val"})
        self.assertIsNone(resp.error_code)

    def test_error_response(self):
        resp = FeishuResponse(
            success=False, error_code="100", error_msg="bad",
            error_type=FeishuErrorType.PARAM,
        )
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_code, "100")


class TestClassifyError(unittest.TestCase):
    def test_auth(self):
        self.assertEqual(_classify_error(401), FeishuErrorType.AUTH)
        self.assertEqual(_classify_error(200, 99991668), FeishuErrorType.AUTH)

    def test_param(self):
        self.assertEqual(_classify_error(400), FeishuErrorType.PARAM)

    def test_rate_limit(self):
        self.assertEqual(_classify_error(429), FeishuErrorType.RATE_LIMIT)

    def test_server(self):
        self.assertEqual(_classify_error(500), FeishuErrorType.SERVER)
        self.assertEqual(_classify_error(502), FeishuErrorType.SERVER)

    def test_unknown(self):
        self.assertEqual(_classify_error(403), FeishuErrorType.UNKNOWN)


class TestParseResponse(unittest.TestCase):
    def test_success_parse(self):
        raw = json.dumps({"code": 0, "data": {"foo": "bar"}}).encode()
        resp = _parse_response(raw, 200)
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, {"foo": "bar"})

    def test_error_parse(self):
        raw = json.dumps({"code": 99991400, "msg": "invalid param"}).encode()
        resp = _parse_response(raw, 400)
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_code, "99991400")
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

    def test_invalid_json(self):
        raw = b"not json"
        resp = _parse_response(raw, 200)
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_code, "PARSE_ERROR")


class TestFeishuClientGetUserInfo(unittest.TestCase):
    def setUp(self):
        self.client = FeishuClient(MOCK_TOKEN)

    @patch("endpoints.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({
            "code": 0,
            "data": {
                "user": {
                    "open_id": "ou_123",
                    "name": "Zhang San",
                    "avatar": {"avatar_72": "https://img.url"},
                    "email": "zhang@test.com",
                    "mobile": "+8613800138000",
                    "department_ids": ["dep_001"],
                }
            },
        })
        resp = self.client.get_user_info("ou_123")
        self.assertTrue(resp.success)
        self.assertIsInstance(resp.data, UserInfo)
        self.assertEqual(resp.data.name, "Zhang San")
        self.assertEqual(resp.data.email, "zhang@test.com")
        mock_urlopen.assert_called_once()

    def test_empty_open_id(self):
        resp = self.client.get_user_info("")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

    @patch("endpoints.urllib.request.urlopen")
    def test_auth_error(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(401, 99991668, "token expired")
        resp = self.client.get_user_info("ou_123")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.AUTH)

    @patch("endpoints.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError(reason=ConnectionError("timeout"))
        resp = self.client.get_user_info("ou_123")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.NETWORK)


class TestFeishuClientSendMessage(unittest.TestCase):
    def setUp(self):
        self.client = FeishuClient(MOCK_TOKEN)

    @patch("endpoints.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({
            "code": 0,
            "data": {
                "message_id": "om_abc123",
                "create_time": "1700000000",
            },
        })
        resp = self.client.send_message("ou_456", "text", '{"text":"hello"}')
        self.assertTrue(resp.success)
        self.assertIsInstance(resp.data, MessageResult)
        self.assertEqual(resp.data.message_id, "om_abc123")

    def test_missing_params(self):
        resp = self.client.send_message("", "text", "content")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

    @patch("endpoints.urllib.request.urlopen")
    def test_rate_limit(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(429, 99991403, "rate limited")
        resp = self.client.send_message("ou_456", "text", "{}")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.RATE_LIMIT)


class TestFeishuClientCalendarEvents(unittest.TestCase):
    def setUp(self):
        self.client = FeishuClient(MOCK_TOKEN)

    @patch("endpoints.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({
            "code": 0,
            "data": {
                "items": [
                    {"event_id": "ev_1", "summary": "Meeting A", "start_time": "10:00", "end_time": "11:00"},
                    {"event_id": "ev_2", "summary": "Meeting B", "start_time": "14:00", "end_time": "15:00"},
                ]
            },
        })
        resp = self.client.list_calendar_events("2026-05-01", "2026-05-02")
        self.assertTrue(resp.success)
        self.assertEqual(len(resp.data), 2)
        self.assertIsInstance(resp.data[0], CalendarEvent)
        self.assertEqual(resp.data[0].summary, "Meeting A")

    def test_missing_times(self):
        resp = self.client.list_calendar_events("", "2026-05-02")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

    @patch("endpoints.urllib.request.urlopen")
    def test_server_error(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(500, -1, "internal error")
        resp = self.client.list_calendar_events("2026-05-01", "2026-05-02")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.SERVER)

    @patch("endpoints.urllib.request.urlopen")
    def test_empty_events(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"code": 0, "data": {"items": []}})
        resp = self.client.list_calendar_events("2026-05-01", "2026-05-02")
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, [])


class TestRequestHeaders(unittest.TestCase):
    def test_bearer_token(self):
        client = FeishuClient("my-token")
        headers = client._headers()
        self.assertEqual(headers["Authorization"], "Bearer my-token")
        self.assertIn("application/json", headers["Content-Type"])


if __name__ == "__main__":
    unittest.main()
