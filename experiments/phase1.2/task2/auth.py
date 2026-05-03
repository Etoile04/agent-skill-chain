"""Feishu API authentication layer: token management with auto-refresh.

Supports two identity modes:
- App (tenant_access_token): for application-level API calls
- User (user_access_token): for user-delegated API calls
"""

import time
import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any


class TokenInfo:
    """Holds a token string with its expiry timestamp."""

    def __init__(self, token: str, expire_time: float):
        self.token = token
        self.expire_time = expire_time  # absolute timestamp (time.time())

    def is_expired(self, buffer_seconds: float = 300) -> bool:
        """Check if token is expired or will expire within buffer."""
        return time.time() >= (self.expire_time - buffer_seconds)


class AuthManager:
    """Manages Feishu API authentication tokens.

    Supports:
    - tenant_access_token (app identity)
    - user_access_token (user identity, via OAuth refresh)
    """

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    REFRESH_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/oidc/refresh_access_token"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        http_client: Optional[Any] = None,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self._http_client = http_client  # injectable for testing
        self._tenant_token: Optional[TokenInfo] = None
        self._user_token: Optional[TokenInfo] = None
        self._refresh_token: Optional[str] = None

    # -- HTTP abstraction (mockable) --

    def _http_post(self, url: str, headers: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict:
        """Make an HTTP POST and return parsed JSON response."""
        if self._http_client is not None:
            return self._http_client.post(url, headers=headers, body=body)

        req_headers = {"Content-Type": "application/json; charset=utf-8"}
        if headers:
            req_headers.update(headers)

        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode("utf-8"))

    # -- Tenant (app) token --

    def get_tenant_token(self) -> str:
        """Get a valid tenant_access_token, refreshing if needed."""
        if self._tenant_token is None or self._tenant_token.is_expired():
            self._refresh_tenant_token()
        return self._tenant_token.token

    def _refresh_tenant_token(self) -> None:
        """Fetch a new tenant_access_token from Feishu API."""
        resp = self._http_post(
            self.TOKEN_URL,
            body={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
        )
        self._tenant_token = TokenInfo(
            token=resp["tenant_access_token"],
            expire_time=time.time() + resp.get("expire", 7200),
        )

    # -- User token --

    def set_user_credentials(self, access_token: str, refresh_token: str, expires_in: int = 7200) -> None:
        """Manually set user token credentials (e.g. after initial OAuth flow)."""
        self._user_token = TokenInfo(
            token=access_token,
            expire_time=time.time() + expires_in,
        )
        self._refresh_token = refresh_token

    def get_user_token(self) -> str:
        """Get a valid user_access_token, refreshing if needed."""
        if self._user_token is None:
            raise RuntimeError("User token not initialized. Call set_user_credentials first.")
        if self._user_token.is_expired():
            self._refresh_user_token()
        return self._user_token.token

    def _refresh_user_token(self) -> None:
        """Refresh user_access_token using the refresh_token."""
        if not self._refresh_token:
            raise RuntimeError("No refresh_token available for user token refresh.")

        # Need a tenant token for the refresh request
        tenant_token = self.get_tenant_token()

        resp = self._http_post(
            self.REFRESH_TOKEN_URL,
            headers={"Authorization": f"Bearer {tenant_token}"},
            body={"grant_type": "refresh_token", "refresh_token": self._refresh_token},
        )

        data = resp.get("data", resp)
        self._user_token = TokenInfo(
            token=data["access_token"],
            expire_time=time.time() + data.get("expires_in", 7200),
        )
        # Update refresh_token if a new one is provided
        if "refresh_token" in data:
            self._refresh_token = data["refresh_token"]

    # -- Unified header builder --

    def get_headers(self, mode: str = "tenant") -> Dict[str, str]:
        """Return authorization headers for the given mode.

        Args:
            mode: "tenant" for app identity, "user" for user identity.

        Returns:
            Dict with Authorization header set.
        """
        if mode == "tenant":
            token = self.get_tenant_token()
        elif mode == "user":
            token = self.get_user_token()
        else:
            raise ValueError(f"Unknown auth mode: {mode!r}. Use 'tenant' or 'user'.")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    # -- Introspection helpers (useful for testing) --

    @property
    def is_tenant_token_cached(self) -> bool:
        return self._tenant_token is not None

    @property
    def is_user_token_cached(self) -> bool:
        return self._user_token is not None
