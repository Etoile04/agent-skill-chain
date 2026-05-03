"""Approval Gate - risk-based auto-approval and manual review for agent operations."""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRequest:
    request_id: str
    operation: str
    agent_id: str
    risk_level: str
    details: dict
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None

    @property
    def requires_human_approval(self) -> bool:
        return self.risk_level in ("high", "medium")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        data = dict(data)
        data["status"] = ApprovalStatus(data["status"])
        return cls(**data)


class ApprovalGate:
    def __init__(self, persistence_path: str, auto_approve_low_risk: bool = True):
        self.persistence_path = persistence_path
        self.auto_approve_low_risk = auto_approve_low_risk
        self._requests: dict[str, ApprovalRequest] = {}
        self.load()

    def submit(self, operation: str, agent_id: str, risk_level: str, details: dict) -> str:
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            request_id=request_id,
            operation=operation,
            agent_id=agent_id,
            risk_level=risk_level,
            details=details,
        )
        if self.auto_approve_low_risk and risk_level == "low":
            req.status = ApprovalStatus.APPROVED
            req.approver = "auto"
            req.resolved_at = datetime.now(timezone.utc).isoformat()
        self._requests[request_id] = req
        return request_id

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def approve(self, request_id: str, approver: str) -> bool:
        req = self._requests.get(request_id)
        if req is None or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.APPROVED
        req.approver = approver
        req.resolved_at = datetime.now(timezone.utc).isoformat()
        return True

    def reject(self, request_id: str, approver: str, reason: str = "") -> bool:
        req = self._requests.get(request_id)
        if req is None or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.REJECTED
        req.approver = approver
        req.reason = reason
        req.resolved_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    def save(self):
        data = {rid: req.to_dict() for rid, req in self._requests.items()}
        with open(self.persistence_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        try:
            with open(self.persistence_path, "r") as f:
                data = json.load(f)
            self._requests = {rid: ApprovalRequest.from_dict(d) for rid, d in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self._requests = {}
