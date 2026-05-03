import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector
from reflection_loop import ReflectionLoop
from agent_registry import AgentCard, AgentRegistry
from task_ontology import TaskOntology, TaskType
from learning_loop import LearningLoop, LearningCycleResult


class TestLearningCycleResult(unittest.TestCase):
    def test_create_result(self):
        r = LearningCycleResult(
            cycle_id="cycle-001",
            experiences_collected=5,
            principles_updated=2,
            knowledge_distributed=True,
            summary="Test"
        )
        self.assertTrue(r.knowledge_distributed)


class TestLearningLoop(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory_store = MemoryStore()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        self.registry.register(AgentCard("agent-1", "Agent 1", ["code_gen"], ["py"], 2, 0.8))
        self.ontology = TaskOntology()
        self.ontology.register(TaskType("code_gen", "dev", ["code"], ["code_gen"], "med"))
        self.loop = LearningLoop(
            self.memory_store, self.principle_store, self.bias_detector,
            self.reflection, self.registry, self.ontology
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_collect_experience(self):
        result = self.loop.collect_experience(
            agent_id="agent-1",
            task_type="code_gen",
            outcome="success",
            details={"steps": 5, "tests_passed": 20}
        )
        self.assertIsNotNone(result)

    def test_collect_and_reflect_on_failure(self):
        self.loop.collect_experience("agent-1", "code_gen", "failure", {
            "error_type": "test_failure",
            "symptom": "tests not run",
            "root_cause": "skipped verification",
            "fix_applied": "run tests"
        })
        principles = self.principle_store.list_all()
        self.assertGreater(len(principles), 0)

    def test_distribute_knowledge(self):
        p = Principle("P-1", "Verify first", "desc", "reflection", "commit", "run tests", ["code_gen"])
        p.record_application(True)
        self.principle_store.add(p)
        result = self.loop.distribute_knowledge()
        self.assertTrue(result.distributed_count > 0)

    def test_full_cycle(self):
        self.loop.collect_experience("agent-1", "code_gen", "failure", {
            "error_type": "scope_creep", "symptom": "added extras",
            "root_cause": "no scope check", "fix_applied": "check spec"
        })
        self.loop.collect_experience("agent-1", "code_gen", "success", {
            "steps": 4, "tests_passed": 15
        })
        result = self.loop.run_cycle()
        self.assertIsNotNone(result)
        self.assertTrue(result.experiences_collected > 0)
        self.assertIsInstance(result, LearningCycleResult)

    def test_cycle_history(self):
        self.loop.collect_experience("agent-1", "code_gen", "success", {})
        self.loop.run_cycle()
        history = self.loop.get_cycle_history()
        self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
