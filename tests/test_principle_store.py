import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from principle_store import Principle, PrincipleStore


class TestPrinciple(unittest.TestCase):
    def test_create_principle(self):
        p = Principle(
            principle_id="P-001",
            title="Always verify before claiming completion",
            description="Run verification commands before any success claim",
            source="reflection",
            trigger="about to claim task is complete",
            action="run test suite, read output, confirm 0 failures",
            tags=["verification", "discipline"]
        )
        self.assertEqual(p.principle_id, "P-001")
        self.assertEqual(len(p.tags), 2)

    def test_principle_has_effectiveness_tracking(self):
        p = Principle("P-002", "Test", "desc", "error", "trigger", "action", [])
        self.assertEqual(p.times_applied, 0)
        self.assertEqual(p.times_prevented_error, 0)

    def test_record_application(self):
        p = Principle("P-003", "Test", "desc", "error", "trigger", "action", [])
        p.record_application(prevented_error=True)
        self.assertEqual(p.times_applied, 1)
        self.assertEqual(p.times_prevented_error, 1)
        self.assertGreater(p.effectiveness(), 0.0)

    def test_effectiveness_with_no_applications(self):
        p = Principle("P-004", "Test", "desc", "error", "trigger", "action", [])
        self.assertEqual(p.effectiveness(), 0.0)


class TestPrincipleStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = PrincipleStore(os.path.join(self.tmpdir, "principles.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_principle(self):
        p = Principle("P-001", "Verify first", "desc", "reflection", "t", "a", ["test"])
        self.store.add(p)
        result = self.store.get("P-001")
        self.assertEqual(result.title, "Verify first")

    def test_list_all_principles(self):
        for i in range(3):
            p = Principle(f"P-{i}", f"T{i}", "d", "reflection", "t", "a", [])
            self.store.add(p)
        all_p = self.store.list_all()
        self.assertEqual(len(all_p), 3)

    def test_search_by_tag(self):
        self.store.add(Principle("P-1", "T1", "d", "r", "t", "a", ["verification"]))
        self.store.add(Principle("P-2", "T2", "d", "r", "t", "a", ["debugging"]))
        self.store.add(Principle("P-3", "T3", "d", "r", "t", "a", ["verification", "debugging"]))
        results = self.store.search_by_tag("verification")
        self.assertEqual(len(results), 2)

    def test_search_by_trigger(self):
        self.store.add(Principle("P-1", "T1", "d", "r", "about to commit", "a", []))
        self.store.add(Principle("P-2", "T2", "d", "r", "test fails", "a", []))
        results = self.store.search_by_trigger("commit")
        self.assertEqual(len(results), 1)

    def test_get_most_effective(self):
        p1 = Principle("P-1", "T1", "d", "r", "t", "a", [])
        p1.record_application(True)
        p1.record_application(True)
        p2 = Principle("P-2", "T2", "d", "r", "t", "a", [])
        p2.record_application(True)
        p2.record_application(False)
        self.store.add(p1)
        self.store.add(p2)
        best = self.store.get_most_effective()
        self.assertEqual(best.principle_id, "P-1")

    def test_update_principle(self):
        p = Principle("P-1", "Original", "d", "r", "t", "a", [])
        self.store.add(p)
        updated = Principle("P-1", "Updated", "new desc", "r", "t", "a", ["new_tag"])
        self.store.add(updated)
        result = self.store.get("P-1")
        self.assertEqual(result.title, "Updated")

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "principles.json")
        s1 = PrincipleStore(path)
        s1.add(Principle("P-1", "T", "d", "r", "t", "a", []))
        s1.save()
        s2 = PrincipleStore(path)
        result = s2.get("P-1")
        self.assertIsNotNone(result)

    def test_get_principles_for_situation(self):
        self.store.add(Principle("P-1", "Verify", "d", "r", "about to commit code", "run tests", []))
        self.store.add(Principle("P-2", "Debug", "d", "r", "test failure detected", "trace root cause", []))
        results = self.store.get_for_situation("commit")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].principle_id, "P-1")
