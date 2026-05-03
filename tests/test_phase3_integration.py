"""Phase 3 Integration Tests: verify all outer-layer + inner-layer modules work together."""

import unittest
import tempfile
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter
from approval_gate import ApprovalGate, ApprovalStatus
from governance_versioner import GovernanceVersioner
from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover


class TestPhase3Integration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_outer_layer_workflow(self):
        """Register agents → route task → approve high-risk op → version config"""
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard(
            "code-agent", "Code Agent",
            ["code_generation", "debugging", "testing"], ["python"], 2, 0.9
        ))
        registry.register(AgentCard(
            "research-agent", "Research Agent",
            ["literature_search", "data_analysis"], ["materials"], 1, 0.8
        ))

        router = TaskRouter(registry)
        decision = router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")

        gate = ApprovalGate(os.path.join(self.tmpdir, "approvals.json"))
        req_id = gate.submit("deploy_to_production", "code-agent", "high", {})
        self.assertEqual(gate.get_request(req_id).status, ApprovalStatus.PENDING)
        gate.approve(req_id, approver="admin")
        self.assertEqual(gate.get_request(req_id).status, ApprovalStatus.APPROVED)

        versioner = GovernanceVersioner(os.path.join(self.tmpdir, "gov.json"))
        versioner.commit(
            {"agents": {"code-agent": {"max_budget": 10000}}},
            author="admin",
            description="Set budget"
        )
        self.assertIsNotNone(versioner.get_current())

    def test_full_inner_layer_workflow(self):
        """Error → reflection → principle → bias detection → self-improvement"""
        ps = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bd = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        rl = ReflectionLoop(ps, bd)
        improver = AutonomousImprover(ps, bd, rl)

        bd.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Claims done without evidence",
            ["should work", "looks fine"],
            "high"
        ))

        result = rl.reflect_on_error({
            "error_type": "test_failure",
            "symptom": "tests not run before commit",
            "root_cause": "no verification step",
            "fix_applied": "run full test suite before any commit"
        })
        self.assertTrue(result.has_findings)
        self.assertGreater(result.new_principles, 0)

        bias_result = rl.reflect_on_behavior("The code should work fine now")
        self.assertTrue(bias_result.has_findings)

        proposals = improver.run_improvement_cycle()
        self.assertIsInstance(proposals, list)

        principles = ps.get_for_situation("commit")
        self.assertGreater(len(principles), 0)

    def test_cross_layer_interaction(self):
        """Outer-layer routing + inner-layer reflection interaction"""
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard("a1", "A1", ["code_gen"], ["py"], 2, 0.9))
        router = TaskRouter(registry)

        ps = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bd = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        rl = ReflectionLoop(ps, bd)

        decision = router.route("code_gen")
        self.assertIsNotNone(decision)
        self.assertEqual(len(router.get_history()), 1)

    def test_all_phase3_modules_importable(self):
        """All Phase 3 modules can be imported"""
        from agent_registry import AgentCard, AgentRegistry
        from task_router import TaskRouter, RoutingDecision
        from approval_gate import ApprovalGate, ApprovalRequest, ApprovalStatus
        from governance_versioner import GovernanceVersioner, ConfigVersion
        from principle_store import Principle, PrincipleStore
        from bias_detector import BiasPattern, BiasDetector, DetectionResult
        from reflection_loop import ReflectionLoop, ReflectionResult
        from autonomous_improver import AutonomousImprover, ImprovementProposal
        self.assertTrue(True)

    def test_phase2_modules_still_work(self):
        """Phase 2 modules still function correctly"""
        from memory_layer import MemoryStore
        from skill_trigger import SkillTriggerEngine
        from planning_tracker import PlanningQualityTracker
        from task_roadmap import TaskRoadmap
        from budget_tracker import BudgetTracker

        store = MemoryStore()
        store.semantic.store("test", "value")
        self.assertEqual(store.semantic.retrieve("test"), "value")

        rm = TaskRoadmap("rm-1", "Test Roadmap")
        rm.add_milestone("M1", "Milestone 1")
        rm.add_task("M1", "T1", "Task 1")
        self.assertAlmostEqual(rm.progress_pct(), 0.0)
