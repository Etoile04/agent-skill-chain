import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop, ReflectionResult


class TestReflectionResult(unittest.TestCase):
    def test_create_result(self):
        result = ReflectionResult(
            has_findings=True,
            new_principles=1,
            updated_principles=0,
            detected_biases=0,
            summary="Found 1 new principle"
        )
        self.assertTrue(result.has_findings)
        self.assertEqual(result.new_principles, 1)


class TestReflectionLoop(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "principles.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "biases.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reflect_on_error_generates_principle(self):
        error_context = {
            "error_type": "test_failure",
            "symptom": "claimed tests pass without running them",
            "root_cause": "assumed success from code review alone",
            "fix_applied": "added mandatory test run step"
        }
        result = self.reflection.reflect_on_error(error_context)
        self.assertTrue(result.has_findings)
        self.assertGreater(result.new_principles, 0)
        principles = self.principle_store.list_all()
        self.assertGreater(len(principles), 0)

    def test_reflect_on_success_no_new_principles(self):
        success_context = {
            "task_type": "code_generation",
            "steps_completed": 5,
            "tests_passed": 20,
            "tests_failed": 0
        }
        result = self.reflection.reflect_on_success(success_context)
        self.assertIsInstance(result, ReflectionResult)

    def test_reflect_on_text_detects_bias(self):
        self.bias_detector.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Claims done without evidence",
            ["should work", "looks good enough"],
            "high"
        ))
        result = self.reflection.reflect_on_behavior("The code should work fine now")
        self.assertTrue(result.has_findings)
        self.assertGreater(result.detected_biases, 0)

    def test_reflection_generates_actionable_principle(self):
        error_context = {
            "error_type": "integration_failure",
            "symptom": "modules don't work together",
            "root_cause": "no integration test between modules",
            "fix_applied": "added integration test"
        }
        self.reflection.reflect_on_error(error_context)
        principles = self.principle_store.list_all()
        for p in principles:
            self.assertTrue(len(p.trigger) > 0)
            self.assertTrue(len(p.action) > 0)

    def test_repeated_error_updates_existing_principle(self):
        ctx = {
            "error_type": "test_failure",
            "symptom": "same symptom",
            "root_cause": "same root cause",
            "fix_applied": "same fix"
        }
        r1 = self.reflection.reflect_on_error(ctx)
        r2 = self.reflection.reflect_on_error(ctx)
        principles = self.principle_store.list_all()
        self.assertEqual(len(principles), r1.new_principles)

    def test_reflection_history(self):
        self.reflection.reflect_on_error({
            "error_type": "test", "symptom": "s", "root_cause": "r", "fix_applied": "f"
        })
        history = self.reflection.get_history()
        self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
