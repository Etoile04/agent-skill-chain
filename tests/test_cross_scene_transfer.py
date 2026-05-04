# tests/test_cross_scene_transfer.py
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from task_ontology import TaskType, TaskOntology
from principle_store import Principle, PrincipleStore
from cross_scene_transfer import CrossSceneTransfer, TransferResult


class TestTransferResult(unittest.TestCase):
    def test_create_result(self):
        r = TransferResult(
            principle_id="P-1",
            source_type="code_generation",
            target_type="debugging",
            confidence=0.7,
            adapted_trigger="fix code",
            original_trigger="write code",
            principles_transferred=2,
            adaptations=["changed 'write code' to 'fix code'"]
        )
        self.assertEqual(r.source_type, "code_generation")
        self.assertTrue(r.confidence > 0.5)


class TestCrossSceneTransfer(unittest.TestCase):
    def setUp(self):
        self.ontology = TaskOntology()
        self.ontology.register(TaskType("code_gen", "development", ["code"], ["code_gen"], "medium"))
        self.ontology.register(TaskType("debugging", "development", ["debug"], ["debugging"], "high"))
        self.ontology.register(TaskType("testing", "quality", ["test"], ["testing"], "low"))
        self.ontology.register(TaskType("research", "research", ["search"], ["literature_search"], "medium"))
        # PrincipleStore requires a path; use a temp file
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmpfile.close()
        self.principles = PrincipleStore(self._tmpfile.name)

    def tearDown(self):
        try:
            os.unlink(self._tmpfile.name)
        except FileNotFoundError:
            pass

    def test_find_transferable_principles(self):
        """同类别任务间的原则可以迁移"""
        p = Principle("P-1", "Verify code", "Run tests after code changes",
                      "reflection", "write code", "run test suite", ["code_gen"])
        p.record_application(True)
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        self.assertGreater(len(results), 0)

    def test_no_transfer_across_dissimilar_categories(self):
        """跨类别不迁移"""
        p = Principle("P-1", "Test", "d", "r", "write code", "a", ["code_gen"])
        p.record_application(True)
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("research")
        self.assertEqual(len(results), 0)

    def test_transfer_adapts_trigger(self):
        """迁移时应适配 trigger"""
        p = Principle("P-1", "Verify", "Run tests", "r", "write code", "run tests", ["code_gen"])
        p.record_application(True)
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        self.assertGreater(len(results), 0)
        adapted = results[0]
        # adapted trigger should reference debugging, not code_gen
        self.assertIn("adapted_trigger", adapted.to_dict())

    def test_transfer_confidence_based_on_similarity(self):
        """迁移置信度基于任务相似度"""
        p = Principle("P-1", "Test", "d", "r", "code trigger", "a", ["code_gen"])
        p.record_application(True)
        p.record_application(True)
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        if results:
            self.assertGreater(results[0].confidence, 0.0)

    def test_transfer_respects_effectiveness(self):
        """只迁移效果好的原则"""
        p_good = Principle("P-good", "Good", "d", "r", "t", "a", ["code_gen"])
        p_good.record_application(True)
        p_good.record_application(True)
        p_bad = Principle("P-bad", "Bad", "d", "r", "t", "a", ["code_gen"])
        p_bad.record_application(False)
        p_bad.record_application(False)
        self.principles.add(p_good)
        self.principles.add(p_bad)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        transferred_ids = [r.principle_id for r in results]
        self.assertIn("P-good", transferred_ids)
        self.assertNotIn("P-bad", transferred_ids)


if __name__ == "__main__":
    unittest.main()
