"""Skill Trigger Engine: recommends which skill cards to load based on events and task types."""

import json
import os
from fnmatch import fnmatch
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TriggerRule:
    """A single trigger rule that matches events + task types to skill card paths."""
    rule_id: str
    event: str
    task_type_pattern: str
    skill_card_path: str
    priority: float = 0.5

    def matches(self, task_type: str) -> bool:
        """Check if a task_type matches this rule's pattern (supports glob wildcards)."""
        return fnmatch(task_type, self.task_type_pattern)


class SkillTriggerEngine:
    """Skill trigger engine: given an event and task type, recommends skill cards to load."""

    def __init__(self):
        self._rules: List[TriggerRule] = []

    def add_rule(self, rule: TriggerRule) -> None:
        """Register a trigger rule."""
        self._rules.append(rule)

    def load_rules(self, path: str) -> None:
        """Load trigger rules from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            self.add_rule(TriggerRule(**item))

    def find_matching(self, event: str, task_type: str) -> List[TriggerRule]:
        """Find all rules matching the given event and task type, sorted by priority (desc)."""
        matches = [r for r in self._rules if r.event == event and r.matches(task_type)]
        return sorted(matches, key=lambda r: r.priority, reverse=True)

    def get_recommended_skills(self, event: str, task_type: str) -> list:
        """Get recommended skill cards as dicts with path, priority, and rule_id."""
        rules = self.find_matching(event, task_type)
        return [
            {"path": r.skill_card_path, "priority": r.priority, "rule_id": r.rule_id}
            for r in rules
        ]
