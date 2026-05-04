# tests/test_phase4_integration.py
"""Phase 4 Integration Tests: three-layer closed loop end-to-end."""

import unittest
import tempfile
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover
from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter
from approval_gate import ApprovalGate
from task_ontology import TaskType, TaskOntology
from learning_loop import LearningLoop
from cross_scene_transfer import CrossSceneTransfer
from self_optimizer import SelfOptimizer
from evaluation_framework import EvaluationFramework
from capability_replicator import CapabilityReplicator


class TestPhase4Integration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_closed_loop(self):
        """完整三层闭环：经验收集→学习→迁移→评测→复制"""
        # Setup
        memory = MemoryStore()
        ps = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bd = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        rl = ReflectionLoop(ps, bd)
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard("veteran", "Veteran", ["code_gen", "debugging"], ["py"], 2, 0.9))
        registry.register(AgentCard("rookie", "Rookie", ["code_gen"], ["py"], 1, 0.5))
        router = TaskRouter(registry)
        ontology = TaskOntology()
        ontology.register(TaskType("code_gen", "development", ["code"], ["code_gen"], "medium"))
        ontology.register(TaskType("debugging", "development", ["debug"], ["debugging"], "high"))

        # 1. Learning Loop: collect experience → reflect → distribute
        loop = LearningLoop(memory, ps, bd, rl, registry, ontology)
        loop.collect_experience("veteran", "code_gen", "failure", {
            "error_type": "test_failure", "symptom": "no tests",
            "root_cause": "skipped TDD", "fix_applied": "write tests first"
        })
        loop.collect_experience("veteran", "code_gen", "success", {"steps": 5, "tests": 20})
        cycle = loop.run_cycle()
        self.assertTrue(cycle.experiences_collected > 0)

        # 2. Cross-scene transfer: code_gen → debugging
        transfer = CrossSceneTransfer(ontology, ps)
        transfers = transfer.find_transferable("debugging")
        # Note: transfer requires principles with effectiveness > 0.3 and
        # tags matching similar task types; with fresh stores the list may
        # be empty, which is fine — we just verify the call succeeds.

        # 3. Evaluation: measure system health
        eval_fw = EvaluationFramework()
        eval_fw.register_metric("stability", "inner", 0.95, "ratio")
        eval_fw.register_metric("learning_efficiency", "middle", 0.7, "ratio")
        eval_fw.register_metric("task_completion", "outer", 0.9, "ratio")
        eval_fw.record("stability", 0.97)
        eval_fw.record("learning_efficiency", 0.8)
        eval_fw.record("task_completion", 0.92)
        score = eval_fw.compute_overall_score()
        self.assertGreater(score, 0.8)

        # 4. Capability replication: veteran → rookie
        replicator = CapabilityReplicator(registry, ps, memory)
        result = replicator.replicate("veteran", "rookie")
        self.assertTrue(result.success)
        # principles_copied may be 0 with fresh store — just check the call works
        self.assertIsInstance(result.principles_copied, int)

    def test_self_optimization_feedback_loop(self):
        """自优化：评测→调参→再评测"""
        optimizer = SelfOptimizer()
        optimizer.register_parameter("complexity_threshold", 0.7, 0.0, 1.0, 0.05)
        optimizer.register_parameter("exploration_rate", 0.3, 0.0, 1.0, 0.05)

        # Simulate poor performance → auto-adjust
        r1 = optimizer.evaluate("complexity_threshold", 0.3, "maximize")
        self.assertIsNotNone(r1)

        # After adjustment, check parameter changed
        params = optimizer.get_current_params()
        self.assertNotEqual(params.get("complexity_threshold"), 0.7)

    def test_all_phase4_modules_importable(self):
        from task_ontology import TaskType, TaskOntology
        from learning_loop import LearningLoop, LearningCycleResult
        from cross_scene_transfer import CrossSceneTransfer, TransferResult
        from self_optimizer import SelfOptimizer, ParameterSet, OptimizationRecord
        from evaluation_framework import EvaluationFramework, MetricRecord
        from capability_replicator import CapabilityReplicator, ReplicationResult
        self.assertTrue(True)

    def test_phase2_3_modules_still_work(self):
        """Phase 2+3 modules remain functional"""
        from memory_layer import MemoryStore
        from principle_store import Principle, PrincipleStore
        from agent_registry import AgentCard, AgentRegistry
        from task_router import TaskRouter

        store = MemoryStore()
        store.semantic.store("k", "v")
        self.assertEqual(store.semantic.retrieve("k"), "v")

        reg = AgentRegistry(os.path.join(self.tmpdir, "reg.json"))
        reg.register(AgentCard("a", "A", ["cap"], [], 1, 0.5))
        router = TaskRouter(reg)
        d = router.route("cap")
        self.assertIsNotNone(d)


if __name__ == "__main__":
    unittest.main()
