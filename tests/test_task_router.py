import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter, RoutingDecision


class TestRoutingDecision(unittest.TestCase):
    def test_create_routing_decision(self):
        decision = RoutingDecision(
            task_type="code_generation",
            assigned_agent="coding-a2a",
            confidence=0.9,
            reason="Best capability match"
        )
        self.assertEqual(decision.task_type, "code_generation")
        self.assertEqual(decision.assigned_agent, "coding-a2a")

    def test_routing_decision_needs_approval_when_low_confidence(self):
        decision = RoutingDecision(
            task_type="unknown_task",
            assigned_agent="fallback-agent",
            confidence=0.3,
            reason="No good match"
        )
        self.assertTrue(decision.needs_approval())

    def test_routing_decision_no_approval_when_high_confidence(self):
        decision = RoutingDecision(
            task_type="code_generation",
            assigned_agent="code-agent",
            confidence=0.9,
            reason="Good match"
        )
        self.assertFalse(decision.needs_approval())


class TestTaskRouter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        self.registry.register(AgentCard(
            "code-agent", "Code Agent",
            ["code_generation", "debugging", "testing"], ["python"], 2, 0.9
        ))
        self.registry.register(AgentCard(
            "research-agent", "Research Agent",
            ["literature_search", "data_analysis"], ["materials"], 1, 0.8
        ))
        self.registry.register(AgentCard(
            "general-agent", "General Agent",
            ["code_generation", "literature_search", "testing"], ["python", "materials"], 3, 0.6
        ))
        self.router = TaskRouter(self.registry)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_route_to_specialist(self):
        decision = self.router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")

    def test_route_to_research_agent(self):
        decision = self.router.route("literature_search")
        self.assertEqual(decision.assigned_agent, "research-agent")

    def test_route_unknown_returns_none(self):
        decision = self.router.route("unknown_capability")
        self.assertIsNone(decision)

    def test_route_prefers_higher_confidence(self):
        decision = self.router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")
        self.assertGreater(decision.confidence, 0.5)

    def test_routing_history(self):
        self.router.route("code_generation")
        self.router.route("literature_search")
        history = self.router.get_history()
        self.assertEqual(len(history), 2)


if __name__ == '__main__':
    unittest.main()
