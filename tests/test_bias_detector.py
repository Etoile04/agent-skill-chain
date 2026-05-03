import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from bias_detector import BiasPattern, BiasDetector, DetectionResult


class TestBiasPattern(unittest.TestCase):
    def test_create_bias_pattern(self):
        bp = BiasPattern(
            pattern_id="BIAS-001",
            name="Confirmation Bias",
            description="Agent seeks only confirming evidence",
            indicators=["ignores failing tests", "only checks positive results"],
            severity="high"
        )
        self.assertEqual(bp.pattern_id, "BIAS-001")
        self.assertEqual(bp.severity, "high")

    def test_bias_pattern_indicators(self):
        bp = BiasPattern("BIAS-002", "Test", "d", ["indicator1", "indicator2"], "medium")
        self.assertEqual(len(bp.indicators), 2)


class TestBiasDetector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = BiasDetector(os.path.join(self.tmpdir, "biases.json"))
        self.detector.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Agent claims completion without running tests",
            ["claims done without test output", "says 'should work'"],
            "high"
        ))
        self.detector.register(BiasPattern(
            "BIAS-002", "Scope Creep",
            "Agent adds features beyond the spec",
            ["implements unrequested features", "adds nice-to-haves"],
            "medium"
        ))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detect_matching_pattern(self):
        result = self.detector.detect("I'm done, it should work fine now")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-001")

    def test_detect_scope_creep(self):
        result = self.detector.detect("I also added a caching layer for nice-to-haves")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-002")

    def test_no_match_returns_none(self):
        result = self.detector.detect("All 34 tests pass, 0 failures confirmed")
        self.assertIsNone(result)

    def test_detection_result_has_severity(self):
        result = self.detector.detect("claims done without test output")
        self.assertEqual(result.severity, "high")

    def test_batch_detect(self):
        texts = [
            "should work now",
            "all tests pass",
            "implements unrequested features for caching"
        ]
        results = self.detector.batch_detect(texts)
        self.assertEqual(len(results), 2)

    def test_register_new_pattern(self):
        self.detector.register(BiasPattern(
            "BIAS-003", "Test", "d", ["new indicator pattern"], "low"
        ))
        result = self.detector.detect("I see new indicator pattern here")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-003")

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "biases.json")
        d1 = BiasDetector(path)
        d1.register(BiasPattern("B1", "T", "d", ["p1"], "low"))
        d1.save()
        d2 = BiasDetector(path)
        result = d2.detect("p1 found")
        self.assertIsNotNone(result)

    def test_get_all_patterns(self):
        patterns = self.detector.list_patterns()
        self.assertEqual(len(patterns), 2)

    def test_detection_confidence(self):
        result = self.detector.detect("claims done without test output, says 'should work'")
        self.assertIsNotNone(result)
        self.assertGreater(result.confidence, 0.0)


if __name__ == '__main__':
    unittest.main()
