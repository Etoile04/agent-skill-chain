"""Task Router - capability-based routing with confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

from agent_registry import AgentRegistry


@dataclass
class RoutingDecision:
    """Represents a routing decision for a task."""
    task_type: str
    assigned_agent: str
    confidence: float
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def needs_approval(self) -> bool:
        """Returns True if confidence is below the approval threshold (0.5)."""
        return self.confidence < 0.5


class TaskRouter:
    """Routes tasks to the best available agent based on capability matching."""

    def __init__(self, registry: AgentRegistry):
        self._registry = registry
        self._history: List[RoutingDecision] = []

    def route(self, task_type: str) -> Optional[RoutingDecision]:
        """Route a task to the best agent. Returns None if no capable agent found."""
        agent = self._registry.find_best_for_task(task_type)
        if agent is None:
            return None

        confidence = agent.confidence_threshold

        decision = RoutingDecision(
            task_type=task_type,
            assigned_agent=agent.agent_id,
            confidence=confidence,
            reason=f"Best capability match for {task_type} (confidence={confidence:.2f})"
        )
        self._history.append(decision)
        return decision

    def get_history(self) -> List[RoutingDecision]:
        """Return all routing decisions made so far."""
        return list(self._history)
