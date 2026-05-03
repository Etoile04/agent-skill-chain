"""Principle Store: CRUD, effectiveness tracking, and situation matching for behavioral principles."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Principle:
    """A behavioral principle extracted from reflection or error."""

    principle_id: str
    title: str
    description: str
    source: str  # reflection | error | human | autonomous
    trigger: str
    action: str
    tags: list[str] = field(default_factory=list)
    times_applied: int = 0
    times_prevented_error: int = 0
    created_at: float = field(default_factory=time.time)

    def record_application(self, prevented_error: bool = False) -> None:
        """Record that this principle was applied."""
        self.times_applied += 1
        if prevented_error:
            self.times_prevented_error += 1

    def effectiveness(self) -> float:
        """Return the ratio of applications that prevented an error."""
        if self.times_applied == 0:
            return 0.0
        return self.times_prevented_error / self.times_applied

    def to_dict(self) -> dict:
        return {
            "principle_id": self.principle_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "trigger": self.trigger,
            "action": self.action,
            "tags": list(self.tags),
            "times_applied": self.times_applied,
            "times_prevented_error": self.times_prevented_error,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Principle":
        return cls(
            principle_id=data["principle_id"],
            title=data["title"],
            description=data["description"],
            source=data["source"],
            trigger=data["trigger"],
            action=data["action"],
            tags=data.get("tags", []),
            times_applied=data.get("times_applied", 0),
            times_prevented_error=data.get("times_prevented_error", 0),
            created_at=data.get("created_at", time.time()),
        )


class PrincipleStore:
    """Persistent store for principles with search and effectiveness ranking."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._principles: dict[str, Principle] = {}
        self._load()

    def add(self, principle: Principle) -> None:
        """Add or update a principle."""
        self._principles[principle.principle_id] = principle
        self.save()

    def get(self, principle_id: str) -> Optional[Principle]:
        """Get a principle by ID."""
        return self._principles.get(principle_id)

    def list_all(self) -> list[Principle]:
        """Return all principles."""
        return list(self._principles.values())

    def search_by_tag(self, tag: str) -> list[Principle]:
        """Return principles that contain the given tag."""
        return [p for p in self._principles.values() if tag in p.tags]

    def search_by_trigger(self, keyword: str) -> list[Principle]:
        """Return principles whose trigger contains the keyword."""
        return [p for p in self._principles.values() if keyword.lower() in p.trigger.lower()]

    def get_most_effective(self) -> Optional[Principle]:
        """Return the principle with the highest effectiveness score."""
        if not self._principles:
            return None
        return max(self._principles.values(), key=lambda p: p.effectiveness())

    def get_for_situation(self, situation: str) -> list[Principle]:
        """Return principles whose trigger matches the situation keyword."""
        return [p for p in self._principles.values() if situation.lower() in p.trigger.lower()]

    def save(self) -> None:
        """Persist all principles to the JSON file."""
        data = {pid: p.to_dict() for pid, p in self._principles.items()}
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """Load principles from the JSON file if it exists."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._principles = {pid: Principle.from_dict(d) for pid, d in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self._principles = {}
