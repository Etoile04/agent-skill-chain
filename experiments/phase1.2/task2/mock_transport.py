"""Mock transport layer for testing Feishu API toolchain without real HTTP.

Provides a Transport abstraction and a MockTransport implementation with
predefined responses for all three endpoints (auth, user-info, messaging,
calendar) covering success, auth failure, rate limit (429), server error (500),
and network timeout scenarios.
"""

import json
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Transport abstraction
# ---------------------------------------------------------------------------

class TransportError(Exception):
    """Simulates a network-level error (timeout, connection refused, etc.)."""
    pass


class Transport(ABC):
    """Unified HTTP transport interface.

    All concrete transports implement this single method.
    """

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, …).
            url: Full request URL.
            headers: Request headers dict.
            body: JSON-serialisable request body (for POST/PUT).

        Returns:
            (status_code, response_headers, response_body_bytes)
        """
        ...


# ---------------------------------------------------------------------------
# Response mode enum
# ---------------------------------------------------------------------------

class MockMode(Enum):
    ALWAYS_SUCCESS = "always_success"
    ALWAYS_FAIL = "always_fail"
    REALISTIC = "realistic"  # route based on URL pattern


# ---------------------------------------------------------------------------
# Predefined response catalogues
# ---------------------------------------------------------------------------

def _ok_body(**extra) -> bytes:
    base = {"code": 0, "msg": "success"}
    base.update(extra)
    return json.dumps(base).encode("utf-8")


def _err_body(code: int, msg: str) -> bytes:
    return json.dumps({"code": code, "msg": msg}).encode("utf-8")


# --- Auth (tenant_access_token) responses ---

AUTH_SUCCESS = (200, {}, _ok_body(
    tenant_access_token="mock-tenant-token-abc123",
    expire=7200,
))

AUTH_APP_SECRET_INVALID = (200, {}, _err_body(99991663, "app secret invalid"))

# --- User info responses ---

USER_SUCCESS_BODY = _ok_body(data={
    "user": {
        "open_id": "ou_mock_user_001",
        "name": "Mock User",
        "avatar": {"avatar_72": "https://mock.avatar/72.png"},
        "email": "mock@example.com",
        "mobile": "+8613800001111",
        "department_ids": ["0"],
    }
})

USER_SUCCESS = (200, {}, USER_SUCCESS_BODY)

USER_AUTH_FAIL = (401, {}, _err_body(99991668, "Access token expired"))

USER_RATE_LIMIT = (429, {"Retry-After": "5"}, _err_body(99991403, "rate limit exceeded"))

USER_SERVER_ERROR = (500, {}, _err_body(99999999, "internal server error"))

# --- Messaging responses ---

MSG_SUCCESS = (200, {}, _ok_body(data={
    "message_id": "om_mock_msg_001",
    "create_time": "1700000000000",
}))

MSG_PARAM_ERROR = (400, {}, _err_body(99991401, "param error: receive_id is empty"))

# --- Calendar responses ---

CAL_SUCCESS = (200, {}, _ok_body(data={
    "items": [
        {
            "event_id": "evt_mock_001",
            "summary": "Mock Meeting",
            "start_time": "1700000000",
            "end_time": "1700003600",
        }
    ]
}))

CAL_RATE_LIMIT = (429, {"Retry-After": "10"}, _err_body(99991403, "rate limit exceeded"))

CAL_SERVER_ERROR = (500, {}, _err_body(99999999, "internal server error"))

# --- User token refresh ---

REFRESH_SUCCESS_BODY = _ok_body(data={
    "access_token": "mock-user-token-refreshed",
    "expires_in": 7200,
    "refresh_token": "mock-refresh-token-new",
})

REFRESH_SUCCESS = (200, {}, REFRESH_SUCCESS_BODY)

# ---------------------------------------------------------------------------
# URL routing helpers
# ---------------------------------------------------------------------------

def _match_url(url: str) -> str:
    """Return a route key based on the URL path."""
    if "tenant_access_token" in url:
        return "auth"
    if "refresh_access_token" in url:
        return "refresh"
    if "/contact/v3/users/" in url:
        return "user"
    if "/im/v1/messages" in url:
        return "message"
    if "/calendar/v4/" in url:
        return "calendar"
    return "unknown"


# ---------------------------------------------------------------------------
# MockTransport
# ---------------------------------------------------------------------------

class MockTransport(Transport):
    """Mock transport that returns predefined responses without network I/O.

    Modes:
        always_success – every request returns the canonical success response.
        always_fail    – every request returns a 500 server error.
        realistic      – routes based on URL and can be configured per-route.
    """

    def __init__(
        self,
        mode: MockMode = MockMode.REALISTIC,
        delay_seconds: float = 0.0,
        route_overrides: Optional[Dict[str, Tuple[int, Dict, bytes]]] = None,
    ):
        """
        Args:
            mode: Default response mode.
            delay_seconds: Simulated network latency (set 0 for fast tests).
            route_overrides: Per-route override mapping, e.g.
                {"auth": AUTH_APP_SECRET_INVALID, "user": USER_RATE_LIMIT}.
                Keys: "auth", "refresh", "user", "message", "calendar", "unknown".
        """
        self.mode = mode
        self.delay_seconds = delay_seconds
        self.route_overrides = route_overrides or {}
        self.request_log: list = []  # recorded for assertions

    # --- realistic route table ---

    _REALISTIC_MAP: Dict[str, Tuple[int, Dict, bytes]] = {
        "auth": AUTH_SUCCESS,
        "refresh": REFRESH_SUCCESS,
        "user": USER_SUCCESS,
        "message": MSG_SUCCESS,
        "calendar": CAL_SUCCESS,
        "unknown": (404, {}, _err_body(99991404, "not found")),
    }

    # --- Transport interface ---

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, str], bytes]:
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        # Log the request for test assertions
        self.request_log.append({
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
        })

        route = _match_url(url)

        # 1. Per-route override takes precedence
        if route in self.route_overrides:
            return self.route_overrides[route]

        # 2. Mode-based default
        if self.mode == MockMode.ALWAYS_SUCCESS:
            known = {k: v for k, v in self._REALISTIC_MAP.items() if k != "unknown"}
            return known.get(route, (200, {}, _ok_body()))

        if self.mode == MockMode.ALWAYS_FAIL:
            return (500, {}, _err_body(99999999, "mock server error"))

        # REALISTIC
        return self._REALISTIC_MAP.get(route, (404, {}, _err_body(99991404, "not found")))


# ---------------------------------------------------------------------------
# HttpClient adapter for auth.py injection
# ---------------------------------------------------------------------------

class MockHttpClient:
    """Adapter that satisfies the ``http_client`` interface used by AuthManager.

    AuthManager calls ``http_client.post(url, headers, body)`` and expects
    a parsed JSON dict back.  This adapter wraps MockTransport and does the
    (status, headers, body) → dict conversion plus error simulation.
    """

    def __init__(self, transport: MockTransport):
        self.transport = transport

    def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        status, resp_headers, raw = self.transport.request("POST", url, headers, body)
        parsed = json.loads(raw.decode("utf-8"))
        return parsed


# ---------------------------------------------------------------------------
# UrllibTransportAdapter for endpoints.py injection
# ---------------------------------------------------------------------------

class MockUrllibAdapter:
    """Patches ``urllib.request.urlopen`` so that FeishuClient uses MockTransport.

    Usage::

        transport = MockTransport(MockMode.ALWAYS_SUCCESS)
        adapter = MockUrllibAdapter(transport)
        with adapter.patch():
            client = FeishuClient(access_token="test")
            resp = client.get_user_info("ou_xxx")
    """

    def __init__(self, transport: MockTransport):
        self.transport = transport
        self._original_urlopen = None

    def _mock_urlopen(self, req):
        """Drop-in replacement for urllib.request.urlopen."""
        method = req.method if hasattr(req, "method") else "GET"
        url = req.full_url if hasattr(req, "full_url") else str(req)
        headers = dict(req.headers) if hasattr(req, "headers") else {}
        body = None
        if req.data:
            try:
                body = json.loads(req.data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = {"raw": req.data}

        status, resp_headers, raw = self.transport.request(method, url, headers, body)

        # Build a fake response object
        return _MockHTTPResponse(raw, status, resp_headers)

    def patch(self):
        """Context manager that replaces urllib.request.urlopen."""
        import urllib.request
        import contextlib

        self._original_urlopen = urllib.request.urlopen

        @contextlib.contextmanager
        def _ctx():
            urllib.request.urlopen = self._mock_urlopen
            try:
                yield
            finally:
                urllib.request.urlopen = self._original_urlopen

        return _ctx()


class _MockHTTPResponse:
    """Minimal file-like object mimicking http.client.HTTPResponse."""

    def __init__(self, body: bytes, status: int, headers: Dict[str, str]):
        self._body = body
        self.status = status
        self.code = status
        self._headers = headers
        self.fp = None
        self.closed = False

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def get(self, name, default=None):
        return self._headers.get(name, default)
