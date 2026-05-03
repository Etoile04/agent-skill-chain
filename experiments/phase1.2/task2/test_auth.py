"""Tests for auth.py — Feishu API authentication layer."""

import unittest
import time
from unittest.mock import MagicMock, patch
from auth import AuthManager, TokenInfo


class FakeHTTPClient:
    """Mock HTTP client that returns canned responses."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def add_response(self, url: str, response: dict):
        self._responses[url] = response

    def post(self, url, headers=None, body=None):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if url in self._responses:
            return self._responses[url]
        return {"code": 1, "msg": "no mock response"}


def _make_auth(**kwargs):
    http = FakeHTTPClient()
    mgr = AuthManager(app_id="test_app", app_secret="test_secret", http_client=http, **kwargs)
    return mgr, http


class TestTokenInfo(unittest.TestCase):
    def test_not_expired_initially(self):
        t = TokenInfo("tok", time.time() + 7200)
        self.assertFalse(t.is_expired())

    def test_expired_when_past(self):
        t = TokenInfo("tok", time.time() - 1)
        self.assertTrue(t.is_expired())

    def test_buffer_triggers_expiry(self):
        # Token expires in 200s, default buffer is 300s → should be "expired"
        t = TokenInfo("tok", time.time() + 200)
        self.assertTrue(t.is_expired())

    def test_custom_buffer(self):
        t = TokenInfo("tok", time.time() + 200)
        self.assertFalse(t.is_expired(buffer_seconds=100))


class TestTenantToken(unittest.TestCase):
    def test_fetch_tenant_token(self):
        mgr, http = _make_auth()
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-abc123",
            "expire": 7200,
        })

        token = mgr.get_tenant_token()
        self.assertEqual(token, "t-abc123")
        self.assertTrue(mgr.is_tenant_token_cached)

        # Should have made exactly one HTTP call
        self.assertEqual(len(http.calls), 1)
        self.assertEqual(http.calls[0]["body"]["app_id"], "test_app")

    def test_tenant_token_cached(self):
        mgr, http = _make_auth()
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-cache",
            "expire": 7200,
        })

        mgr.get_tenant_token()
        mgr.get_tenant_token()
        # Only one HTTP call; second hit the cache
        self.assertEqual(len(http.calls), 1)

    def test_tenant_token_auto_refresh(self):
        mgr, http = _make_auth()
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-first",
            "expire": 100,  # small TTL
        })

        token1 = mgr.get_tenant_token()
        self.assertEqual(token1, "t-first")

        # Manually expire the token
        mgr._tenant_token.expire_time = time.time() - 1

        # Update mock for refresh
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-refreshed",
            "expire": 7200,
        })

        token2 = mgr.get_tenant_token()
        self.assertEqual(token2, "t-refreshed")
        self.assertEqual(len(http.calls), 2)


class TestUserToken(unittest.TestCase):
    def test_set_and_get_user_token(self):
        mgr, _ = _make_auth()
        mgr.set_user_credentials("u-token1", "r-token1", expires_in=7200)

        token = mgr.get_user_token()
        self.assertEqual(token, "u-token1")
        self.assertTrue(mgr.is_user_token_cached)

    def test_user_token_not_initialized_raises(self):
        mgr, _ = _make_auth()
        with self.assertRaises(RuntimeError):
            mgr.get_user_token()

    def test_user_token_auto_refresh(self):
        mgr, http = _make_auth()

        # Need tenant token for refresh call
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-for-refresh",
            "expire": 7200,
        })
        http.add_response(AuthManager.REFRESH_TOKEN_URL, {
            "code": 0,
            "data": {
                "access_token": "u-refreshed",
                "refresh_token": "r-new",
                "expires_in": 7200,
            },
        })

        mgr.set_user_credentials("u-old", "r-old", expires_in=100)
        # Expire it immediately
        mgr._user_token.expire_time = time.time() - 1

        token = mgr.get_user_token()
        self.assertEqual(token, "u-refreshed")
        self.assertEqual(mgr._refresh_token, "r-new")  # refresh_token rotated

    def test_user_refresh_without_refresh_token_raises(self):
        mgr, _ = _make_auth()
        mgr.set_user_credentials("u-tok", "r-tok")
        mgr._user_token.expire_time = time.time() - 1
        mgr._refresh_token = None

        with self.assertRaises(RuntimeError):
            mgr.get_user_token()


class TestGetHeaders(unittest.TestCase):
    def test_tenant_headers(self):
        mgr, http = _make_auth()
        http.add_response(AuthManager.TOKEN_URL, {
            "code": 0,
            "tenant_access_token": "t-hdr",
            "expire": 7200,
        })

        headers = mgr.get_headers(mode="tenant")
        self.assertEqual(headers["Authorization"], "Bearer t-hdr")
        self.assertIn("Content-Type", headers)

    def test_user_headers(self):
        mgr, http = _make_auth()
        mgr.set_user_credentials("u-hdr", "r-hdr")

        headers = mgr.get_headers(mode="user")
        self.assertEqual(headers["Authorization"], "Bearer u-hdr")

    def test_invalid_mode_raises(self):
        mgr, _ = _make_auth()
        with self.assertRaises(ValueError):
            mgr.get_headers(mode="unknown")


if __name__ == "__main__":
    unittest.main()
