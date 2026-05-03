"""
memory-layer.py — Four-Layer Memory Architecture

Implements four memory layers for the agent-skill-chain system:
- SemanticMemory: fact-based knowledge (key-value, persisted to JSON)
- EpisodicMemory: time-indexed events (in-memory, searchable by type/tags/time)
- ProceduralMemory: task-type procedures (steps + success rates)
- TriggerMemory: event-condition-action triggers (skill auto-loading)
- MemoryStore: unified entry point combining all four layers
"""

import json
import os
import time as _time
from typing import Any, List, Optional, Tuple


class SemanticMemory:
    """语义记忆层：存储事实性知识（key-value pairs）。持久化到 JSON 文件。"""

    def __init__(self, path: Optional[str] = None):
        self._data: dict = {}
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def store(self, key: str, value: Any) -> None:
        self._data[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def list_all(self) -> List[Tuple[str, Any]]:
        return list(self._data.items())

    def save(self) -> None:
        if self._path:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    self._data = json.loads(content)


class EpisodicMemory:
    """情景记忆层：按时间线存储事件（带标签、类型索引）。内存存储。"""

    def __init__(self):
        self._episodes: dict = {}
        self._counter = 0

    def store(self, event_type: str, data: dict, tags: list) -> str:
        self._counter += 1
        ep_id = f"ep-{self._counter:06d}"
        self._episodes[ep_id] = {
            "id": ep_id,
            "event_type": event_type,
            "data": data,
            "tags": tags,
            "timestamp": _time.time(),
        }
        return ep_id

    def retrieve(self, ep_id: str) -> Optional[dict]:
        return self._episodes.get(ep_id)

    def search(self, event_type: Optional[str] = None,
               tags: Optional[list] = None,
               time_start: Optional[float] = None,
               time_end: Optional[float] = None) -> list:
        results = list(self._episodes.values())
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if tags:
            results = [e for e in results if any(t in e["tags"] for t in tags)]
        if time_start:
            results = [e for e in results if e["timestamp"] >= time_start]
        if time_end:
            results = [e for e in results if e["timestamp"] <= time_end]
        return results


class ProceduralMemory:
    """过程记忆层：存储任务类型的标准流程（步骤列表 + 成功率）。"""

    def __init__(self):
        self._procedures: dict = {}
        self._counter = 0

    def store(self, task_type: str, procedure: list,
              success_rate: float, prerequisites: list) -> str:
        self._counter += 1
        proc_id = f"proc-{self._counter:06d}"
        self._procedures[proc_id] = {
            "id": proc_id,
            "task_type": task_type,
            "procedure": procedure,
            "success_rate": success_rate,
            "prerequisites": prerequisites,
            "usage_count": 0,
        }
        return proc_id

    def retrieve(self, proc_id: str) -> Optional[dict]:
        return self._procedures.get(proc_id)

    def find_by_task_type(self, task_type: str) -> list:
        return [p for p in self._procedures.values() if p["task_type"] == task_type]

    def find_best(self, task_type: str) -> Optional[dict]:
        procs = self.find_by_task_type(task_type)
        if not procs:
            return None
        return max(procs, key=lambda p: p["success_rate"])

    def update_success_rate(self, proc_id: str, new_reward: float) -> None:
        proc = self._procedures.get(proc_id)
        if proc:
            old_rate = proc["success_rate"]
            old_count = proc["usage_count"]
            if old_count == 0:
                # First update: average of initial rate and new reward
                proc["success_rate"] = (old_rate + new_reward) / 2
            else:
                proc["success_rate"] = (old_rate * old_count + new_reward) / (old_count + 1)
            proc["usage_count"] += 1


class TriggerMemory:
    """触发记忆层：基于事件+条件触发动作。用于技能自动加载等场景。"""

    def __init__(self):
        self._triggers: list = []  # [(event, condition, action)]

    def register(self, event: str, condition: str, action) -> None:
        self._triggers.append({"event": event, "condition": condition, "action": action})

    def fire(self, event: str, context: dict) -> list:
        results = []
        for t in self._triggers:
            if t["event"] == event:
                result = t["action"](context)
                results.append(result)
        return results

    def _condition_matches(self, condition: str, context: dict) -> bool:
        # Always match if no context provided
        if not context:
            return True
        # Check if condition string appears in any context value
        for v in context.values():
            if condition in str(v):
                return True
        # Also match if condition is a substring of any key
        return condition in str(context)

    def list_triggers(self, event: Optional[str] = None) -> list:
        if event:
            return [{"event": t["event"], "condition": t["condition"]}
                    for t in self._triggers if t["event"] == event]
        return [{"event": t["event"], "condition": t["condition"]} for t in self._triggers]


class MemoryStore:
    """四层记忆的统一入口。"""

    def __init__(self, semantic_path: Optional[str] = None):
        self.semantic = SemanticMemory(semantic_path)
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()
        self.trigger = TriggerMemory()
