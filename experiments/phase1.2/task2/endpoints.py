"""Feishu API endpoint wrappers: user info, messaging, calendar."""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FeishuErrorType(Enum):
    NETWORK = "network_error"
    AUTH = "auth_error"
    PARAM = "param_error"
    RATE_LIMIT = "rate_limit"
    SERVER = "server_error"
    UNKNOWN = "unknown_error"


@dataclass
class FeishuResponse:
    success: bool
    data: Any = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    error_type: Optional[FeishuErrorType] = None


@dataclass
class UserInfo:
    open_id: str = ""
    name: str = ""
    avatar_url: str = ""
    email: str = ""
    mobile: str = ""
    department_id: str = ""


@dataclass
class MessageResult:
    message_id: str = ""
    create_time: str = ""


@dataclass
class CalendarEvent:
    event_id: str = ""
    summary: str = ""
    start_time: str = ""
    end_time: str = ""


# Map HTTP status / API error codes to FeishuErrorType
def _classify_error(status_code: int, api_code: Optional[int] = None) -> FeishuErrorType:
    if status_code == 401 or (api_code and api_code in (99991668, 99991663)):
        return FeishuErrorType.AUTH
    if status_code == 400 or (api_code and api_code in (99991400, 99991401)):
        return FeishuErrorType.PARAM
    if status_code == 429 or (api_code and api_code == 99991403):
        return FeishuErrorType.RATE_LIMIT
    if status_code >= 500:
        return FeishuErrorType.SERVER
    return FeishuErrorType.UNKNOWN


def _parse_response(raw: bytes, status_code: int) -> FeishuResponse:
    """Parse JSON response body into FeishuResponse."""
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return FeishuResponse(
            success=False,
            error_code="PARSE_ERROR",
            error_msg=str(exc),
            error_type=FeishuErrorType.UNKNOWN,
        )

    api_code = body.get("code", 0)
    if api_code == 0:
        return FeishuResponse(success=True, data=body.get("data", {}))

    error_type = _classify_error(status_code, api_code)
    return FeishuResponse(
        success=False,
        error_code=str(api_code),
        error_msg=body.get("msg", ""),
        error_type=error_type,
    )


class FeishuClient:
    """Lightweight Feishu Open API client."""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, access_token: str = ""):
        self._token = access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> FeishuResponse:
        url = f"{self.BASE_URL}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return _parse_response(resp.read(), resp.status)
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            return _parse_response(raw, exc.code)
        except urllib.error.URLError as exc:
            return FeishuResponse(
                success=False,
                error_code="NETWORK_ERROR",
                error_msg=str(exc.reason),
                error_type=FeishuErrorType.NETWORK,
            )

    # ---- Public API ----

    def get_user_info(self, open_id: str) -> FeishuResponse:
        """GET /contact/v3/users/{open_id}"""
        if not open_id:
            return FeishuResponse(
                success=False,
                error_code="PARAM_ERROR",
                error_msg="open_id is required",
                error_type=FeishuErrorType.PARAM,
            )
        resp = self._request("GET", f"/contact/v3/users/{open_id}")
        if resp.success and isinstance(resp.data, dict):
            user = resp.data.get("user", {})
            resp.data = UserInfo(
                open_id=user.get("open_id", ""),
                name=user.get("name", ""),
                avatar_url=user.get("avatar", {}).get("avatar_72", ""),
                email=user.get("email", ""),
                mobile=user.get("mobile", ""),
                department_id=user.get("department_ids", [""])[0] if user.get("department_ids") else "",
            )
        return resp

    def send_message(self, receive_id: str, msg_type: str, content: str) -> FeishuResponse:
        """POST /im/v1/messages"""
        if not receive_id or not msg_type or not content:
            return FeishuResponse(
                success=False,
                error_code="PARAM_ERROR",
                error_msg="receive_id, msg_type and content are required",
                error_type=FeishuErrorType.PARAM,
            )
        body = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,
        }
        resp = self._request("POST", "/im/v1/messages", body)
        if resp.success and isinstance(resp.data, dict):
            if "message_id" in resp.data:
                resp.data = MessageResult(
                    message_id=resp.data["message_id"],
                    create_time=resp.data.get("create_time", ""),
                )
        return resp

    def list_calendar_events(self, start_time: str, end_time: str) -> FeishuResponse:
        """GET /calendar/v4/calendars/{calendar_id}/events"""
        if not start_time or not end_time:
            return FeishuResponse(
                success=False,
                error_code="PARAM_ERROR",
                error_msg="start_time and end_time are required",
                error_type=FeishuErrorType.PARAM,
            )
        # Use primary calendar
        path = f"/calendar/v4/calendars/primary/events?start_time={start_time}&end_time={end_time}"
        resp = self._request("GET", path)
        if resp.success and isinstance(resp.data, dict):
            items = resp.data.get("items", [])
            resp.data = [
                CalendarEvent(
                    event_id=e.get("event_id", ""),
                    summary=e.get("summary", ""),
                    start_time=e.get("start_time", ""),
                    end_time=e.get("end_time", ""),
                )
                for e in items
            ]
        return resp
