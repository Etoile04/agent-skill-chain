# tests/test_budget_tracker.py
import sys
sys.path.insert(0, "scripts")

import unittest, tempfile, os
from budget_tracker import BudgetTracker

class TestBudgetTracker(unittest.TestCase):
    def test_track_usage(self):
        tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0)
        tracker.record(tokens=5000, cost_usd=0.05)
        self.assertEqual(tracker.total_tokens, 5000)
        self.assertAlmostEqual(tracker.total_cost_usd, 0.05)

    def test_budget_remaining(self):
        tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0)
        tracker.record(tokens=30000, cost_usd=0.3)
        self.assertEqual(tracker.tokens_remaining(), 70000)
        self.assertAlmostEqual(tracker.cost_remaining_usd(), 0.7)

    def test_over_budget(self):
        tracker = BudgetTracker(tokens_budget=10000, cost_budget_usd=0.1)
        tracker.record(tokens=12000, cost_usd=0.12)
        self.assertTrue(tracker.is_over_budget())

    def test_usage_pct(self):
        tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0)
        tracker.record(tokens=25000, cost_usd=0.25)
        self.assertAlmostEqual(tracker.usage_pct_tokens(), 25.0)
        self.assertAlmostEqual(tracker.usage_pct_cost(), 25.0)

    def test_threshold_alert(self):
        tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0,
                                alert_threshold_pct=80)
        tracker.record(tokens=85000, cost_usd=0.85)
        alerts = tracker.check_alerts()
        self.assertTrue(any("80%" in a for a in alerts))

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "budget.json")
            tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0, path=path)
            tracker.record(tokens=5000, cost_usd=0.05)
            tracker.save()
            tracker2 = BudgetTracker(path=path)
            self.assertEqual(tracker2.total_tokens, 5000)

    def test_per_task_tracking(self):
        tracker = BudgetTracker(tokens_budget=100000, cost_budget_usd=1.0)
        tracker.record(tokens=1000, cost_usd=0.01, task_id="T-001")
        tracker.record(tokens=2000, cost_usd=0.02, task_id="T-002")
        tracker.record(tokens=500, cost_usd=0.005, task_id="T-001")
        self.assertEqual(tracker.task_tokens("T-001"), 1500)

if __name__ == "__main__":
    unittest.main()
