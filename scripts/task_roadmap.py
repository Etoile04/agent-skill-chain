"""Task Roadmap: goal → milestone → task hierarchy for tracking global position."""

import json
from typing import Optional


class TaskRoadmap:
    """目标链：goal → milestone → task 层级。"""

    def __init__(self, roadmap_id: str, title: str, description: str = ""):
        self.roadmap_id = roadmap_id
        self.title = title
        self.description = description
        self.milestones: list = []

    def add_milestone(self, milestone_id: str, title: str) -> None:
        self.milestones.append({
            "milestone_id": milestone_id,
            "title": title,
            "status": "pending",
            "tasks": [],
        })

    def add_task(self, milestone_id: str, task_id: str, title: str) -> None:
        for ms in self.milestones:
            if ms["milestone_id"] == milestone_id:
                ms["tasks"].append({
                    "task_id": task_id, "title": title, "status": "pending"
                })
                return
        raise KeyError(f"Milestone {milestone_id} not found")

    def get_milestone(self, milestone_id: str) -> Optional[dict]:
        for ms in self.milestones:
            if ms["milestone_id"] == milestone_id:
                return ms
        return None

    def set_task_status(self, task_id: str, status: str) -> None:
        for ms in self.milestones:
            for task in ms["tasks"]:
                if task["task_id"] == task_id:
                    task["status"] = status
                    # Auto-update milestone status
                    if all(t["status"] == "completed" for t in ms["tasks"]):
                        ms["status"] = "completed"
                    elif any(t["status"] == "in_progress" for t in ms["tasks"]):
                        ms["status"] = "in_progress"
                    return

    def get_current_position(self) -> dict:
        for ms in self.milestones:
            for task in ms["tasks"]:
                if task["status"] != "completed":
                    return {"milestone_id": ms["milestone_id"], "task_id": task["task_id"]}
        return {"milestone_id": "ALL_COMPLETE", "task_id": "ALL_COMPLETE"}

    def progress_pct(self) -> float:
        total = len(self.all_tasks())
        if total == 0:
            return 0.0
        completed = sum(1 for t in self.all_tasks() if t["status"] == "completed")
        return round(completed / total * 100, 1)

    def all_tasks(self) -> list:
        tasks = []
        for ms in self.milestones:
            tasks.extend(ms["tasks"])
        return tasks

    def to_dict(self) -> dict:
        return {
            "roadmap_id": self.roadmap_id,
            "title": self.title,
            "description": self.description,
            "milestones": self.milestones,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskRoadmap":
        rm = cls(data["roadmap_id"], data["title"], data.get("description", ""))
        rm.milestones = data["milestones"]
        return rm
