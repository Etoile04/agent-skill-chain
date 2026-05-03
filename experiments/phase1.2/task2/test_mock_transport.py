"""Tests for mock_transport – verify mock mode covers all endpoint scenarios
without issuing real HTTP requests."""

import json
import sys
import os
import unittest
from unittest.mock import patch

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from mock_transport import (
    MockTransport, MockMode, MockHttpClient, MockUrllibAdapter,
    TransportError, Transport,
    AUTH_SUCCESS, AUTH_APP_SECRET_INVALID,
    USER_SUCCESS, USER_AUTH_FAIL, USER_RATE_LIMIT, USER_SERVER_ERROR,
    MSG_SUCCESS, MSG_PARAM_ERROR,
    CAL_SUCCESS, CAL_RATE_LIMIT, CAL_SERVER_ERROR,
    REFRESH_SUCCESS,
)
from auth import AuthManager
from endpoints import FeishuClient, FeishuErrorType


# ===================================================================
# 1. Transport contract tests
# ===================================================================

class TestTransportContract(unittest.TestCase):
    """Verify MockTransport satisfies the Transport ABC."""

    def test_is_subclass(self):
        self.assertTrue(issubclass(MockTransport, Transport))

    def test_returns_tuple(self):
        t = MockTransport()
        result = t.request("GET", "https://example.com")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_status_is_int(self):
        status, _, _ = MockTransport().request("GET", "https://example.com")
        self.assertIsInstance(status, int)


# ===================================================================
# 2. Mode-based response tests
# ===================================================================

class TestAlwaysSuccessMode(unittest.TestCase):

    def setUp(self):
        self.t = MockTransport(mode=MockMode.ALWAYS_SUCCESS)

    def test_auth_endpoint(self):
        status, _, body = self.t.request("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["code"], 0)
        self.assertIn("tenant_access_token", data)

    def test_user_endpoint(self):
        status, _, body = self.t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 200)

    def test_message_endpoint(self):
        status, _, body = self.t.request("POST", "https://open.feishu.cn/open-apis/im/v1/messages")
        self.assertEqual(status, 200)

    def test_calendar_endpoint(self):
        status, _, body = self.t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(status, 200)


class TestAlwaysFailMode(unittest.TestCase):

    def setUp(self):
        self.t = MockTransport(mode=MockMode.ALWAYS_FAIL)

    def test_auth_returns_500(self):
        status, _, body = self.t.request("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(status, 500)

    def test_user_returns_500(self):
        status, _, _ = self.t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 500)

    def test_message_returns_500(self):
        status, _, _ = self.t.request("POST", "https://open.feishu.cn/open-apis/im/v1/messages")
        self.assertEqual(status, 500)

    def test_calendar_returns_500(self):
        status, _, _ = self.t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(status, 500)


class TestRealisticMode(unittest.TestCase):

    def setUp(self):
        self.t = MockTransport(mode=MockMode.REALISTIC)

    def test_auth_success(self):
        status, _, body = self.t.request("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("tenant_access_token", data)

    def test_user_success(self):
        status, _, body = self.t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["data"]["user"]["open_id"], "ou_mock_user_001")

    def test_message_success(self):
        status, _, body = self.t.request("POST", "https://open.feishu.cn/open-apis/im/v1/messages")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["data"]["message_id"], "om_mock_msg_001")

    def test_calendar_success(self):
        status, _, body = self.t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(len(data["data"]["items"]), 1)

    def test_unknown_route_404(self):
        status, _, _ = self.t.request("GET", "https://open.feishu.cn/open-apis/unknown/endpoint")
        self.assertEqual(status, 404)


# ===================================================================
# 3. Route override tests (failure & rate-limit scenarios)
# ===================================================================

class TestRouteOverrides(unittest.TestCase):

    def test_auth_failure_override(self):
        t = MockTransport(route_overrides={"auth": AUTH_APP_SECRET_INVALID})
        status, _, body = t.request("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(status, 200)  # Feishu returns 200 even on app-level errors
        data = json.loads(body)
        self.assertNotEqual(data["code"], 0)

    def test_user_auth_fail(self):
        t = MockTransport(route_overrides={"user": USER_AUTH_FAIL})
        status, _, _ = t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 401)

    def test_user_rate_limit(self):
        t = MockTransport(route_overrides={"user": USER_RATE_LIMIT})
        status, headers, body = t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 429)
        self.assertIn("Retry-After", headers)

    def test_user_server_error(self):
        t = MockTransport(route_overrides={"user": USER_SERVER_ERROR})
        status, _, _ = t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_123")
        self.assertEqual(status, 500)

    def test_calendar_rate_limit(self):
        t = MockTransport(route_overrides={"calendar": CAL_RATE_LIMIT})
        status, headers, _ = t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(status, 429)

    def test_calendar_server_error(self):
        t = MockTransport(route_overrides={"calendar": CAL_SERVER_ERROR})
        status, _, _ = t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(status, 500)

    def test_message_param_error(self):
        t = MockTransport(route_overrides={"message": MSG_PARAM_ERROR})
        status, _, _ = t.request("POST", "https://open.feishu.cn/open-apis/im/v1/messages")
        self.assertEqual(status, 400)


# ===================================================================
# 4. Delay & request logging tests
# ===================================================================

class TestDelayAndLogging(unittest.TestCase):

    def test_zero_delay(self):
        t = MockTransport(delay_seconds=0)
        import time
        start = time.monotonic()
        t.request("GET", "https://example.com")
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.1)

    def test_request_log(self):
        t = MockTransport()
        t.request("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                   headers={"X-Test": "1"}, body={"app_id": "abc"})
        self.assertEqual(len(t.request_log), 1)
        entry = t.request_log[0]
        self.assertEqual(entry["method"], "POST")
        self.assertIn("tenant_access_token", entry["url"])
        self.assertEqual(entry["headers"]["X-Test"], "1")
        self.assertEqual(entry["body"]["app_id"], "abc")

    def test_multiple_requests_logged(self):
        t = MockTransport()
        t.request("GET", "https://open.feishu.cn/open-apis/contact/v3/users/ou_1")
        t.request("POST", "https://open.feishu.cn/open-apis/im/v1/messages")
        t.request("GET", "https://open.feishu.cn/open-apis/calendar/v4/calendars/primary/events")
        self.assertEqual(len(t.request_log), 3)


# ===================================================================
# 5. Integration: AuthManager with MockHttpClient
# ===================================================================

class TestAuthManagerWithMock(unittest.TestCase):

    def test_get_tenant_token(self):
        transport = MockTransport(mode=MockMode.ALWAYS_SUCCESS)
        client = MockHttpClient(transport)
        mgr = AuthManager(app_id="test_app", app_secret="test_secret", http_client=client)
        token = mgr.get_tenant_token()
        self.assertEqual(token, "mock-tenant-token-abc123")

    def test_tenant_token_cached(self):
        transport = MockTransport(mode=MockMode.ALWAYS_SUCCESS)
        client = MockHttpClient(transport)
        mgr = AuthManager(app_id="test_app", app_secret="test_secret", http_client=client)
        mgr.get_tenant_token()
        self.assertTrue(mgr.is_tenant_token_cached)
        # Second call should not trigger new request (cached)
        count_before = len(transport.request_log)
        mgr.get_tenant_token()
        self.assertEqual(len(transport.request_log), count_before)

    def test_auth_headers(self):
        transport = MockTransport(mode=MockMode.ALWAYS_SUCCESS)
        client = MockHttpClient(transport)
        mgr = AuthManager(app_id="test_app", app_secret="test_secret", http_client=client)
        headers = mgr.get_headers(mode="tenant")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer mock-tenant-token"))

    def test_user_token_refresh(self):
        transport = MockTransport(mode=MockMode.ALWAYS_SUCCESS)
        client = MockHttpClient(transport)
        mgr = AuthManager(app_id="test_app", app_secret="test_secret", http_client=client)
        mgr.set_user_credentials("old-access-token", "old-refresh-token", expires_in=0)
        # Token expired (expires_in=0), will trigger refresh
        new_token = mgr.get_user_token()
        self.assertEqual(new_token, "mock-user-token-refreshed")

    def test_auth_failure_propagates(self):
        transport = MockTransport(route_overrides={"auth": AUTH_APP_SECRET_INVALID})
        client = MockHttpClient(transport)
        mgr = AuthManager(app_id="test_app", app_secret="wrong", http_client=client)
        with self.assertRaises(KeyError):
            mgr.get_tenant_token()


# ===================================================================
# 6. Integration: FeishuClient with MockUrllibAdapter
# ===================================================================

class TestFeishuClientWithMock(unittest.TestCase):

    def test_get_user_info_success(self):
        transport = MockTransport(mode=MockMode.REALISTIC)
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.name, "Mock User")
        self.assertEqual(resp.data.email, "mock@example.com")

    def test_get_user_info_auth_fail(self):
        transport = MockTransport(route_overrides={"user": USER_AUTH_FAIL})
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="expired-token")
        with adapter.patch():
            resp = client.get_user_info("ou_123")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.AUTH)

    def test_get_user_info_rate_limit(self):
        transport = MockTransport(route_overrides={"user": USER_RATE_LIMIT})
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.get_user_info("ou_123")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.RATE_LIMIT)

    def test_get_user_info_server_error(self):
        transport = MockTransport(route_overrides={"user": USER_SERVER_ERROR})
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.get_user_info("ou_123")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.SERVER)

    def test_send_message_success(self):
        transport = MockTransport(mode=MockMode.REALISTIC)
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.send_message("ou_123", "text", '{"text":"hello"}')
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.message_id, "om_mock_msg_001")

    def test_send_message_param_error(self):
        # FeishuClient does client-side validation first
        transport = MockTransport(mode=MockMode.REALISTIC)
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.send_message("", "text", '{"text":"hello"}')
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

    def test_calendar_events_success(self):
        transport = MockTransport(mode=MockMode.REALISTIC)
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.list_calendar_events("1700000000", "1700003600")
        self.assertTrue(resp.success)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0].summary, "Mock Meeting")

    def test_calendar_rate_limit(self):
        transport = MockTransport(route_overrides={"calendar": CAL_RATE_LIMIT})
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.list_calendar_events("1700000000", "1700003600")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.RATE_LIMIT)

    def test_calendar_server_error(self):
        transport = MockTransport(route_overrides={"calendar": CAL_SERVER_ERROR})
        adapter = MockUrllibAdapter(transport)
        client = FeishuClient(access_token="mock-token")
        with adapter.patch():
            resp = client.list_calendar_events("1700000000", "1700003600")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.SERVER)


# ===================================================================
# 7. No real HTTP verification
# ===================================================================

class TestNoRealHTTP(unittest.TestCase):
    """Ensure MockTransport never touches the network."""

    def test_no_real_request(self):
        """MockTransport returns responses purely from memory, never DNS/network."""
        # REALISTIC mode returns 404 for unknown routes (no DNS lookup)
        t = MockTransport(mode=MockMode.REALISTIC)
        status, _, _ = t.request("GET", "https://definitely-not-a-real-host.invalid/path")
        self.assertEqual(status, 404)

        # ALWAYS_SUCCESS returns generic success for unknown routes
        t2 = MockTransport(mode=MockMode.ALWAYS_SUCCESS)
        status2, _, _ = t2.request("POST", "https://another-fake-host.invalid/api")
        self.assertEqual(status2, 200)

        # ALWAYS_FAIL always returns 500
        t3 = MockTransport(mode=MockMode.ALWAYS_FAIL)
        status3, _, _ = t3.request("GET", "https://yet-another-fake-host.invalid/api")
        self.assertEqual(status3, 500)


if __name__ == "__main__":
    unittest.main()
