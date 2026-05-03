import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from task_roadmap import TaskRoadmap


class TestTaskRoadmap(unittest.TestCase):
    def test_create_roadmap(self):
        rm = TaskRoadmap("RM-001", "Phase 2 Implementation")
        self.assertEqual(rm.roadmap_id, "RM-001")
        self.assertEqual(len(rm.milestones), 0)

    def test_add_milestone(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "Middle Layer")
        self.assertEqual(len(rm.milestones), 1)

    def test_add_task_to_milestone(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "Middle Layer")
        rm.add_task("MS-001", "T-001", "Memory Layers")
        rm.add_task("MS-001", "T-002", "Skill Trigger")
        ms = rm.get_milestone("MS-001")
        self.assertEqual(len(ms["tasks"]), 2)

    def test_get_current_position(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "Middle Layer")
        rm.add_task("MS-001", "T-001", "Memory")
        rm.add_task("MS-001", "T-002", "Trigger")
        rm.add_milestone("MS-002", "Outer Layer")
        rm.add_task("MS-002", "T-003", "Task State")
        rm.set_task_status("T-001", "completed")
        pos = rm.get_current_position()
        self.assertEqual(pos["milestone_id"], "MS-001")
        self.assertEqual(pos["task_id"], "T-002")

    def test_progress_pct(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "M1")
        rm.add_task("MS-001", "T-001", "Task 1")
        rm.add_task("MS-001", "T-002", "Task 2")
        rm.add_task("MS-001", "T-003", "Task 3")
        rm.add_milestone("MS-002", "M2")
        rm.add_task("MS-002", "T-004", "Task 4")
        rm.set_task_status("T-001", "completed")
        self.assertAlmostEqual(rm.progress_pct(), 25.0)

    def test_all_tasks(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "M1")
        rm.add_task("MS-001", "T-001", "Task 1")
        rm.add_task("MS-001", "T-002", "Task 2")
        rm.add_milestone("MS-002", "M2")
        rm.add_task("MS-002", "T-003", "Task 3")
        self.assertEqual(len(rm.all_tasks()), 3)

    def test_to_dict_and_from_dict(self):
        rm = TaskRoadmap("RM-001", "Phase 2")
        rm.add_milestone("MS-001", "M1")
        rm.add_task("MS-001", "T-001", "Task 1")
        d = rm.to_dict()
        rm2 = TaskRoadmap.from_dict(d)
        self.assertEqual(rm2.roadmap_id, "RM-001")
        self.assertEqual(len(rm2.all_tasks()), 1)


if __name__ == "__main__":
    unittest.main()
