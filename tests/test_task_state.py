# tests/test_task_state.py
import unittest, tempfile, os, json, sys
sys.path.insert(0, "scripts")

from task_state import TaskStateManager

class TestTaskState(unittest.TestCase):
    def test_create_task(self):
        mgr = TaskStateManager()
        state = mgr.create("T-001", "Build memory system", roadmap_id="RM-001")
        self.assertEqual(state["task_id"], "T-001")
        self.assertEqual(state["status"], "pending")

    def test_transition_status(self):
        mgr = TaskStateManager()
        state = mgr.create("T-001", "Test task")
        mgr.transition("T-001", "in_progress")
        self.assertEqual(mgr.get("T-001")["status"], "in_progress")

    def test_invalid_transition(self):
        mgr = TaskStateManager()
        mgr.create("T-001", "Test task")
        with self.assertRaises(ValueError):
            mgr.transition("T-001", "completed")  # pending → completed not allowed

    def test_checkpoint(self):
        mgr = TaskStateManager()
        mgr.create("T-001", "Test task")
        mgr.transition("T-001", "in_progress")
        mgr.checkpoint("T-001", {
            "step_plan_path": "plans/test.json",
            "completed_steps": ["step-1", "step-2"],
            "resume_hint": "Continue from step-3"
        })
        state = mgr.get("T-001")
        self.assertEqual(len(state["checkpoint"]["completed_steps"]), 2)

    def test_resume_from_checkpoint(self):
        mgr = TaskStateManager()
        mgr.create("T-001", "Test task")
        mgr.transition("T-001", "in_progress")
        mgr.checkpoint("T-001", {"resume_hint": "Continue from step-3"})
        mgr.transition("T-001", "paused")
        hint = mgr.resume("T-001")
        self.assertEqual(hint, "Continue from step-3")
        self.assertEqual(mgr.get("T-001")["status"], "in_progress")

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "state.json")
            mgr = TaskStateManager(path)
            mgr.create("T-001", "Test task")
            mgr.save()
            mgr2 = TaskStateManager(path)
            self.assertIsNotNone(mgr2.get("T-001"))

    def test_update_progress(self):
        mgr = TaskStateManager()
        mgr.create("T-001", "Test task")
        mgr.transition("T-001", "in_progress")
        mgr.update_progress("T-001", current_step=2, total_steps=5)
        state = mgr.get("T-001")
        self.assertEqual(state["current_step"], 2)
        self.assertAlmostEqual(state["progress_pct"], 40.0)
