"""
Task Ontology — task type classification, similarity computation, and capability mapping.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TaskType:
    """A single task type in the ontology."""

    type_id: str
    category: str
    keywords: List[str]
    required_capabilities: List[str]
    typical_complexity: str  # "low" | "medium" | "high"

    @staticmethod
    def _keyword_matches(keyword: str, text_lower: str) -> bool:
        """A keyword matches if all its constituent words appear in *text*."""
        words = keyword.lower().split()
        return all(w in text_lower for w in words)

    def matches(self, text: str) -> bool:
        """Return True if any keyword appears in *text* (case-insensitive)."""
        lower = text.lower()
        return any(self._keyword_matches(kw, lower) for kw in self.keywords)

    def match_score(self, text: str) -> float:
        """Fraction of keywords that appear in *text* (case-insensitive)."""
        if not self.keywords:
            return 0.0
        lower = text.lower()
        hit = sum(1 for kw in self.keywords if self._keyword_matches(kw, lower))
        return hit / len(self.keywords)

    def to_dict(self) -> dict:
        return {
            "type_id": self.type_id,
            "category": self.category,
            "keywords": self.keywords,
            "required_capabilities": self.required_capabilities,
            "typical_complexity": self.typical_complexity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskType":
        return cls(
            type_id=d["type_id"],
            category=d["category"],
            keywords=d["keywords"],
            required_capabilities=d["required_capabilities"],
            typical_complexity=d["typical_complexity"],
        )


class TaskOntology:
    """Registry of task types with classification and similarity."""

    def __init__(self) -> None:
        self._types: Dict[str, TaskType] = {}

    # -- mutators --

    def register(self, tt: TaskType) -> None:
        self._types[tt.type_id] = tt

    # -- queries --

    def classify(self, text: str) -> Optional[TaskType]:
        """Return the best-matching TaskType, or None if no keyword matches."""
        best: Optional[TaskType] = None
        best_score = 0.0
        for tt in self._types.values():
            score = tt.match_score(text)
            if score > best_score:
                best_score = score
                best = tt
        # Require at least one keyword hit (score > 0)
        return best if best_score > 0 else None

    def find_similar(self, type_id: str) -> List[TaskType]:
        """Return task types in the same category but with a different type_id."""
        target = self._types.get(type_id)
        if target is None:
            return []
        return [
            tt for tt in self._types.values()
            if tt.category == target.category and tt.type_id != type_id
        ]

    def get_required_capabilities(self, type_id: str) -> List[str]:
        tt = self._types.get(type_id)
        return list(tt.required_capabilities) if tt else []

    def list_by_category(self, category: str) -> List[TaskType]:
        return [tt for tt in self._types.values() if tt.category == category]

    # -- persistence --

    def save(self, path: str) -> None:
        data = [tt.to_dict() for tt in self._types.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._types.clear()
        for item in data:
            tt = TaskType.from_dict(item)
            self._types[tt.type_id] = tt
