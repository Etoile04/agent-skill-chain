"""Reflection Loop: error→principle extraction, bias detection, and reflection history."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector


@dataclass
class ReflectionResult:
    """Outcome of a single reflection cycle."""

    has_findings: bool
    new_principles: int = 0
    updated_principles: int = 0
    detected_biases: int = 0
    summary: str = ""
    timestamp: float = field(default_factory=time.time)


class ReflectionLoop:
    """Orchestrate reflection cycles that extract principles from errors and
    detect cognitive biases in agent behaviour text."""

    _counter: int = 0  # class-level auto-increment for principle IDs

    def __init__(self, principle_store: PrincipleStore, bias_detector: BiasDetector) -> None:
        self._store = principle_store
        self._bias = bias_detector
        self._history: List[ReflectionResult] = []

    # ── Public API ────────────────────────────────────────────────────

    def reflect_on_error(self, error_context: Dict[str, Any]) -> ReflectionResult:
        """Analyse an error context and extract/update a behavioural principle."""
        error_type = error_context.get("error_type", "unknown")
        symptom = error_context.get("symptom", "")
        root_cause = error_context.get("root_cause", "")
        fix_applied = error_context.get("fix_applied", "")

        # Check for an existing similar principle (same error_type tag and
        # root_cause substring in the description).
        existing = self._find_similar_principle(error_type, root_cause)

        if existing is not None:
            # Update the existing principle with the new fix.
            existing.title = f"Prevent {error_type}: {root_cause[:50]}"
            existing.trigger = f"encounter {error_type} or see symptom: {symptom[:60]}"
            existing.action = fix_applied or f"Investigate root cause: {root_cause}"
            existing.description = root_cause
            self._store.add(existing)
            result = ReflectionResult(
                has_findings=True,
                new_principles=0,
                updated_principles=1,
                summary=f"Updated existing principle {existing.principle_id}",
            )
        else:
            # Create a new principle.
            ReflectionLoop._counter += 1
            pid = f"P-AUTO-{ReflectionLoop._counter:04d}"
            principle = Principle(
                principle_id=pid,
                title=f"Prevent {error_type}: {root_cause[:50]}",
                description=root_cause,
                source="reflection",
                trigger=f"encounter {error_type} or see symptom: {symptom[:60]}",
                action=fix_applied or f"Investigate root cause: {root_cause}",
                tags=[error_type, "auto-generated"],
            )
            self._store.add(principle)
            result = ReflectionResult(
                has_findings=True,
                new_principles=1,
                updated_principles=0,
                summary=f"Created new principle {pid}",
            )

        self._history.append(result)
        return result

    def reflect_on_success(self, success_context: Dict[str, Any]) -> ReflectionResult:
        """Record a successful outcome. Typically produces no new principles."""
        result = ReflectionResult(
            has_findings=False,
            new_principles=0,
            updated_principles=0,
            detected_biases=0,
            summary="Success recorded; no new principles needed.",
        )
        self._history.append(result)
        return result

    def reflect_on_behavior(self, text: str) -> ReflectionResult:
        """Detect cognitive biases in the given text."""
        detection = self._bias.detect(text)
        if detection is not None:
            result = ReflectionResult(
                has_findings=True,
                new_principles=0,
                updated_principles=0,
                detected_biases=1,
                summary=f"Detected bias: {detection.pattern_name} "
                f"(severity={detection.severity}, "
                f"confidence={detection.confidence:.2f})",
            )
        else:
            result = ReflectionResult(
                has_findings=False,
                new_principles=0,
                updated_principles=0,
                detected_biases=0,
                summary="No bias detected.",
            )
        self._history.append(result)
        return result

    def get_history(self) -> List[ReflectionResult]:
        """Return all reflection results recorded so far."""
        return list(self._history)

    # ── Private helpers ───────────────────────────────────────────────

    def _find_similar_principle(
        self, error_type: str, root_cause: str
    ) -> Optional[Principle]:
        """Find a principle whose tags include *error_type* and whose
        description contains a substring of *root_cause*."""
        for p in self._store.list_all():
            if error_type in p.tags and root_cause in p.description:
                return p
        return None
