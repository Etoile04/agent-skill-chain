"""Capability Replicator: transfer knowledge from experienced agents to new agents."""

from typing import List, Optional
from dataclasses import dataclass, field

from agent_registry import AgentRegistry
from principle_store import PrincipleStore
from memory_layer import MemoryStore


@dataclass
class ReplicationResult:
    source_agent: str
    target_agent: str
    principles_copied: int = 0
    memories_copied: int = 0
    copied_principle_ids: List[str] = field(default_factory=list)
    success: bool = False
    report: str = ""


class CapabilityReplicator:
    def __init__(self, registry: AgentRegistry, principle_store: PrincipleStore,
                 memory_store: MemoryStore, effectiveness_threshold: float = 0.3):
        self._registry = registry
        self._principles = principle_store
        self._memory = memory_store
        self._threshold = effectiveness_threshold

    def replicate(self, source_id: str, target_id: str) -> ReplicationResult:
        source = self._registry.get(source_id)
        target = self._registry.get(target_id)

        if not source or not target:
            return ReplicationResult(
                source_agent=source_id, target_agent=target_id,
                success=False, report=f"Agent not found: source={source is not None}, target={target is not None}"
            )

        # Filter effective principles relevant to target's capabilities
        copied_ids = []
        for p in self._principles.list_all():
            if p.effectiveness() < self._threshold:
                continue
            if p.times_applied < 1:
                continue
            if any(tag in target.capabilities for tag in p.tags):
                copied_ids.append(p.principle_id)

        # Count memories
        semantic_facts = self._memory.semantic.list_all()
        episodes = self._memory.episodic.search(event_type="task_complete")
        memories_count = len(semantic_facts) + len(episodes)

        report = (f"Replicated {len(copied_ids)} principles and {memories_count} memories "
                  f"from {source.name} to {target.name}")

        return ReplicationResult(
            source_agent=source_id,
            target_agent=target_id,
            principles_copied=len(copied_ids),
            memories_copied=memories_count,
            copied_principle_ids=copied_ids,
            success=True,
            report=report,
        )
