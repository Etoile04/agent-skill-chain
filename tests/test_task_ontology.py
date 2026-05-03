import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from task_ontology import TaskType, TaskOntology


class TestTaskType(unittest.TestCase):
    def test_create_task_type(self):
        tt = TaskType(
            type_id="code_generation",
            category="development",
            keywords=["code", "implement", "write function"],
            required_capabilities=["code_generation"],
            typical_complexity="medium"
        )
        self.assertEqual(tt.type_id, "code_generation")
        self.assertEqual(tt.category, "development")

    def test_match_keywords(self):
        tt = TaskType("testing", "quality", ["test", "verify", "assert"], ["testing"], "low")
        self.assertTrue(tt.matches("write a test for this function"))
        self.assertFalse(tt.matches("deploy to production"))


class TestTaskOntology(unittest.TestCase):
    def setUp(self):
        self.ontology = TaskOntology()
        self.ontology.register(TaskType(
            "code_generation", "development",
            ["code", "implement", "write function"],
            ["code_generation"], "medium"
        ))
        self.ontology.register(TaskType(
            "testing", "quality",
            ["test", "verify", "assert", "validate"],
            ["testing"], "low"
        ))
        self.ontology.register(TaskType(
            "debugging", "development",
            ["debug", "fix bug", "trace error", "investigate failure"],
            ["debugging"], "high"
        ))
        self.ontology.register(TaskType(
            "documentation", "communication",
            ["document", "readme", "doc", "explain"],
            ["code_generation"], "low"
        ))

    def test_classify_task(self):
        result = self.ontology.classify("write a function to parse JSON")
        self.assertIsNotNone(result)
        self.assertEqual(result.type_id, "code_generation")

    def test_classify_returns_best_match(self):
        result = self.ontology.classify("fix the bug in the test")
        self.assertIsNotNone(result)

    def test_classify_unknown_returns_none(self):
        result = self.ontology.classify("order pizza for the team")
        self.assertIsNone(result)

    def test_find_similar_types(self):
        similar = self.ontology.find_similar("code_generation")
        self.assertGreater(len(similar), 0)
        ids = [s.type_id for s in similar]
        self.assertIn("debugging", ids)

    def test_get_required_capabilities(self):
        caps = self.ontology.get_required_capabilities("code_generation")
        self.assertIn("code_generation", caps)

    def test_list_by_category(self):
        dev_tasks = self.ontology.list_by_category("development")
        self.assertEqual(len(dev_tasks), 2)

    def test_persistence(self):
        import tempfile
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "ontology.json")
            o1 = TaskOntology()
            o1.register(TaskType("t1", "cat1", ["kw1"], ["cap1"], "low"))
            o1.save(path)
            o2 = TaskOntology()
            o2.load(path)
            result = o2.classify("kw1 related task")
            self.assertIsNotNone(result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
