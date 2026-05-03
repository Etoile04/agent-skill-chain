"""Agent Registry: AgentCard dataclass + AgentRegistry manager."""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AgentCard:
    agent_id: str
    name: str
    capabilities: list[str]
    specializations: list[str]
    max_concurrent_tasks: int
    confidence_threshold: float
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def skill_coverage(self) -> dict[str, float]:
        """Return capability → confidence mapping."""
        return {cap: self.confidence_threshold for cap in self.capabilities}

    def can_handle(self, task_type: str) -> bool:
        return task_type in self.capabilities

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentCard":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class AgentRegistry:
    def __init__(self, path: str):
        self.path = path
        self._agents: dict[str, AgentCard] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                data = json.load(f)
            for d in data:
                card = AgentCard.from_dict(d)
                self._agents[card.agent_id] = card

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([c.to_dict() for c in self._agents.values()], f, indent=2)

    def register(self, card: AgentCard):
        if card.agent_id in self._agents:
            card.created_at = self._agents[card.agent_id].created_at
        card.updated_at = time.time()
        self._agents[card.agent_id] = card

    def get(self, agent_id: str) -> Optional[AgentCard]:
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentCard]:
        return list(self._agents.values())

    def find_by_capability(self, capability: str) -> list[AgentCard]:
        return [a for a in self._agents.values() if a.can_handle(capability)]

    def find_best_for_task(self, task_type: str) -> Optional[AgentCard]:
        candidates = self.find_by_capability(task_type)
        if not candidates:
            return None
        return max(candidates, key=lambda a: (a.confidence_threshold, len(a.capabilities)))

    def unregister(self, agent_id: str):
        self._agents.pop(agent_id, None)
