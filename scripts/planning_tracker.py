# scripts/planning_tracker.py
"""Planning Quality Tracker: record and analyze StepPlan execution quality."""

import json
import os
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class QualityRecord:
    """A single plan execution record."""
    plan_id: str
    task_type: str
    total_steps: int
    steps_completed: int
    steps_failed: int
    fallbacks_triggered: int
    total_time_ms: float
    tests_total: int = 0
    tests_passed: int = 0
    hint_violations: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def success_rate(self) -> float:
        """Step-level success rate: completed / total."""
        return self.steps_completed / max(self.total_steps, 1)

    def is_success(self) -> bool:
        """Plan is fully successful if no failures and no fallbacks."""
        return self.steps_failed == 0 and self.fallbacks_triggered == 0


class PlanningQualityTracker:
    """Tracks quality of StepPlan executions — success rates, fallback rates,
    per-task-type stats. Helps evaluate whether the planning system improves."""

    def __init__(self, path: Optional[str] = None):
        self._records: List[QualityRecord] = []
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def record(self, rec: QualityRecord) -> None:
        """Add a quality record."""
        self._records.append(rec)

    def overall_success_rate(self) -> float:
        """Fraction of plans that are fully successful (no failures, no fallbacks)."""
        if not self._records:
            return 0.0
        successes = sum(1 for r in self._records if r.is_success())
        return successes / len(self._records)

    def avg_step_success_rate(self) -> float:
        """Average step completion rate across all plans."""
        if not self._records:
            return 0.0
        total = sum(r.total_steps for r in self._records)
        completed = sum(r.steps_completed for r in self._records)
        return completed / max(total, 1)

    def fallback_rate(self) -> float:
        """Fraction of plans that triggered at least one fallback."""
        if not self._records:
            return 0.0
        with_fallback = sum(1 for r in self._records if r.fallbacks_triggered > 0)
        return with_fallback / len(self._records)

    def stats_by_task_type(self, task_type: str) -> dict:
        """Aggregate statistics for a specific task type."""
        recs = [r for r in self._records if r.task_type == task_type]
        if not recs:
            return {"count": 0}
        return {
            "count": len(recs),
            "avg_steps": sum(r.total_steps for r in recs) / len(recs),
            "avg_success_rate": sum(r.success_rate() for r in recs) / len(recs),
        }

    def save(self) -> None:
        """Persist records to JSON file."""
        if self._path:
            data = [asdict(r) for r in self._records]
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load records from JSON file."""
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                return  # empty file, no records
            data = json.loads(content)
            self._records = [QualityRecord(**d) for d in data]
