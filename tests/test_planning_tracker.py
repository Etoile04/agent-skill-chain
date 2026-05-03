# tests/test_planning_tracker.py
import sys
sys.path.insert(0, "scripts")

import unittest
from planning_tracker import PlanningQualityTracker, QualityRecord


class TestQualityRecord(unittest.TestCase):
    def test_create_record(self):
        rec = QualityRecord(
            plan_id="P-001", task_type="doc_converter",
            total_steps=4, steps_completed=4, steps_failed=0,
            fallbacks_triggered=0, total_time_ms=300000,
            tests_total=10, tests_passed=10
        )
        self.assertEqual(rec.plan_id, "P-001")
        self.assertTrue(rec.is_success())

    def test_success_rate(self):
        rec = QualityRecord(
            plan_id="P-002", task_type="api_test",
            total_steps=6, steps_completed=5, steps_failed=1,
            fallbacks_triggered=1, total_time_ms=600000
        )
        self.assertAlmostEqual(rec.success_rate(), 5 / 6)

    def test_partial_failure(self):
        rec = QualityRecord(
            plan_id="P-003", task_type="validation",
            total_steps=4, steps_completed=3, steps_failed=1,
            fallbacks_triggered=0, total_time_ms=400000
        )
        self.assertFalse(rec.is_success())


class TestPlanningQualityTracker(unittest.TestCase):
    def _make_tracker_with_data(self):
        tracker = PlanningQualityTracker()
        tracker.record(QualityRecord("P-001", "doc_converter", 4, 4, 0, 0, 300000, 10, 10))
        tracker.record(QualityRecord("P-002", "api_test", 6, 5, 1, 1, 600000, 139, 139))
        tracker.record(QualityRecord("P-003", "validation", 4, 4, 0, 0, 400000, 142, 142))
        tracker.record(QualityRecord("P-004", "api_test", 5, 3, 2, 2, 500000, 20, 18))
        return tracker

    def test_overall_success_rate(self):
        tracker = self._make_tracker_with_data()
        self.assertAlmostEqual(tracker.overall_success_rate(), 0.5)  # 2/4 plans fully successful

    def test_average_steps_success_rate(self):
        tracker = self._make_tracker_with_data()
        # Total steps: 4+6+4+5=19, completed: 4+5+4+3=16
        self.assertAlmostEqual(tracker.avg_step_success_rate(), 16 / 19)

    def test_stats_by_task_type(self):
        tracker = self._make_tracker_with_data()
        stats = tracker.stats_by_task_type("api_test")
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["avg_steps"], 5.5)  # (6+5)/2

    def test_fallback_rate(self):
        tracker = self._make_tracker_with_data()
        self.assertEqual(tracker.fallback_rate(), 0.5)  # 2/4 plans had fallbacks

    def test_persistence(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            tracker = PlanningQualityTracker(path)
            tracker.record(QualityRecord("P-001", "test", 1, 1, 0, 0, 100))
            tracker.save()
            tracker2 = PlanningQualityTracker(path)
            self.assertEqual(len(tracker2._records), 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
