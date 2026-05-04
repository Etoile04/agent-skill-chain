"""Cross-Scene Transfer: transfer learned principles across similar task types."""

from __future__ import annotations

from typing import List
from dataclasses import dataclass, field

from task_ontology import TaskOntology
from principle_store import PrincipleStore


@dataclass
class TransferResult:
    principle_id: str
    source_type: str
    target_type: str
    adapted_trigger: str
    original_trigger: str
    confidence: float
    principles_transferred: int = 1
    adaptations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "principle_id": self.principle_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "adapted_trigger": self.adapted_trigger,
            "original_trigger": self.original_trigger,
            "confidence": self.confidence,
        }


class CrossSceneTransfer:
    """Transfer effective principles from one task type to another within the same category."""

    def __init__(self, ontology: TaskOntology, principle_store: PrincipleStore) -> None:
        self._ontology = ontology
        self._principles = principle_store

    def find_transferable(
        self, target_type: str, effectiveness_threshold: float = 0.3
    ) -> List[TransferResult]:
        """Find principles from similar task types that can be transferred to *target_type*."""
        target_tt = self._ontology._types.get(target_type)
        if not target_tt:
            return []

        similar = self._ontology.find_similar(target_type)
        similar_ids = [s.type_id for s in similar]

        results: List[TransferResult] = []
        for p in self._principles.list_all():
            # Skip principles with no track record or low effectiveness
            if p.times_applied < 1 or p.effectiveness() < effectiveness_threshold:
                continue

            # Principle must be tagged with at least one similar task type
            source_tag = None
            for tag in p.tags:
                if tag in similar_ids:
                    source_tag = tag
                    break
            if source_tag is None:
                continue

            # Adapt trigger: replace source type references with target type
            adapted_trigger = p.trigger.replace(source_tag, target_type)
            confidence = p.effectiveness() * 0.8

            results.append(
                TransferResult(
                    principle_id=p.principle_id,
                    source_type=source_tag,
                    target_type=target_type,
                    adapted_trigger=adapted_trigger,
                    original_trigger=p.trigger,
                    confidence=confidence,
                    adaptations=[
                        f"adapted trigger from '{source_tag}' to '{target_type}'"
                    ],
                )
            )
        return results
