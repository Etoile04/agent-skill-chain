import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from evaluation_framework import EvaluationFramework, MetricRecord


class TestMetricRecord(unittest.TestCase):
    def test_create_metric(self):
        m = MetricRecord("stability", "inner", 0.95, 0.99, "ratio")
        self.assertEqual(m.metric_name, "stability")
        self.assertTrue(m.passes_target())

    def test_metric_fails_target(self):
        m = MetricRecord("error_rate", "inner", 0.15, 0.05, "ratio")
        self.assertFalse(m.passes_target())


class TestEvaluationFramework(unittest.TestCase):
    def setUp(self):
        self.framework = EvaluationFramework()

    def test_register_metric(self):
        self.framework.register_metric("stability", "inner", 0.99, "ratio", "Success rate")
        metrics = self.framework.list_metrics()
        self.assertEqual(len(metrics), 1)

    def test_record_measurement(self):
        self.framework.register_metric("stability", "inner", 0.99, "ratio")
        self.framework.record("stability", 0.95)
        records = self.framework.get_records("stability")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].value, 0.95)

    def test_compute_layer_score(self):
        self.framework.register_metric("stability", "inner", 0.99, "ratio")
        self.framework.register_metric("learning_efficiency", "inner", 0.7, "ratio")
        self.framework.record("stability", 0.95)
        self.framework.record("learning_efficiency", 0.8)
        score = self.framework.compute_layer_score("inner")
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_compute_overall_score(self):
        for name, layer in [("s1", "inner"), ("s2", "middle"), ("s3", "outer")]:
            self.framework.register_metric(name, layer, 0.8, "ratio")
            self.framework.record(name, 0.9)
        score = self.framework.compute_overall_score()
        self.assertGreater(score, 0.0)

    def test_get_failing_metrics(self):
        self.framework.register_metric("good", "inner", 0.8, "ratio")
        self.framework.register_metric("bad", "inner", 0.8, "ratio")
        self.framework.record("good", 0.9)
        self.framework.record("bad", 0.5)
        failing = self.framework.get_failing_metrics()
        self.assertEqual(len(failing), 1)
        self.assertEqual(failing[0].metric_name, "bad")

    def test_layer_metrics_summary(self):
        self.framework.register_metric("m1", "inner", 0.8, "ratio")
        self.framework.register_metric("m2", "middle", 0.7, "ratio")
        self.framework.record("m1", 0.9)
        self.framework.record("m2", 0.75)
        summary = self.framework.get_layer_summary()
        self.assertIn("inner", summary)
        self.assertIn("middle", summary)


if __name__ == "__main__":
    unittest.main()
