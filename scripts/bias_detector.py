"""Bias Detector — detects cognitive bias patterns in agent output text."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BiasPattern:
    pattern_id: str
    name: str
    description: str
    indicators: List[str]
    severity: str  # low | medium | high
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "indicators": self.indicators,
            "severity": self.severity,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BiasPattern":
        return cls(
            pattern_id=d["pattern_id"],
            name=d["name"],
            description=d["description"],
            indicators=d["indicators"],
            severity=d["severity"],
            created_at=d.get("created_at", time.time()),
        )


@dataclass
class DetectionResult:
    pattern_id: str
    pattern_name: str
    severity: str
    confidence: float
    matched_indicators: List[str]


class BiasDetector:
    """Detect known cognitive bias patterns in agent text output."""

    def __init__(self, store_path: Optional[str] = None):
        self._patterns: List[BiasPattern] = []
        self._store_path = store_path
        if store_path and os.path.isfile(store_path):
            self.load()

    # ── CRUD ──────────────────────────────────────────────────────────

    def register(self, pattern: BiasPattern) -> None:
        self._patterns.append(pattern)

    def list_patterns(self) -> List[BiasPattern]:
        return list(self._patterns)

    # ── Matching helpers ──────────────────────────────────────────────

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase and remove quote characters for forgiving matching."""
        return s.lower().replace("'", "").replace('"', "")

    @staticmethod
    def _indicator_matches(indicator: str, text_lower: str) -> bool:
        """Check if an indicator matches the text.

        Matching layers (first hit wins):
        1. Normalised indicator as a whole substring of text.
        2. Any keyword (>= 3 chars) from the indicator appears in the text
           as a whole word (word-boundary regex).
        """
        norm = BiasDetector._normalize(indicator)
        if norm in text_lower:
            return True

        # Whole-word keyword match — prevents e.g. "test" matching "tests"
        keywords = [w for w in norm.replace("-", " ").split() if len(w) >= 3]
        return any(
            re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
            for kw in keywords
        )

    # ── Detection ─────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[DetectionResult]:
        """Return the best-matching DetectionResult or None."""
        best: Optional[DetectionResult] = None
        text_lower = text.lower()

        for pattern in self._patterns:
            matched = [
                ind
                for ind in pattern.indicators
                if self._indicator_matches(ind, text_lower)
            ]
            if not matched:
                continue
            confidence = len(matched) / len(pattern.indicators)
            result = DetectionResult(
                pattern_id=pattern.pattern_id,
                pattern_name=pattern.name,
                severity=pattern.severity,
                confidence=confidence,
                matched_indicators=matched,
            )
            if best is None or result.confidence > best.confidence:
                best = result

        return best

    def batch_detect(self, texts: List[str]) -> List[DetectionResult]:
        """Return DetectionResult for every text that matches at least one pattern."""
        results: List[DetectionResult] = []
        for text in texts:
            r = self.detect(text)
            if r is not None:
                results.append(r)
        return results

    # ── Persistence ───────────────────────────────────────────────────

    def save(self) -> None:
        if not self._store_path:
            return
        data = [p.to_dict() for p in self._patterns]
        os.makedirs(os.path.dirname(self._store_path) or ".", exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if not self._store_path or not os.path.isfile(self._store_path):
            return
        with open(self._store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._patterns = [BiasPattern.from_dict(d) for d in data]
