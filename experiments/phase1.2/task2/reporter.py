"""Test report generation: response time, success rate, error breakdown."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TestRecord:
    endpoint: str
    status: str  # "success" or "fail"
    response_time_ms: float
    error_type: Optional[str] = None
    timestamp: Optional[str] = None  # ISO 8601

    def __post_init__(self):
        if self.status not in ("success", "fail"):
            raise ValueError(f"status must be 'success' or 'fail', got '{self.status}'")
        if self.status == "fail" and self.error_type is None:
            raise ValueError("error_type is required when status is 'fail'")


def _percentile(sorted_data: list[float], pct: float) -> float:
    """Compute percentile using nearest-rank method."""
    if not sorted_data:
        return 0.0
    k = (pct / 100.0) * (len(sorted_data) - 1)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def _compute_timing(times: list[float]) -> dict:
    """Return avg, p50, p95, p99 from a list of response times."""
    if not times:
        return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
    s = sorted(times)
    return {
        "avg": round(statistics.mean(s), 2),
        "p50": round(_percentile(s, 50), 2),
        "p95": round(_percentile(s, 95), 2),
        "p99": round(_percentile(s, 99), 2),
    }


class TestReport:
    def __init__(self):
        self._records: list[TestRecord] = []

    def add_record(self, record: TestRecord) -> None:
        self._records.append(record)

    # ---- core stats ----

    def _base_stats(self, records: list[TestRecord]) -> dict:
        total = len(records)
        if total == 0:
            return {
                "total": 0, "success": 0, "fail": 0,
                "success_rate": 0.0,
                "response_time": {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0},
                "error_breakdown": {},
            }
        success = sum(1 for r in records if r.status == "success")
        fail = total - success
        times = [r.response_time_ms for r in records]
        error_breakdown: dict[str, int] = {}
        for r in records:
            if r.status == "fail" and r.error_type:
                error_breakdown[r.error_type] = error_breakdown.get(r.error_type, 0) + 1
        return {
            "total": total,
            "success": success,
            "fail": fail,
            "success_rate": round(success / total * 100, 2),
            "response_time": _compute_timing(times),
            "error_breakdown": error_breakdown,
        }

    def get_summary(self) -> dict:
        return self._base_stats(self._records)

    def get_by_endpoint(self, endpoint: str) -> dict:
        records = [r for r in self._records if r.endpoint == endpoint]
        stats = self._base_stats(records)
        stats["endpoint"] = endpoint
        return stats

    def get_all_endpoints(self) -> dict[str, dict]:
        endpoints = sorted({r.endpoint for r in self._records})
        return {ep: self.get_by_endpoint(ep) for ep in endpoints}

    # ---- formatters ----

    def format_text(self) -> str:
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("  TEST REPORT")
        lines.append("=" * 60)

        # Overall summary
        summary = self.get_summary()
        lines.append(f"\nOverall: {summary['total']} requests | "
                      f"Success: {summary['success']} | Fail: {summary['fail']} | "
                      f"Rate: {summary['success_rate']}%")
        rt = summary["response_time"]
        lines.append(f"Response Time (ms): avg={rt['avg']}  p50={rt['p50']}  "
                      f"p95={rt['p95']}  p99={rt['p99']}")
        if summary["error_breakdown"]:
            lines.append("Error Breakdown:")
            for etype, cnt in sorted(summary["error_breakdown"].items()):
                lines.append(f"  {etype}: {cnt}")

        # Per-endpoint
        by_ep = self.get_all_endpoints()
        if by_ep:
            lines.append("\n" + "-" * 60)
            lines.append("  PER-ENDPOINT STATS")
            lines.append("-" * 60)
            for ep, stats in by_ep.items():
                lines.append(f"\n  [{ep}]")
                lines.append(f"    Total: {stats['total']}  Success: {stats['success']}  "
                              f"Fail: {stats['fail']}  Rate: {stats['success_rate']}%")
                srt = stats["response_time"]
                lines.append(f"    Response (ms): avg={srt['avg']}  p50={srt['p50']}  "
                              f"p95={srt['p95']}  p99={srt['p99']}")
                if stats["error_breakdown"]:
                    for etype, cnt in sorted(stats["error_breakdown"].items()):
                        lines.append(f"    Error: {etype}: {cnt}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_json(self, indent: int = 2) -> str:
        return json.dumps({
            "summary": self.get_summary(),
            "by_endpoint": self.get_all_endpoints(),
        }, indent=indent, ensure_ascii=False)
