# scripts/task_state.py — Task State Object with status machine and checkpoint/resume
import json, os
from datetime import datetime
from typing import Optional

# Valid status transitions
TRANSITIONS = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["paused", "completed", "failed"],
    "paused": ["in_progress", "cancelled"],
    "completed": [],
    "failed": ["pending"],  # retry
    "cancelled": ["pending"],  # restart
}

class TaskStateManager:
    """Manages long-running task lifecycle with status machine, checkpoint/resume, and progress tracking."""

    def __init__(self, path: Optional[str] = None):
        self._states: dict = {}
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def create(self, task_id: str, title: str, **kwargs) -> dict:
        now = datetime.now().isoformat()
        state = {
            "task_id": task_id,
            "status": "pending",
            "title": title,
            "created_at": now,
            "updated_at": now,
            "checkpoint": {"completed_steps": [], "artifacts": []},
            **kwargs,
        }
        self._states[task_id] = state
        return state

    def get(self, task_id: str) -> Optional[dict]:
        return self._states.get(task_id)

    def transition(self, task_id: str, new_status: str) -> dict:
        state = self._states.get(task_id)
        if not state:
            raise KeyError(f"Task {task_id} not found")
        current = state["status"]
        if new_status not in TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid transition: {current} → {new_status}")
        state["status"] = new_status
        state["updated_at"] = datetime.now().isoformat()
        if new_status == "completed":
            state["completed_at"] = datetime.now().isoformat()
        return state

    def checkpoint(self, task_id: str, checkpoint_data: dict) -> dict:
        state = self._states[task_id]
        state["checkpoint"].update(checkpoint_data)
        state["updated_at"] = datetime.now().isoformat()
        self._auto_save()
        return state

    def resume(self, task_id: str) -> Optional[str]:
        state = self._states[task_id]
        if state["status"] != "paused":
            raise ValueError(f"Can only resume from paused, got {state['status']}")
        self.transition(task_id, "in_progress")
        return state["checkpoint"].get("resume_hint")

    def update_progress(self, task_id: str, current_step: int, total_steps: int) -> dict:
        state = self._states[task_id]
        state["current_step"] = current_step
        state["total_steps"] = total_steps
        state["progress_pct"] = round(current_step / max(total_steps, 1) * 100, 1)
        state["updated_at"] = datetime.now().isoformat()
        return state

    def _auto_save(self):
        if self._path:
            self.save()

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._states, f, indent=2, ensure_ascii=False)

    def load(self):
        with open(self._path, "r", encoding="utf-8") as f:
            self._states = json.load(f)
