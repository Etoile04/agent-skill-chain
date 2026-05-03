# scripts/budget-tracker.py
"""Token and cost budget tracker with per-task tracking and threshold alerts."""

import json
import os
from typing import Optional
from collections import defaultdict


class BudgetTracker:
    """Token and cost budget tracker with per-task breakdown and alerts."""

    def __init__(self, tokens_budget: float = 0, cost_budget_usd: float = 0,
                 alert_threshold_pct: float = 80, path: Optional[str] = None):
        self.tokens_budget = tokens_budget
        self.cost_budget_usd = cost_budget_usd
        self.alert_threshold_pct = alert_threshold_pct
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self._per_task = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def record(self, tokens: int, cost_usd: float, task_id: Optional[str] = None) -> None:
        """Record token usage and cost. Optionally attribute to a specific task."""
        self.total_tokens += tokens
        self.total_cost_usd += cost_usd
        if task_id:
            self._per_task[task_id]["tokens"] += tokens
            self._per_task[task_id]["cost"] += cost_usd

    def tokens_remaining(self) -> float:
        return max(self.tokens_budget - self.total_tokens, 0)

    def cost_remaining_usd(self) -> float:
        return max(self.cost_budget_usd - self.total_cost_usd, 0)

    def is_over_budget(self) -> bool:
        return self.total_tokens > self.tokens_budget or self.total_cost_usd > self.cost_budget_usd

    def usage_pct_tokens(self) -> float:
        if self.tokens_budget == 0:
            return 0.0
        return round(self.total_tokens / self.tokens_budget * 100, 1)

    def usage_pct_cost(self) -> float:
        if self.cost_budget_usd == 0:
            return 0.0
        return round(self.total_cost_usd / self.cost_budget_usd * 100, 1)

    def task_tokens(self, task_id: str) -> int:
        return self._per_task[task_id]["tokens"]

    def check_alerts(self) -> list:
        """Check for threshold breaches and return alert messages."""
        alerts = []
        if self.usage_pct_tokens() >= self.alert_threshold_pct:
            alerts.append(f"Token usage at {self.usage_pct_tokens()}% (threshold: {self.alert_threshold_pct}%)")
        if self.usage_pct_cost() >= self.alert_threshold_pct:
            alerts.append(f"Cost usage at {self.usage_pct_cost()}% (threshold: {self.alert_threshold_pct}%)")
        if self.is_over_budget():
            alerts.append("OVER BUDGET")
        return alerts

    def save(self) -> None:
        if self._path:
            data = {
                "total_tokens": self.total_tokens,
                "total_cost_usd": self.total_cost_usd,
                "tokens_budget": self.tokens_budget,
                "cost_budget_usd": self.cost_budget_usd,
                "per_task": dict(self._per_task),
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.total_tokens = data.get("total_tokens", 0)
            self.total_cost_usd = data.get("total_cost_usd", 0.0)
            self.tokens_budget = data.get("tokens_budget", self.tokens_budget)
            self.cost_budget_usd = data.get("cost_budget_usd", self.cost_budget_usd)
            self._per_task = defaultdict(
                lambda: {"tokens": 0, "cost": 0.0},
                data.get("per_task", {})
            )
