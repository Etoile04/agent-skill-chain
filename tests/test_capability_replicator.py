# tests/test_capability_replicator.py
import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from agent_registry import AgentCard, AgentRegistry
from principle_store import Principle, PrincipleStore
from memory_layer import MemoryStore
from capability_replicator import CapabilityReplicator, ReplicationResult


class TestReplicationResult(unittest.TestCase):
    def test_create_result(self):
        r = ReplicationResult(
            source_agent="agent-1",
            target_agent="agent-2",
            principles_copied=5,
            memories_copied=10,
            success=True
        )
        self.assertTrue(r.success)
        self.assertEqual(r.principles_copied, 5)


class TestCapabilityReplicator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        self.principles = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.memory = MemoryStore()

        # Source agent with knowledge
        self.registry.register(AgentCard("veteran", "Veteran", ["code_gen", "debugging"], ["py"], 2, 0.9))
        # New agent to receive knowledge
        self.registry.register(AgentCard("rookie", "Rookie", ["code_gen"], ["py"], 1, 0.5))

        # Veteran has effective principles
        for i in range(5):
            p = Principle(f"P-{i}", f"Rule {i}", "desc", "reflection", f"trigger {i}", f"action {i}", ["code_gen"])
            p.record_application(True)
            self.principles.add(p)

        # Veteran has memories
        self.memory.semantic.store("project_style", "TDD")
        self.memory.semantic.store("test_framework", "pytest")
        self.memory.episodic.store("task_complete", {"task": "refactor"}, ["milestone"])

        self.replicator = CapabilityReplicator(self.registry, self.principles, self.memory)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_replicate_to_new_agent(self):
        """将 veteran 知识复制到 rookie"""
        result = self.replicator.replicate("veteran", "rookie")
        self.assertTrue(result.success)
        self.assertGreater(result.principles_copied, 0)
        self.assertGreater(result.memories_copied, 0)

    def test_only_effective_principles_copied(self):
        """只复制效果好的原则"""
        bad_p = Principle("P-bad", "Bad", "d", "r", "t", "a", ["code_gen"])
        bad_p.record_application(False)
        bad_p.record_application(False)
        self.principles.add(bad_p)

        result = self.replicator.replicate("veteran", "rookie")
        copied_ids = [p for p in result.copied_principle_ids]
        self.assertNotIn("P-bad", copied_ids)

    def test_replicate_nonexistent_agent_fails(self):
        result = self.replicator.replicate("ghost", "rookie")
        self.assertFalse(result.success)

    def test_replicate_checks_capability_overlap(self):
        """只复制与目标 Agent 能力相关的原则"""
        # Add a principle for debugging (rookie doesn't have debugging capability)
        p_debug = Principle("P-debug", "Debug rule", "d", "r", "debug trigger", "a", ["debugging"])
        p_debug.record_application(True)
        self.principles.add(p_debug)

        result = self.replicator.replicate("veteran", "rookie")
        copied_ids = result.copied_principle_ids
        self.assertNotIn("P-debug", copied_ids)  # rookie can't debug

    def test_replication_report(self):
        """复制结果应包含详细报告"""
        result = self.replicator.replicate("veteran", "rookie")
        self.assertTrue(len(result.report) > 0)
