"""Learning Loop: organization-level learning cycle orchestration.

Coordinates experience collection, reflection, principle extraction,
knowledge distribution, and full cycle management across agents.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector
from reflection_loop import ReflectionLoop
from agent_registry import AgentRegistry
from task_ontology import TaskOntology


@dataclass
class LearningCycleResult:
    """Outcome of a single learning cycle."""

    cycle_id: str
    experiences_collected: int
    principles_updated: int
    knowledge_distributed: bool
    summary: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class DistributionResult:
    """Result of distributing knowledge to agents."""

    distributed_count: int


class LearningLoop:
    """Orchestrate the organization-level learning closed loop.

    Cycle: collect experiences → reflect on failures → extract/update
    principles → distribute effective principles to relevant agents.
    """

    _cycle_counter: int = 0

    def __init__(
        self,
        memory_store: MemoryStore,
        principle_store: PrincipleStore,
        bias_detector: BiasDetector,
        reflection: ReflectionLoop,
        registry: AgentRegistry,
        ontology: TaskOntology,
    ) -> None:
        self._memory = memory_store
        self._principles = principle_store
        self._bias = bias_detector
        self._reflection = reflection
        self._registry = registry
        self._ontology = ontology
        self._pending_experiences: List[Dict[str, Any]] = []
        self._cycle_history: List[LearningCycleResult] = []

    # ── Experience collection ─────────────────────────────────────────

    def collect_experience(
        self,
        agent_id: str,
        task_type: str,
        outcome: str,
        details: Dict[str, Any],
    ) -> str:
        """Store an experience in episodic memory.

        On failure outcomes, immediately triggers reflection to extract
        or update a behavioural principle.

        Returns the episodic memory entry ID.
        """
        ep_id = self._memory.episodic.store(
            event_type="experience",
            data={
                "agent_id": agent_id,
                "task_type": task_type,
                "outcome": outcome,
                "details": details,
            },
            tags=[task_type, outcome],
        )
        self._pending_experiences.append(
            {
                "ep_id": ep_id,
                "agent_id": agent_id,
                "task_type": task_type,
                "outcome": outcome,
                "details": details,
            }
        )

        if outcome == "failure":
            self._reflection.reflect_on_error(details)

        return ep_id

    # ── Knowledge distribution ────────────────────────────────────────

    def distribute_knowledge(self) -> DistributionResult:
        """Find effective principles and match them to capable agents.

        A principle is considered effective if its effectiveness score
        exceeds 0.3.  It is distributed to every agent whose
        capabilities overlap with the principle's tags (matched via the
        task ontology).
        """
        effective_principles = [
            p for p in self._principles.list_all() if p.effectiveness() > 0.3
        ]
        distributed_count = 0

        for principle in effective_principles:
            # Find task types that match this principle's tags
            relevant_task_types: set[str] = set()
            for tag in principle.tags:
                # Direct match or ontology-classified match
                if self._ontology.get_required_capabilities(tag):
                    relevant_task_types.add(tag)
                # Also check if any registered task type has this tag in
                # its required capabilities
                for tt_id in getattr(self._ontology, "_types", {}):
                    tt = self._ontology._types.get(tt_id)
                    if tt and tag in tt.required_capabilities:
                        relevant_task_types.add(tt_id)
                    if tt and tag == tt.type_id:
                        relevant_task_types.add(tt.type_id)

            # Find agents that can handle any of these task types
            for task_type in relevant_task_types:
                agents = self._registry.find_by_capability(task_type)
                distributed_count += len(agents)

        return DistributionResult(distributed_count=distributed_count)

    # ── Full cycle ────────────────────────────────────────────────────

    def run_cycle(self) -> LearningCycleResult:
        """Execute a complete learning cycle.

        1. Count collected experiences since last cycle.
        2. Count principles (reflecting any on-failure extractions).
        3. Distribute effective knowledge.
        4. Record the result.
        """
        LearningLoop._cycle_counter += 1
        cycle_id = f"cycle-{LearningLoop._cycle_counter:06d}"

        experiences_collected = len(self._pending_experiences)

        # Snapshot current principle count (some may have been added via
        # collect_experience's on-failure trigger already).
        principles_before = set(
            p.principle_id for p in self._principles.list_all()
        )

        # Run distribution step
        dist_result = self.distribute_knowledge()

        # Compute updated principles (new ones from this cycle)
        principles_after = set(
            p.principle_id for p in self._principles.list_all()
        )
        principles_updated = len(principles_after - principles_before)

        # Build summary
        summary = (
            f"Cycle {cycle_id}: collected {experiences_collected} experiences, "
            f"updated {principles_updated} principles, "
            f"distributed to {dist_result.distributed_count} agent(s)."
        )

        result = LearningCycleResult(
            cycle_id=cycle_id,
            experiences_collected=experiences_collected,
            principles_updated=principles_updated,
            knowledge_distributed=dist_result.distributed_count > 0,
            summary=summary,
        )

        self._cycle_history.append(result)
        # Clear pending experiences for next cycle
        self._pending_experiences.clear()

        return result

    # ── History ───────────────────────────────────────────────────────

    def get_cycle_history(self) -> List[LearningCycleResult]:
        """Return all completed cycle results."""
        return list(self._cycle_history)
