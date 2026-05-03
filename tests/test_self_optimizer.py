import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from self_optimizer import SelfOptimizer, ParameterSet, OptimizationRecord


class TestParameterSet(unittest.TestCase):
    def test_create_params(self):
        ps = ParameterSet({"complexity_threshold": 0.7, "retrieval_weight": 0.5})
        self.assertEqual(ps.get("complexity_threshold"), 0.7)

    def test_update_param(self):
        ps = ParameterSet({"threshold": 0.5})
        ps.set("threshold", 0.6)
        self.assertEqual(ps.get("threshold"), 0.6)

    def test_get_missing_returns_none(self):
        ps = ParameterSet({})
        self.assertIsNone(ps.get("nonexistent"))


class TestSelfOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = SelfOptimizer()

    def test_register_parameter(self):
        self.optimizer.register_parameter("complexity_threshold", 0.7, 0.0, 1.0, 0.1)
        params = self.optimizer.get_current_params()
        self.assertEqual(params.get("complexity_threshold"), 0.7)

    def test_evaluate_and_adjust(self):
        self.optimizer.register_parameter("threshold", 0.5, 0.0, 1.0, 0.1)
        record = self.optimizer.evaluate("threshold", performance_score=0.2, direction="maximize")
        self.assertIsNotNone(record)
        self.assertNotEqual(record.old_value, record.new_value)

    def test_no_adjustment_when_performing_well(self):
        self.optimizer.register_parameter("threshold", 0.5, 0.0, 1.0, 0.1)
        record = self.optimizer.evaluate("threshold", performance_score=0.9, direction="maximize")
        self.assertIsNone(record)

    def test_adjustment_respects_bounds(self):
        self.optimizer.register_parameter("threshold", 0.95, 0.0, 1.0, 0.1)
        record = self.optimizer.evaluate("threshold", performance_score=0.1, direction="maximize")
        self.assertLessEqual(record.new_value, 1.0)

    def test_optimization_history(self):
        self.optimizer.register_parameter("threshold", 0.5, 0.0, 1.0, 0.1)
        self.optimizer.evaluate("threshold", 0.2, "maximize")
        self.optimizer.evaluate("threshold", 0.4, "maximize")
        history = self.optimizer.get_history()
        self.assertEqual(len(history), 2)

    def test_suggest_parameters(self):
        self.optimizer.register_parameter("x", 0.5, 0.0, 1.0, 0.1)
        self.optimizer.evaluate("x", 0.3, "maximize")
        suggestion = self.optimizer.suggest("x")
        self.assertIsNotNone(suggestion)


if __name__ == "__main__":
    unittest.main()
