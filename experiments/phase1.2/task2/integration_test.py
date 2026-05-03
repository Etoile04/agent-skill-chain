#!/usr/bin/env python3
"""End-to-end integration tests for the Feishu API toolchain.

Uses MockTransport to eliminate all real HTTP requests while validating
the complete pipeline: AuthManager → FeishuClient → RateLimiter → TestReport.

Scenarios:
    1. Happy path: auth → user query → send message → calendar → report
    2. Auth failure with refresh retry
    3. Rate-limit backoff and retry
    4. Mixed success/failure, report statistics correct
    5. All-fail scenario, report summary correct
"""

import json
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------

sys.path.insert(0, "/tmp/agent-skill-chain/experiments/phase1.2/task2")

from auth import AuthManager
from endpoints import FeishuClient, FeishuErrorType
from ratelimit import RateLimiter, RateLimitError, NonRetryableError, RETRYABLE_STATUS_CODES
from reporter import TestReport, TestRecord
from mock_transport import (
    MockTransport,
    MockMode,
    MockHttpClient,
    MockUrllibAdapter,
    AUTH_SUCCESS,
    AUTH_APP_SECRET_INVALID,
    USER_SUCCESS,
    USER_AUTH_FAIL,
    USER_RATE_LIMIT,
    USER_SERVER_ERROR,
    MSG_SUCCESS,
    MSG_PARAM_ERROR,
    CAL_SUCCESS,
    CAL_RATE_LIMIT,
    CAL_SERVER_ERROR,
    REFRESH_SUCCESS,
)


# ===================================================================
# Helper: build a fully-wired AuthManager + FeishuClient pair
# ===================================================================

def _wire_clients(transport: MockTransport) -> tuple:
    """Return (AuthManager, FeishuClient) both backed by *transport*."""
    http_client = MockHttpClient(transport)
    auth = AuthManager(
        app_id="mock_app_id",
        app_secret="mock_app_secret",
        http_client=http_client,
    )
    # Bootstrap tenant token
    tenant_token = auth.get_tenant_token()
    client = FeishuClient(access_token=tenant_token)
    return auth, client


# ===================================================================
# Scenario 1: Happy path
# ===================================================================

class TestScenario1HappyPath(unittest.TestCase):
    """Full pipeline: auth → user → message → calendar → report."""

    def test_complete_flow(self):
        transport = MockTransport(MockMode.REALISTIC)
        auth, client = _wire_clients(transport)

        report = TestReport()

        # Step 1: query user
        with MockUrllibAdapter(transport).patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.open_id, "ou_mock_user_001")
        report.add_record(TestRecord("get_user_info", "success", 42.0))

        # Step 2: send message
        with MockUrllibAdapter(transport).patch():
            resp = client.send_message(
                "ou_mock_user_001", "text", '{"text":"hello"}'
            )
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.message_id, "om_mock_msg_001")
        report.add_record(TestRecord("send_message", "success", 88.0))

        # Step 3: list calendar
        with MockUrllibAdapter(transport).patch():
            resp = client.list_calendar_events("1700000000", "1700003600")
        self.assertTrue(resp.success)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0].summary, "Mock Meeting")
        report.add_record(TestRecord("list_calendar_events", "success", 120.0))

        # Report verification
        summary = report.get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["success"], 3)
        self.assertEqual(summary["fail"], 0)
        self.assertAlmostEqual(summary["success_rate"], 100.0)
        self.assertEqual(summary["response_time"]["avg"], 83.33)

        # Text report is non-empty
        text = report.format_text()
        self.assertIn("TEST REPORT", text)
        self.assertIn("get_user_info", text)


# ===================================================================
# Scenario 2: Auth failure → refresh → retry
# ===================================================================

class TestScenario2AuthRefresh(unittest.TestCase):
    """Token is initially expired/invalid; refresh restores access."""

    def test_auth_refresh_retries(self):
        # First auth call fails, second succeeds
        # We use a custom transport that flips state after first call
        transport = MockTransport(MockMode.REALISTIC)
        call_count = {"n": 0}

        original_request = transport.request

        def _flipping_request(method, url, headers=None, body=None):
            route_key = None
            if "/contact/v3/users/" in url:
                route_key = "user"

            if route_key == "user" and call_count["n"] == 0:
                call_count["n"] += 1
                return USER_AUTH_FAIL  # 401 first time
            return original_request(method, url, headers, body)

        transport.request = _flipping_request
        auth, client = _wire_clients(transport)

        report = TestReport()

        # First attempt: auth failure
        with MockUrllibAdapter(transport).patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.AUTH)
        report.add_record(TestRecord("get_user_info", "fail", 30.0, error_type="auth_error"))

        # Simulate token refresh + retry
        auth._tenant_token = None  # force re-auth
        with MockUrllibAdapter(transport).patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.open_id, "ou_mock_user_001")
        report.add_record(TestRecord("get_user_info", "success", 35.0))

        summary = report.get_summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertEqual(summary["error_breakdown"]["auth_error"], 1)

    def test_user_token_refresh(self):
        """User token refresh via refresh_token flow."""
        transport = MockTransport(MockMode.REALISTIC)
        auth, _ = _wire_clients(transport)

        # Set up user credentials that are already expired
        auth.set_user_credentials(
            access_token="expired-user-token",
            refresh_token="mock-refresh-token",
            expires_in=-1,  # already expired
        )

        # Getting user token should trigger refresh
        token = auth.get_user_token()
        self.assertEqual(token, "mock-user-token-refreshed")


# ===================================================================
# Scenario 3: Rate limit → backoff → retry
# ===================================================================

class TestScenario3RateLimit(unittest.TestCase):
    """Rate limit (429) triggers exponential backoff, then succeeds."""

    def test_rate_limit_retry_success(self):
        transport = MockTransport(MockMode.REALISTIC)
        call_count = {"n": 0}

        original_request = transport.request

        def _rate_limit_then_ok(method, url, headers=None, body=None):
            route_key = None
            if "/im/v1/messages" in url:
                route_key = "message"

            if route_key == "message" and call_count["n"] < 2:
                call_count["n"] += 1
                return MSG_SUCCESS if call_count["n"] >= 2 else USER_RATE_LIMIT
            return original_request(method, url, headers, body)

        transport.request = _rate_limit_then_ok

        # Custom retry function: detect 429 from FeishuClient → retry
        report = TestReport()

        # First call returns rate limit
        with MockUrllibAdapter(transport).patch():
            resp = client_send_with_retry(transport, "ou_mock_user_001", "text", '{"text":"hi"}')

        # After retries, should succeed
        self.assertTrue(resp.success)
        report.add_record(TestRecord("send_message", "success", 150.0))

        summary = report.get_summary()
        self.assertEqual(summary["success"], 1)

    def test_rate_limiter_execute_with_retry(self):
        """RateLimiter.execute_with_retry works with mock function."""
        limiter = RateLimiter(base_delay=0.001, jitter=0.001)  # fast for tests

        attempt = {"n": 0}

        def _flaky():
            attempt["n"] += 1
            if attempt["n"] < 3:
                raise RateLimitError("429")
            return (200, {}, "ok")

        result = limiter.execute_with_retry(_flaky, max_retries=3)
        self.assertEqual(result, "ok")
        self.assertEqual(attempt["n"], 3)

    def test_rate_limit_exhausted(self):
        """RateLimiter raises after max retries."""
        limiter = RateLimiter(base_delay=0.001, jitter=0.001)

        def _always_429():
            raise RateLimitError("429")

        with self.assertRaises(RateLimitError):
            limiter.execute_with_retry(_always_429, max_retries=2)

    def test_should_retry_classification(self):
        limiter = RateLimiter()
        self.assertTrue(limiter.should_retry(429))
        self.assertTrue(limiter.should_retry(500))
        self.assertTrue(limiter.should_retry(502))
        self.assertTrue(limiter.should_retry(503))
        self.assertFalse(limiter.should_retry(400))
        self.assertFalse(limiter.should_retry(401))
        self.assertFalse(limiter.should_retry(403))
        self.assertFalse(limiter.should_retry(404))


# ===================================================================
# Scenario 4: Mixed success/failure → report statistics
# ===================================================================

class TestScenario4MixedResults(unittest.TestCase):
    """A mix of successes and failures; report aggregates correctly."""

    def test_mixed_report(self):
        transport = MockTransport(MockMode.REALISTIC)
        auth, client = _wire_clients(transport)
        report = TestReport()

        # Success: user query
        with MockUrllibAdapter(transport).patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertTrue(resp.success)
        report.add_record(TestRecord("get_user_info", "success", 25.0))

        # Fail: user auth error (via route override)
        transport_fail = MockTransport(
            MockMode.REALISTIC,
            route_overrides={"user": USER_AUTH_FAIL},
        )
        client_fail = FeishuClient(access_token=auth.get_tenant_token())
        with MockUrllibAdapter(transport_fail).patch():
            resp = client_fail.get_user_info("ou_mock_user_001")
        self.assertFalse(resp.success)
        report.add_record(TestRecord("get_user_info", "fail", 15.0, error_type="auth_error"))

        # Success: send message (original transport)
        with MockUrllibAdapter(transport).patch():
            resp = client.send_message("ou_mock_user_001", "text", '{"text":"test"}')
        self.assertTrue(resp.success)
        report.add_record(TestRecord("send_message", "success", 55.0))

        # Fail: calendar rate limit
        transport_cal_fail = MockTransport(
            MockMode.REALISTIC,
            route_overrides={"calendar": CAL_RATE_LIMIT},
        )
        client_cal_fail = FeishuClient(access_token=auth.get_tenant_token())
        with MockUrllibAdapter(transport_cal_fail).patch():
            resp = client_cal_fail.list_calendar_events("1700000000", "1700003600")
        self.assertFalse(resp.success)
        report.add_record(TestRecord("list_calendar_events", "fail", 200.0, error_type="rate_limit"))

        # --- Report assertions ---
        summary = report.get_summary()
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["success"], 2)
        self.assertEqual(summary["fail"], 2)
        self.assertAlmostEqual(summary["success_rate"], 50.0)

        # Error breakdown
        self.assertEqual(summary["error_breakdown"]["auth_error"], 1)
        self.assertEqual(summary["error_breakdown"]["rate_limit"], 1)

        # Per-endpoint stats
        user_stats = report.get_by_endpoint("get_user_info")
        self.assertEqual(user_stats["total"], 2)
        self.assertEqual(user_stats["success"], 1)
        self.assertEqual(user_stats["fail"], 1)

        msg_stats = report.get_by_endpoint("send_message")
        self.assertEqual(msg_stats["total"], 1)
        self.assertEqual(msg_stats["success"], 1)

        cal_stats = report.get_by_endpoint("list_calendar_events")
        self.assertEqual(cal_stats["total"], 1)
        self.assertEqual(cal_stats["fail"], 1)

        # JSON output is valid
        json_str = report.format_json()
        data = json.loads(json_str)
        self.assertIn("summary", data)
        self.assertIn("by_endpoint", data)

        # Text report contains all endpoints
        text = report.format_text()
        self.assertIn("get_user_info", text)
        self.assertIn("send_message", text)
        self.assertIn("list_calendar_events", text)
        self.assertIn("auth_error", text)
        self.assertIn("rate_limit", text)


# ===================================================================
# Scenario 5: All failures → report correctness
# ===================================================================

class TestScenario5AllFail(unittest.TestCase):
    """Every request fails; report still aggregates correctly."""

    def test_all_fail_report(self):
        fail_transport = MockTransport(
            MockMode.REALISTIC,
            route_overrides={
                "user": USER_AUTH_FAIL,
                "message": MSG_PARAM_ERROR,
                "calendar": CAL_SERVER_ERROR,
            },
        )
        auth, _ = _wire_clients(fail_transport)
        client = FeishuClient(access_token=auth.get_tenant_token())
        report = TestReport()

        # User: auth failure
        with MockUrllibAdapter(fail_transport).patch():
            resp = client.get_user_info("ou_mock_user_001")
        self.assertFalse(resp.success)
        report.add_record(TestRecord("get_user_info", "fail", 10.0, error_type="auth_error"))

        # Message: param error
        with MockUrllibAdapter(fail_transport).patch():
            # This endpoint has its own param validation, but we override
            # route to return MSG_PARAM_ERROR — need valid params to reach HTTP
            resp = client.send_message("ou_mock_user_001", "text", '{"text":"x"}')
        self.assertFalse(resp.success)
        report.add_record(TestRecord("send_message", "fail", 5.0, error_type="param_error"))

        # Calendar: server error
        with MockUrllibAdapter(fail_transport).patch():
            resp = client.list_calendar_events("1700000000", "1700003600")
        self.assertFalse(resp.success)
        report.add_record(TestRecord("list_calendar_events", "fail", 300.0, error_type="server_error"))

        # Report assertions
        summary = report.get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["success"], 0)
        self.assertEqual(summary["fail"], 3)
        self.assertAlmostEqual(summary["success_rate"], 0.0)

        # All three error types present
        self.assertEqual(summary["error_breakdown"]["auth_error"], 1)
        self.assertEqual(summary["error_breakdown"]["param_error"], 1)
        self.assertEqual(summary["error_breakdown"]["server_error"], 1)

        # Text report shows 0% success
        text = report.format_text()
        self.assertIn("Rate: 0.0%", text)

        # JSON report
        data = json.loads(report.format_json())
        self.assertEqual(data["summary"]["success_rate"], 0.0)


# ===================================================================
# Helper for Scenario 3 retry logic
# ===================================================================

def client_send_with_retry(transport, receive_id, msg_type, content, max_retries=3):
    """Send a message with manual retry on rate limit."""
    client = FeishuClient(access_token="mock-tenant-token-abc123")
    for attempt in range(max_retries + 1):
        with MockUrllibAdapter(transport).patch():
            resp = client.send_message(receive_id, msg_type, content)
        if resp.success:
            return resp
        if resp.error_type == FeishuErrorType.RATE_LIMIT and attempt < max_retries:
            time.sleep(0.001)  # minimal backoff for tests
            continue
        return resp
    return resp


# ===================================================================
# Cross-cutting: no real HTTP requests
# ===================================================================

class TestNoRealHTTP(unittest.TestCase):
    """Verify that no real urllib calls leak through."""

    def test_transport_request_log(self):
        """MockTransport records all requests and never touches network."""
        transport = MockTransport(MockMode.REALISTIC)
        auth, client = _wire_clients(transport)

        # Make several calls
        with MockUrllibAdapter(transport).patch():
            client.get_user_info("ou_mock_user_001")
            client.send_message("ou_mock_user_001", "text", '{"text":"hi"}')
            client.list_calendar_events("1700000000", "1700003600")

        # All requests went through mock
        self.assertTrue(len(transport.request_log) >= 3)
        for req in transport.request_log:
            self.assertIn("feishu.cn", req["url"])

    def test_auth_uses_mock_client(self):
        """AuthManager with injected http_client never calls urllib."""
        transport = MockTransport(MockMode.REALISTIC)
        auth = AuthManager(
            app_id="test", app_secret="test",
            http_client=MockHttpClient(transport),
        )
        token = auth.get_tenant_token()
        self.assertEqual(token, "mock-tenant-token-abc123")
        # Verify the request was logged in mock transport
        self.assertTrue(any("tenant_access_token" in r["url"] for r in transport.request_log))


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases(unittest.TestCase):
    """Boundary conditions and error handling."""

    def test_empty_report(self):
        report = TestReport()
        summary = report.get_summary()
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["success_rate"], 0.0)
        self.assertEqual(summary["response_time"]["avg"], 0.0)

    def test_single_success(self):
        report = TestReport()
        report.add_record(TestRecord("ping", "success", 10.0))
        summary = report.get_summary()
        self.assertEqual(summary["success_rate"], 100.0)

    def test_single_failure(self):
        report = TestReport()
        report.add_record(TestRecord("ping", "fail", 10.0, error_type="timeout"))
        summary = report.get_summary()
        self.assertEqual(summary["success_rate"], 0.0)
        self.assertEqual(summary["error_breakdown"]["timeout"], 1)

    def test_report_format_text_empty(self):
        report = TestReport()
        text = report.format_text()
        self.assertIn("TEST REPORT", text)
        self.assertIn("0 requests", text)

    def test_invalid_status_in_record(self):
        with self.assertRaises(ValueError):
            TestRecord("x", "pending", 10.0)

    def test_fail_without_error_type(self):
        with self.assertRaises(ValueError):
            TestRecord("x", "fail", 10.0)

    def test_endpoint_param_validation(self):
        """FeishuClient returns param errors without HTTP call."""
        client = FeishuClient(access_token="test")
        resp = client.get_user_info("")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

        resp = client.send_message("", "text", "{}")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)

        resp = client.list_calendar_events("", "")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_type, FeishuErrorType.PARAM)


# ===================================================================
# Main
# ===================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
