import unittest
import json
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from agent_registry import AgentCard, AgentRegistry


class TestAgentCard(unittest.TestCase):
    def test_create_agent_card(self):
        card = AgentCard(
            agent_id="coding-a2a",
            name="Coding Agent",
            capabilities=["code_generation", "debugging", "testing"],
            specializations=["python", "javascript"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.assertEqual(card.agent_id, "coding-a2a")
        self.assertEqual(len(card.capabilities), 3)
        self.assertEqual(card.max_concurrent_tasks, 2)

    def test_agent_card_has_skill_coverage(self):
        card = AgentCard(
            agent_id="research-agent",
            name="Research Agent",
            capabilities=["literature_search", "data_analysis"],
            specializations=["materials_science"],
            max_concurrent_tasks=1,
            confidence_threshold=0.8
        )
        coverage = card.skill_coverage()
        self.assertIn("literature_search", coverage)
        self.assertIn("data_analysis", coverage)

    def test_agent_card_to_dict(self):
        card = AgentCard(
            agent_id="test-agent",
            name="Test",
            capabilities=["test"],
            specializations=[],
            max_concurrent_tasks=1,
            confidence_threshold=0.5
        )
        d = card.to_dict()
        self.assertEqual(d["agent_id"], "test-agent")
        self.assertIn("created_at", d)

    def test_can_handle_task_type(self):
        card = AgentCard(
            agent_id="code-agent",
            name="Code Agent",
            capabilities=["code_generation", "debugging"],
            specializations=["python"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.assertTrue(card.can_handle("code_generation"))
        self.assertFalse(card.can_handle("literature_search"))


class TestAgentRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_agent(self):
        card = AgentCard(
            agent_id="coding-a2a",
            name="Coding Agent",
            capabilities=["code_generation"],
            specializations=["python"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.registry.register(card)
        result = self.registry.get("coding-a2a")
        self.assertEqual(result.name, "Coding Agent")

    def test_list_all_agents(self):
        for i in range(3):
            card = AgentCard(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                capabilities=["test"],
                specializations=[],
                max_concurrent_tasks=1,
                confidence_threshold=0.5
            )
            self.registry.register(card)
        agents = self.registry.list_all()
        self.assertEqual(len(agents), 3)

    def test_find_by_capability(self):
        card1 = AgentCard("a1", "A1", ["code_generation"], ["python"], 2, 0.7)
        card2 = AgentCard("a2", "A2", ["literature_search"], ["materials"], 1, 0.8)
        self.registry.register(card1)
        self.registry.register(card2)
        results = self.registry.find_by_capability("code_generation")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, "a1")

    def test_find_best_for_task(self):
        card1 = AgentCard("a1", "A1", ["code_generation"], ["python"], 2, 0.7)
        card2 = AgentCard("a2", "A2", ["code_generation", "debugging"], ["python", "js"], 2, 0.9)
        self.registry.register(card1)
        self.registry.register(card2)
        best = self.registry.find_best_for_task("code_generation")
        self.assertEqual(best.agent_id, "a2")

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "agents.json")
        reg1 = AgentRegistry(path)
        card = AgentCard("persist-test", "PT", ["test"], [], 1, 0.5)
        reg1.register(card)
        reg1.save()
        reg2 = AgentRegistry(path)
        result = reg2.get("persist-test")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "PT")

    def test_update_agent(self):
        card = AgentCard("update-test", "Original", ["test"], [], 1, 0.5)
        self.registry.register(card)
        updated = AgentCard("update-test", "Updated", ["test", "new_cap"], [], 1, 0.5)
        self.registry.register(updated)
        result = self.registry.get("update-test")
        self.assertEqual(result.name, "Updated")
        self.assertEqual(len(result.capabilities), 2)

    def test_unregister_agent(self):
        card = AgentCard("remove-test", "RT", ["test"], [], 1, 0.5)
        self.registry.register(card)
        self.registry.unregister("remove-test")
        self.assertIsNone(self.registry.get("remove-test"))
