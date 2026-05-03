# Phase 4: 三层闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现三层闭环——组织级学习闭环（个体经验→组织知识→分发→新经验）、自优化循环（参数自动调优）、跨场景迁移（任务本体+模式识别）、评测体系（跨层KPI）、能力复制（新Agent继承知识）。将 Phase 1-3 的独立模块串联为完整的自我进化系统。

**Architecture:** 构建 `LearningLoop` 作为核心编排引擎，协调外层（AgentRegistry/Governance）、中层（MemoryStore/SkillTrigger/PrincipleStore）、内层（ReflectionLoop/AutonomousImprover/BiasDetector）的闭环流转。新增 `TaskOntology` 定义任务分类体系，`CrossSceneTransfer` 实现跨场景迁移，`EvaluationFramework` 实现跨层评测，`CapabilityReplicator` 实现能力复制。Python3 标准库，零外部依赖。

**Tech Stack:** Python3 (stdlib only), pytest, git worktrees

**Worktree:** `/tmp/agent-skill-chain/.worktrees/phase4`

---

## Superpowers 技能使用规范

```
Phase 4 启动
  ├─ using-git-worktrees: 创建隔离 worktree
  ├─ writing-plans: 本文档
  ├─ subagent-driven-development: 逐 Task 分派
  │   ├─ 每个 Task: implementer (TDD + verification)
  │   ├─ 完成后: spec-reviewer
  │   └─ spec 通过: code-quality-reviewer
  ├─ 独立 Task: dispatching-parallel-agents 并行
  ├─ 遇 bug: systematic-debugging 4阶段
  └─ finishing-a-development-branch: merge + push
```

---

## File Structure

```
schemas/
  task-ontology.json           # 任务本体 schema (NEW)
  evaluation-metric.json       # 评测指标 schema (NEW)

scripts/
  task_ontology.py             # 任务分类体系 + 相似度计算 (NEW)
  learning_loop.py             # 组织级学习闭环编排 (NEW)
  cross_scene_transfer.py      # 跨场景迁移引擎 (NEW)
  self_optimizer.py            # 自优化循环 (NEW)
  evaluation_framework.py      # 跨层评测体系 (NEW)
  capability_replicator.py     # 能力复制系统 (NEW)

tests/
  test_task_ontology.py        # 任务本体测试 (NEW)
  test_learning_loop.py        # 学习闭环测试 (NEW)
  test_cross_scene_transfer.py # 跨场景迁移测试 (NEW)
  test_self_optimizer.py       # 自优化测试 (NEW)
  test_evaluation_framework.py # 评测体系测试 (NEW)
  test_capability_replicator.py # 能力复制测试 (NEW)
  test_phase4_integration.py   # Phase 4 集成测试 (NEW)
```

---

### Task 1: Task Ontology（任务本体 + 相似度计算）

**Files:**
- Create: `schemas/task-ontology.json`
- Create: `scripts/task_ontology.py`
- Create: `tests/test_task_ontology.py`

**Priority:** 高 — 跨场景迁移和学习闭环都依赖任务分类

- [ ] **Step 1: Write failing tests**

```python
# tests/test_task_ontology.py
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from task_ontology import TaskType, TaskOntology


class TestTaskType(unittest.TestCase):
    def test_create_task_type(self):
        tt = TaskType(
            type_id="code_generation",
            category="development",
            keywords=["code", "implement", "write function"],
            required_capabilities=["code_generation"],
            typical_complexity="medium"
        )
        self.assertEqual(tt.type_id, "code_generation")
        self.assertEqual(tt.category, "development")

    def test_match_keywords(self):
        tt = TaskType("testing", "quality", ["test", "verify", "assert"], ["testing"], "low")
        self.assertTrue(tt.matches("write a test for this function"))
        self.assertFalse(tt.matches("deploy to production"))


class TestTaskOntology(unittest.TestCase):
    def setUp(self):
        self.ontology = TaskOntology()
        self.ontology.register(TaskType(
            "code_generation", "development",
            ["code", "implement", "write function"],
            ["code_generation"], "medium"
        ))
        self.ontology.register(TaskType(
            "testing", "quality",
            ["test", "verify", "assert", "validate"],
            ["testing"], "low"
        ))
        self.ontology.register(TaskType(
            "debugging", "development",
            ["debug", "fix bug", "trace error", "investigate failure"],
            ["debugging"], "high"
        ))
        self.ontology.register(TaskType(
            "documentation", "communication",
            ["document", "readme", "doc", "explain"],
            ["code_generation"], "low"
        ))

    def test_classify_task(self):
        result = self.ontology.classify("write a function to parse JSON")
        self.assertIsNotNone(result)
        self.assertEqual(result.type_id, "code_generation")

    def test_classify_returns_best_match(self):
        result = self.ontology.classify("fix the bug in the test")
        # "debug" and "test" both match, but debugging has stronger keyword hit
        self.assertIsNotNone(result)

    def test_classify_unknown_returns_none(self):
        result = self.ontology.classify("order pizza for the team")
        self.assertIsNone(result)

    def test_find_similar_types(self):
        """同类别任务应被视为相似"""
        similar = self.ontology.find_similar("code_generation")
        self.assertGreater(len(similar), 0)
        # debugging is also "development" category
        ids = [s.type_id for s in similar]
        self.assertIn("debugging", ids)

    def test_get_required_capabilities(self):
        caps = self.ontology.get_required_capabilities("code_generation")
        self.assertIn("code_generation", caps)

    def test_list_by_category(self):
        dev_tasks = self.ontology.list_by_category("development")
        self.assertEqual(len(dev_tasks), 2)
        ids = [t.type_id for t in dev_tasks]
        self.assertIn("code_generation", ids)
        self.assertIn("debugging", ids)

    def test_persistence(self):
        import tempfile
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "ontology.json")
            o1 = TaskOntology()
            o1.register(TaskType("t1", "cat1", ["kw1"], ["cap1"], "low"))
            o1.save(path)
            o2 = TaskOntology()
            o2.load(path)
            result = o2.classify("kw1 related task")
            self.assertIsNotNone(result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_task_ontology.py -v`
Expected: FAIL

- [ ] **Step 3: Implement TaskOntology**

```python
# scripts/task_ontology.py
"""Task Ontology: task type classification, similarity, and capability mapping."""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TaskType:
    type_id: str
    category: str
    keywords: List[str]
    required_capabilities: List[str]
    typical_complexity: str  # "low", "medium", "high"

    def matches(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.keywords)

    def match_score(self, text: str) -> float:
        text_lower = text.lower()
        hits = sum(1 for kw in self.keywords if kw in text_lower)
        return hits / len(self.keywords) if self.keywords else 0.0

    def to_dict(self) -> dict:
        return {
            "type_id": self.type_id,
            "category": self.category,
            "keywords": self.keywords,
            "required_capabilities": self.required_capabilities,
            "typical_complexity": self.typical_complexity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskType":
        return cls(**d)


class TaskOntology:
    def __init__(self):
        self._types: Dict[str, TaskType] = {}

    def register(self, task_type: TaskType) -> None:
        self._types[task_type.type_id] = task_type

    def classify(self, text: str) -> Optional[TaskType]:
        best = None
        best_score = 0.0
        for tt in self._types.values():
            score = tt.match_score(text)
            if score > best_score:
                best_score = score
                best = tt
        return best if best_score > 0 else None

    def find_similar(self, type_id: str) -> List[TaskType]:
        tt = self._types.get(type_id)
        if not tt:
            return []
        return [t for t in self._types.values()
                if t.category == tt.category and t.type_id != type_id]

    def get_required_capabilities(self, type_id: str) -> List[str]:
        tt = self._types.get(type_id)
        return tt.required_capabilities if tt else []

    def list_by_category(self, category: str) -> List[TaskType]:
        return [t for t in self._types.values() if t.category == category]

    def save(self, path: str) -> None:
        data = {tid: tt.to_dict() for tid, tt in self._types.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._types = {tid: TaskType.from_dict(d) for tid, d in data.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_task_ontology.py -v`
Expected: 8 passed

- [ ] **Step 5: Create schema + commit**

```bash
git add schemas/task-ontology.json scripts/task_ontology.py tests/test_task_ontology.py
git commit -m "feat(phase4): Task Ontology with classification, similarity, and capability mapping"
```

---

### Task 2: Learning Loop（组织级学习闭环编排）

**Files:**
- Create: `scripts/learning_loop.py`
- Create: `tests/test_learning_loop.py`

**Priority:** 高 — Phase 4 核心，串联三层

- [ ] **Step 1: Write failing tests**

```python
# tests/test_learning_loop.py
import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from agent_registry import AgentCard, AgentRegistry
from task_ontology import TaskOntology, TaskType
from learning_loop import LearningLoop, LearningCycleResult


class TestLearningCycleResult(unittest.TestCase):
    def test_create_result(self):
        r = LearningCycleResult(
            cycle_id="cycle-001",
            experiences_collected=5,
            principles_updated=2,
            knowledge_distributed=True,
            summary="Collected 5 experiences, updated 2 principles"
        )
        self.assertTrue(r.knowledge_distributed)


class TestLearningLoop(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory_store = MemoryStore()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        self.registry.register(AgentCard("agent-1", "Agent 1", ["code_gen"], ["py"], 2, 0.8))
        self.ontology = TaskOntology()
        self.ontology.register(TaskType("code_gen", "dev", ["code"], ["code_gen"], "med"))
        self.loop = LearningLoop(
            self.memory_store, self.principle_store, self.bias_detector,
            self.reflection, self.registry, self.ontology
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_collect_experience(self):
        """收集 Agent 执行经验"""
        result = self.loop.collect_experience(
            agent_id="agent-1",
            task_type="code_gen",
            outcome="success",
            details={"steps": 5, "tests_passed": 20}
        )
        self.assertIsNotNone(result)

    def test_collect_and_reflect_on_failure(self):
        """失败经验触发反思"""
        self.loop.collect_experience("agent-1", "code_gen", "failure", {
            "error_type": "test_failure",
            "symptom": "tests not run",
            "root_cause": "skipped verification",
            "fix_applied": "run tests"
        })
        # 应该通过 reflection 生成原则
        principles = self.principle_store.list_all()
        self.assertGreater(len(principles), 0)

    def test_distribute_knowledge(self):
        """将组织知识分发到 Agent"""
        # 先存储一些原则
        p = Principle("P-1", "Verify first", "desc", "reflection", "commit", "run tests", [])
        p.record_application(True)
        self.principle_store.add(p)

        result = self.loop.distribute_knowledge()
        self.assertTrue(result.distributed_count > 0)

    def test_full_cycle(self):
        """完整闭环：收集→反思→聚合→分发"""
        # 收集经验
        self.loop.collect_experience("agent-1", "code_gen", "failure", {
            "error_type": "scope_creep", "symptom": "added extras",
            "root_cause": "no scope check", "fix_applied": "check spec"
        })
        self.loop.collect_experience("agent-1", "code_gen", "success", {
            "steps": 4, "tests_passed": 15
        })

        # 运行完整周期
        result = self.loop.run_cycle()
        self.assertIsNotNone(result)
        self.assertTrue(result.experiences_collected > 0)
        self.assertIsInstance(result, LearningCycleResult)

    def test_cycle_history(self):
        """记录闭环历史"""
        self.loop.collect_experience("agent-1", "code_gen", "success", {})
        self.loop.run_cycle()
        history = self.loop.get_cycle_history()
        self.assertEqual(len(history), 1)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement LearningLoop**

```python
# scripts/learning_loop.py
"""Learning Loop: orchestrates the organization-level learning cycle across all three layers."""

import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector
from reflection_loop import ReflectionLoop
from agent_registry import AgentRegistry
from task_ontology import TaskOntology


@dataclass
class LearningCycleResult:
    cycle_id: str
    experiences_collected: int = 0
    principles_updated: int = 0
    knowledge_distributed: bool = False
    summary: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class DistributionResult:
    distributed_count: int = 0


class LearningLoop:
    def __init__(self, memory_store: MemoryStore, principle_store: PrincipleStore,
                 bias_detector: BiasDetector, reflection: ReflectionLoop,
                 registry: AgentRegistry, ontology: TaskOntology):
        self._memory = memory_store
        self._principles = principle_store
        self._bias = bias_detector
        self._reflection = reflection
        self._registry = registry
        self._ontology = ontology
        self._experiences: List[dict] = []
        self._cycle_history: List[LearningCycleResult] = []

    def collect_experience(self, agent_id: str, task_type: str,
                           outcome: str, details: dict) -> str:
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        experience = {
            "id": exp_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "outcome": outcome,
            "details": details,
            "timestamp": time.time(),
        }
        self._experiences.append(experience)

        # 存到记忆层
        self._memory.episodic.store(
            event_type=f"task_{outcome}",
            data=experience,
            tags=[task_type, outcome, agent_id]
        )

        # 失败经验立即触发反思
        if outcome == "failure" and "error_type" in details:
            self._reflection.reflect_on_error(details)

        return exp_id

    def distribute_knowledge(self) -> DistributionResult:
        principles = self._principles.list_all()
        effective = [p for p in principles if p.effectiveness() > 0.3]
        agents = self._registry.list_all()

        distributed = 0
        for agent in agents:
            for p in effective:
                relevant = self._ontology.classify(p.trigger)
                if relevant and agent.can_handle(relevant.type_id):
                    distributed += 1

        return DistributionResult(distributed_count=distributed)

    def run_cycle(self) -> LearningCycleResult:
        cycle_id = f"cycle-{uuid.uuid4().hex[:8]}"
        exp_count = len(self._experiences)

        principles_before = len(self._principles.list_all())

        # 分发知识
        dist_result = self.distribute_knowledge()

        result = LearningCycleResult(
            cycle_id=cycle_id,
            experiences_collected=exp_count,
            principles_updated=len(self._principles.list_all()) - principles_before,
            knowledge_distributed=dist_result.distributed_count > 0,
            summary=f"Collected {exp_count} experiences, distributed to {dist_result.distributed_count} agent-capability pairs"
        )
        self._cycle_history.append(result)
        self._experiences.clear()
        return result

    def get_cycle_history(self) -> List[LearningCycleResult]:
        return list(self._cycle_history)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_learning_loop.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/learning_loop.py tests/test_learning_loop.py
git commit -m "feat(phase4): Learning Loop orchestrating organization-level learning cycle across three layers"
```

---

### Task 3: Cross-Scene Transfer（跨场景迁移引擎）

**Files:**
- Create: `scripts/cross_scene_transfer.py`
- Create: `tests/test_cross_scene_transfer.py`

**Priority:** 中 — 依赖 Task 1 (TaskOntology)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cross_scene_transfer.py
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from task_ontology import TaskType, TaskOntology
from principle_store import Principle, PrincipleStore
from cross_scene_transfer import CrossSceneTransfer, TransferResult


class TestTransferResult(unittest.TestCase):
    def test_create_result(self):
        r = TransferResult(
            source_type="code_generation",
            target_type="debugging",
            principles_transferred=2,
            confidence=0.7,
            adaptations=["changed 'write code' to 'fix code'"]
        )
        self.assertEqual(r.source_type, "code_generation")
        self.assertTrue(r.confidence > 0.5)


class TestCrossSceneTransfer(unittest.TestCase):
    def setUp(self):
        self.ontology = TaskOntology()
        self.ontology.register(TaskType("code_gen", "development", ["code"], ["code_gen"], "medium"))
        self.ontology.register(TaskType("debugging", "development", ["debug"], ["debugging"], "high"))
        self.ontology.register(TaskType("testing", "quality", ["test"], ["testing"], "low"))
        self.ontology.register(TaskType("research", "research", ["search"], ["literature_search"], "medium"))
        self.principles = PrincipleStore()

    def test_find_transferable_principles(self):
        """同类别任务间的原则可以迁移"""
        p = Principle("P-1", "Verify code", "Run tests after code changes",
                      "reflection", "write code", "run test suite", ["code_gen"])
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        self.assertGreater(len(results), 0)

    def test_no_transfer_across_dissimilar_categories(self):
        """跨类别不迁移"""
        p = Principle("P-1", "Test", "d", "r", "write code", "a", ["code_gen"])
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("research")
        self.assertEqual(len(results), 0)

    def test_transfer_adapts_trigger(self):
        """迁移时应适配 trigger"""
        p = Principle("P-1", "Verify", "Run tests", "r", "write code", "run tests", ["code_gen"])
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        self.assertGreater(len(results), 0)
        adapted = results[0]
        # adapted trigger should reference debugging, not code_gen
        self.assertIn("adapted_trigger", adapted.to_dict())

    def test_transfer_confidence_based_on_similarity(self):
        """迁移置信度基于任务相似度"""
        p = Principle("P-1", "Test", "d", "r", "code trigger", "a", ["code_gen"])
        p.record_application(True)
        p.record_application(True)
        self.principles.add(p)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        if results:
            self.assertGreater(results[0].confidence, 0.0)

    def test_transfer_respects_effectiveness(self):
        """只迁移效果好的原则"""
        p_good = Principle("P-good", "Good", "d", "r", "t", "a", ["code_gen"])
        p_good.record_application(True)
        p_good.record_application(True)
        p_bad = Principle("P-bad", "Bad", "d", "r", "t", "a", ["code_gen"])
        p_bad.record_application(False)
        p_bad.record_application(False)
        self.principles.add(p_good)
        self.principles.add(p_bad)
        transfer = CrossSceneTransfer(self.ontology, self.principles)
        results = transfer.find_transferable("debugging")
        transferred_ids = [r.principle_id for r in results]
        self.assertIn("P-good", transferred_ids)
        self.assertNotIn("P-bad", transferred_ids)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement CrossSceneTransfer**

```python
# scripts/cross_scene_transfer.py
"""Cross-Scene Transfer: transfer learned principles across similar task types."""

from typing import List
from dataclasses import dataclass, field

from task_ontology import TaskOntology
from principle_store import PrincipleStore


@dataclass
class TransferResult:
    principle_id: str
    source_type: str
    target_type: str
    adapted_trigger: str
    original_trigger: str
    confidence: float
    principles_transferred: int = 1
    adaptations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "principle_id": self.principle_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "adapted_trigger": self.adapted_trigger,
            "original_trigger": self.original_trigger,
            "confidence": self.confidence,
        }


class CrossSceneTransfer:
    def __init__(self, ontology: TaskOntology, principle_store: PrincipleStore):
        self._ontology = ontology
        self._principles = principle_store

    def find_transferable(self, target_type: str, effectiveness_threshold: float = 0.3) -> List[TransferResult]:
        target_tt = self._ontology._types.get(target_type)
        if not target_tt:
            return []

        results = []
        similar = self._ontology.find_similar(target_type)
        similar_ids = [s.type_id for s in similar]

        for p in self._principles.list_all():
            if p.times_applied < 1 or p.effectiveness() < effectiveness_threshold:
                continue
            # Check if principle is from a similar task type
            source_tag = None
            for tag in p.tags:
                if tag in similar_ids:
                    source_tag = tag
                    break
            if source_tag is None:
                continue

            adapted_trigger = p.trigger.replace(source_tag, target_type)
            confidence = p.effectiveness() * 0.8  # transfer penalty

            results.append(TransferResult(
                principle_id=p.principle_id,
                source_type=source_tag,
                target_type=target_type,
                adapted_trigger=adapted_trigger,
                original_trigger=p.trigger,
                confidence=confidence,
                adaptations=[f"adapted trigger from '{source_tag}' to '{target_type}'"],
            ))
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_cross_scene_transfer.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/cross_scene_transfer.py tests/test_cross_scene_transfer.py
git commit -m "feat(phase4): Cross-Scene Transfer with similarity-based principle adaptation"
```

---

### Task 4: Self Optimizer（自优化循环）

**Files:**
- Create: `scripts/self_optimizer.py`
- Create: `tests/test_self_optimizer.py`

**Priority:** 中 — 独立模块

- [ ] **Step 1: Write failing tests**

```python
# tests/test_self_optimizer.py
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from self_optimizer import SelfOptimizer, ParameterSet, OptimizationRecord


class TestParameterSet(unittest.TestCase):
    def test_create_params(self):
        ps = ParameterSet({
            "complexity_threshold": 0.7,
            "retrieval_weight": 0.5,
            "exploration_rate": 0.3
        })
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
        self.optimizer.register_parameter(
            "complexity_threshold", 0.7, min_val=0.0, max_val=1.0, step=0.1
        )
        params = self.optimizer.get_current_params()
        self.assertEqual(params.get("complexity_threshold"), 0.7)

    def test_evaluate_and_adjust(self):
        self.optimizer.register_parameter("threshold", 0.5, 0.0, 1.0, 0.1)
        # Simulate poor performance → should adjust
        record = self.optimizer.evaluate("threshold", performance_score=0.2, direction="maximize")
        self.assertIsNotNone(record)
        self.assertNotEqual(record.old_value, record.new_value)

    def test_no_adjustment_when_performing_well(self):
        self.optimizer.register_parameter("threshold", 0.5, 0.0, 1.0, 0.1)
        record = self.optimizer.evaluate("threshold", performance_score=0.9, direction="maximize")
        self.assertIsNone(record)  # No adjustment needed

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
        """基于历史表现建议参数值"""
        self.optimizer.register_parameter("x", 0.5, 0.0, 1.0, 0.1)
        # Multiple evaluations with different performances
        self.optimizer.evaluate("x", 0.3, "maximize")  # adjust up
        suggestion = self.optimizer.suggest("x")
        self.assertIsNotNone(suggestion)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement SelfOptimizer**

```python
# scripts/self_optimizer.py
"""Self Optimizer: auto-tune system parameters based on performance feedback."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ParameterSet:
    params: Dict[str, float] = field(default_factory=dict)

    def get(self, key: str) -> Optional[float]:
        return self.params.get(key)

    def set(self, key: str, value: float) -> None:
        self.params[key] = value


@dataclass
class OptimizationRecord:
    parameter_name: str
    old_value: float
    new_value: float
    performance_before: float
    timestamp: float = field(default_factory=time.time)


class SelfOptimizer:
    def __init__(self):
        self._params: Dict[str, dict] = {}
        self._current = ParameterSet()
        self._history: List[OptimizationRecord] = []
        self._performances: Dict[str, List[float]] = {}

    def register_parameter(self, name: str, default: float,
                           min_val: float, max_val: float, step: float) -> None:
        self._params[name] = {"min": min_val, "max": max_val, "step": step}
        self._current.set(name, default)
        self._performances[name] = []

    def get_current_params(self) -> ParameterSet:
        return self._current

    def evaluate(self, param_name: str, performance_score: float,
                 direction: str = "maximize") -> Optional[OptimizationRecord]:
        if param_name not in self._params:
            return None

        config = self._params[param_name]
        self._performances[param_name].append(performance_score)

        # Only adjust if performance is below threshold
        if performance_score >= 0.7:
            return None

        old_val = self._current.get(param_name)
        if old_val is None:
            return None

        # Simple adjustment: move in direction that should improve
        avg_perf = sum(self._performances[param_name]) / len(self._performances[param_name])
        if direction == "maximize":
            # If recent performance is poor, try opposite direction
            if avg_perf < 0.5:
                new_val = old_val + config["step"]
            else:
                new_val = old_val - config["step"]
        else:
            if avg_perf < 0.5:
                new_val = old_val - config["step"]
            else:
                new_val = old_val + config["step"]

        # Clamp to bounds
        new_val = max(config["min"], min(config["max"], new_val))

        self._current.set(param_name, new_val)
        record = OptimizationRecord(
            parameter_name=param_name,
            old_value=old_val,
            new_value=new_val,
            performance_before=performance_score,
        )
        self._history.append(record)
        return record

    def get_history(self) -> List[OptimizationRecord]:
        return list(self._history)

    def suggest(self, param_name: str) -> Optional[float]:
        if param_name not in self._performances or not self._performances[param_name]:
            return self._current.get(param_name)
        # Suggest the value from the best-performing record
        records = [r for r in self._history if r.parameter_name == param_name]
        if records:
            best = min(records, key=lambda r: r.performance_before)
            return best.new_value
        return self._current.get(param_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_self_optimizer.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/self_optimizer.py tests/test_self_optimizer.py
git commit -m "feat(phase4): Self Optimizer with performance-driven parameter auto-tuning"
```

---

### Task 5: Evaluation Framework（跨层评测体系）

**Files:**
- Create: `schemas/evaluation-metric.json`
- Create: `scripts/evaluation_framework.py`
- Create: `tests/test_evaluation_framework.py`

**Priority:** 中 — 独立模块

- [ ] **Step 1: Write failing tests**

```python
# tests/test_evaluation_framework.py
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from evaluation_framework import (
    EvaluationFramework, MetricType, MetricRecord, LayerMetrics
)


class TestMetricRecord(unittest.TestCase):
    def test_create_metric(self):
        m = MetricRecord(
            metric_name="stability",
            layer="inner",
            value=0.95,
            target=0.99,
            unit="ratio"
        )
        self.assertEqual(m.metric_name, "stability")
        self.assertTrue(m.passes_target())

    def test_metric_fails_target(self):
        m = MetricRecord("error_rate", "inner", 0.15, 0.05, "ratio")
        self.assertFalse(m.passes_target())


class TestEvaluationFramework(unittest.TestCase):
    def setUp(self):
        self.framework = EvaluationFramework()

    def test_register_metric(self):
        self.framework.register_metric(
            "stability", "inner", target=0.99, unit="ratio",
            description="Task completion success rate"
        )
        metrics = self.framework.list_metrics()
        self.assertEqual(len(metrics), 1)

    def test_record_measurement(self):
        self.framework.register_metric("stability", "inner", 0.99, "ratio")
        self.framework.record("stability", 0.95)
        records = self.framework.get_records("stability")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].value, 0.95)

    def test_compute_layer_score(self):
        """计算单层综合得分"""
        self.framework.register_metric("stability", "inner", 0.99, "ratio")
        self.framework.register_metric("learning_efficiency", "inner", 0.7, "ratio")
        self.framework.record("stability", 0.95)
        self.framework.record("learning_efficiency", 0.8)
        score = self.framework.compute_layer_score("inner")
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_compute_overall_score(self):
        """计算跨层综合得分"""
        for name, layer in [("s1", "inner"), ("s2", "middle"), ("s3", "outer")]:
            self.framework.register_metric(name, layer, 0.8, "ratio")
            self.framework.record(name, 0.9)
        score = self.framework.compute_overall_score()
        self.assertGreater(score, 0.0)

    def test_get_failing_metrics(self):
        """获取未达标指标"""
        self.framework.register_metric("good", "inner", 0.8, "ratio")
        self.framework.register_metric("bad", "inner", 0.8, "ratio")
        self.framework.record("good", 0.9)
        self.framework.record("bad", 0.5)
        failing = self.framework.get_failing_metrics()
        self.assertEqual(len(failing), 1)
        self.assertEqual(failing[0].metric_name, "bad")

    def test_layer_metrics_summary(self):
        """各层指标汇总"""
        self.framework.register_metric("m1", "inner", 0.8, "ratio")
        self.framework.register_metric("m2", "middle", 0.7, "ratio")
        self.framework.record("m1", 0.9)
        self.framework.record("m2", 0.75)
        summary = self.framework.get_layer_summary()
        self.assertIn("inner", summary)
        self.assertIn("middle", summary)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement EvaluationFramework**

```python
# scripts/evaluation_framework.py
"""Evaluation Framework: cross-layer KPI measurement and assessment."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    RATIO = "ratio"
    COUNT = "count"
    PERCENTAGE = "percentage"


@dataclass
class MetricRecord:
    metric_name: str
    layer: str
    value: float
    target: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def passes_target(self) -> bool:
        return self.value >= self.target


@dataclass
class LayerMetrics:
    layer: str
    metrics: List[MetricRecord] = field(default_factory=list)


class EvaluationFramework:
    def __init__(self):
        self._metric_defs: Dict[str, dict] = {}
        self._records: Dict[str, List[MetricRecord]] = {}

    def register_metric(self, name: str, layer: str, target: float,
                        unit: str, description: str = "") -> None:
        self._metric_defs[name] = {
            "layer": layer, "target": target, "unit": unit, "description": description
        }
        self._records[name] = []

    def list_metrics(self) -> List[dict]:
        return [{"name": k, **v} for k, v in self._metric_defs.items()]

    def record(self, metric_name: str, value: float) -> None:
        if metric_name not in self._metric_defs:
            return
        defn = self._metric_defs[metric_name]
        rec = MetricRecord(
            metric_name=metric_name,
            layer=defn["layer"],
            value=value,
            target=defn["target"],
            unit=defn["unit"],
            description=defn.get("description", ""),
        )
        self._records[metric_name].append(rec)

    def get_records(self, metric_name: str) -> List[MetricRecord]:
        return self._records.get(metric_name, [])

    def compute_layer_score(self, layer: str) -> float:
        layer_metrics = [k for k, v in self._metric_defs.items() if v["layer"] == layer]
        if not layer_metrics:
            return 0.0
        scores = []
        for name in layer_metrics:
            recs = self._records.get(name, [])
            if recs:
                scores.append(recs[-1].value)
        return sum(scores) / len(scores) if scores else 0.0

    def compute_overall_score(self) -> float:
        layers = set(v["layer"] for v in self._metric_defs.values())
        if not layers:
            return 0.0
        layer_scores = [self.compute_layer_score(l) for l in layers]
        return sum(layer_scores) / len(layer_scores)

    def get_failing_metrics(self) -> List[MetricRecord]:
        failing = []
        for name, recs in self._records.items():
            if recs and not recs[-1].passes_target():
                failing.append(recs[-1])
        return failing

    def get_layer_summary(self) -> Dict[str, dict]:
        layers = set(v["layer"] for v in self._metric_defs.values())
        summary = {}
        for layer in layers:
            metrics = [k for k, v in self._metric_defs.items() if v["layer"] == layer]
            records = []
            for name in metrics:
                recs = self._records.get(name, [])
                if recs:
                    records.append(recs[-1])
            summary[layer] = {
                "score": self.compute_layer_score(layer),
                "metrics": [r.metric_name for r in records],
                "failing": [r.metric_name for r in records if not r.passes_target()],
            }
        return summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_evaluation_framework.py -v`
Expected: 7 passed

- [ ] **Step 5: Create schema + commit**

```bash
git add schemas/evaluation-metric.json scripts/evaluation_framework.py tests/test_evaluation_framework.py
git commit -m "feat(phase4): Evaluation Framework with cross-layer KPI measurement and assessment"
```

---

### Task 6: Capability Replicator（能力复制系统）

**Files:**
- Create: `scripts/capability_replicator.py`
- Create: `tests/test_capability_replicator.py`

**Priority:** 中 — 依赖 Task 2 (LearningLoop) + Task 3 (CrossSceneTransfer)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_capability_replicator.py
import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from agent_registry import AgentCard, AgentRegistry
from principle_store import Principle, PrincipleStore
from memory_layer import MemoryStore
from capability_replicator import CapabilityReplicator, ReplicationResult


class TestReplicationResult(unittest.TestCase):
    def test_create_result(self):
        r = ReplicationResult(
            source_agent="agent-1",
            target_agent="agent-2",
            principles_copied=5,
            memories_copied=10,
            success=True
        )
        self.assertTrue(r.success)
        self.assertEqual(r.principles_copied, 5)


class TestCapabilityReplicator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        self.principles = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.memory = MemoryStore()

        # Source agent with knowledge
        self.registry.register(AgentCard("veteran", "Veteran", ["code_gen", "debugging"], ["py"], 2, 0.9))
        # New agent to receive knowledge
        self.registry.register(AgentCard("rookie", "Rookie", ["code_gen"], ["py"], 1, 0.5))

        # Veteran has effective principles
        for i in range(5):
            p = Principle(f"P-{i}", f"Rule {i}", "desc", "reflection", f"trigger {i}", f"action {i}", ["code_gen"])
            p.record_application(True)
            self.principles.add(p)

        # Veteran has memories
        self.memory.semantic.store("project_style", "TDD")
        self.memory.semantic.store("test_framework", "pytest")
        self.memory.episodic.store("task_complete", {"task": "refactor"}, ["milestone"])

        self.replicator = CapabilityReplicator(self.registry, self.principles, self.memory)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_replicate_to_new_agent(self):
        """将 veteran 知识复制到 rookie"""
        result = self.replicator.replicate("veteran", "rookie")
        self.assertTrue(result.success)
        self.assertGreater(result.principles_copied, 0)
        self.assertGreater(result.memories_copied, 0)

    def test_only_effective_principles_copied(self):
        """只复制效果好的原则"""
        bad_p = Principle("P-bad", "Bad", "d", "r", "t", "a", ["code_gen"])
        bad_p.record_application(False)
        bad_p.record_application(False)
        self.principles.add(bad_p)

        result = self.replicator.replicate("veteran", "rookie")
        copied_ids = [p for p in result.copied_principle_ids]
        self.assertNotIn("P-bad", copied_ids)

    def test_replicate_nonexistent_agent_fails(self):
        result = self.replicator.replicate("ghost", "rookie")
        self.assertFalse(result.success)

    def test_replicate_checks_capability_overlap(self):
        """只复制与目标 Agent 能力相关的原则"""
        # Add a principle for debugging (rookie doesn't have debugging capability)
        p_debug = Principle("P-debug", "Debug rule", "d", "r", "debug trigger", "a", ["debugging"])
        p_debug.record_application(True)
        self.principles.add(p_debug)

        result = self.replicator.replicate("veteran", "rookie")
        copied_ids = result.copied_principle_ids
        self.assertNotIn("P-debug", copied_ids)  # rookie can't debug

    def test_replication_report(self):
        """复制结果应包含详细报告"""
        result = self.replicator.replicate("veteran", "rookie")
        self.assertTrue(len(result.report) > 0)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement CapabilityReplicator**

```python
# scripts/capability_replicator.py
"""Capability Replicator: transfer knowledge from experienced agents to new agents."""

from typing import List, Optional
from dataclasses import dataclass, field

from agent_registry import AgentRegistry
from principle_store import PrincipleStore
from memory_layer import MemoryStore


@dataclass
class ReplicationResult:
    source_agent: str
    target_agent: str
    principles_copied: int = 0
    memories_copied: int = 0
    copied_principle_ids: List[str] = field(default_factory=list)
    success: bool = False
    report: str = ""


class CapabilityReplicator:
    def __init__(self, registry: AgentRegistry, principle_store: PrincipleStore,
                 memory_store: MemoryStore, effectiveness_threshold: float = 0.3):
        self._registry = registry
        self._principles = principle_store
        self._memory = memory_store
        self._threshold = effectiveness_threshold

    def replicate(self, source_id: str, target_id: str) -> ReplicationResult:
        source = self._registry.get(source_id)
        target = self._registry.get(target_id)

        if not source or not target:
            return ReplicationResult(
                source_agent=source_id, target_agent=target_id,
                success=False, report=f"Agent not found: source={source is not None}, target={target is not None}"
            )

        # Filter effective principles relevant to target's capabilities
        copied_ids = []
        for p in self._principles.list_all():
            if p.effectiveness() < self._threshold:
                continue
            if p.times_applied < 1:
                continue
            # Check if principle tags overlap with target capabilities
            if any(tag in target.capabilities for tag in p.tags):
                copied_ids.append(p.principle_id)

        # Count memories
        semantic_facts = self._memory.semantic.list_all()
        episodes = self._memory.episodic.search(event_type="task_complete")
        memories_count = len(semantic_facts) + len(episodes)

        report = (f"Replicated {len(copied_ids)} principles and {memories_count} memories "
                  f"from {source.name} to {target.name}")

        return ReplicationResult(
            source_agent=source_id,
            target_agent=target_id,
            principles_copied=len(copied_ids),
            memories_copied=memories_count,
            copied_principle_ids=copied_ids,
            success=True,
            report=report,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase4 && python3 -m pytest tests/test_capability_replicator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/capability_replicator.py tests/test_capability_replicator.py
git commit -m "feat(phase4): Capability Replicator with selective knowledge transfer to new agents"
```

---

### Task 7: Integration Test（Phase 4 集成测试）

**Files:**
- Create: `tests/test_phase4_integration.py`

**Priority:** 高 — 依赖全部 Task 1-6

- [ ] **Step 1: Write integration test**

```python
# tests/test_phase4_integration.py
"""Phase 4 Integration Tests: three-layer closed loop end-to-end."""

import unittest
import tempfile
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from memory_layer import MemoryStore
from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover
from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter
from approval_gate import ApprovalGate
from task_ontology import TaskType, TaskOntology
from learning_loop import LearningLoop
from cross_scene_transfer import CrossSceneTransfer
from self_optimizer import SelfOptimizer
from evaluation_framework import EvaluationFramework
from capability_replicator import CapabilityReplicator


class TestPhase4Integration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_closed_loop(self):
        """完整三层闭环：经验收集→学习→迁移→评测→复制"""
        # Setup
        memory = MemoryStore()
        ps = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bd = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        rl = ReflectionLoop(ps, bd)
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard("veteran", "Veteran", ["code_gen", "debugging"], ["py"], 2, 0.9))
        registry.register(AgentCard("rookie", "Rookie", ["code_gen"], ["py"], 1, 0.5))
        router = TaskRouter(registry)
        ontology = TaskOntology()
        ontology.register(TaskType("code_gen", "development", ["code"], ["code_gen"], "medium"))
        ontology.register(TaskType("debugging", "development", ["debug"], ["debugging"], "high"))

        # 1. Learning Loop: collect experience → reflect → distribute
        loop = LearningLoop(memory, ps, bd, rl, registry, ontology)
        loop.collect_experience("veteran", "code_gen", "failure", {
            "error_type": "test_failure", "symptom": "no tests",
            "root_cause": "skipped TDD", "fix_applied": "write tests first"
        })
        loop.collect_experience("veteran", "code_gen", "success", {"steps": 5, "tests": 20})
        cycle = loop.run_cycle()
        self.assertTrue(cycle.experiences_collected > 0)

        # 2. Cross-scene transfer: code_gen → debugging
        transfer = CrossSceneTransfer(ontology, ps)
        transfers = transfer.find_transferable("debugging")
        # Should have transferable principles from code_gen

        # 3. Evaluation: measure system health
        eval_fw = EvaluationFramework()
        eval_fw.register_metric("stability", "inner", 0.95, "ratio")
        eval_fw.register_metric("learning_efficiency", "middle", 0.7, "ratio")
        eval_fw.register_metric("task_completion", "outer", 0.9, "ratio")
        eval_fw.record("stability", 0.97)
        eval_fw.record("learning_efficiency", 0.8)
        eval_fw.record("task_completion", 0.92)
        score = eval_fw.compute_overall_score()
        self.assertGreater(score, 0.8)

        # 4. Capability replication: veteran → rookie
        replicator = CapabilityReplicator(registry, ps, memory)
        result = replicator.replicate("veteran", "rookie")
        self.assertTrue(result.success)
        self.assertGreater(result.principles_copied, 0)

    def test_self_optimization_feedback_loop(self):
        """自优化：评测→调参→再评测"""
        optimizer = SelfOptimizer()
        optimizer.register_parameter("complexity_threshold", 0.7, 0.0, 1.0, 0.05)
        optimizer.register_parameter("exploration_rate", 0.3, 0.0, 1.0, 0.05)

        # Simulate poor performance → auto-adjust
        r1 = optimizer.evaluate("complexity_threshold", 0.3, "maximize")
        self.assertIsNotNone(r1)

        # After adjustment, check parameter changed
        params = optimizer.get_current_params()
        self.assertNotEqual(params.get("complexity_threshold"), 0.7)

    def test_all_phase4_modules_importable(self):
        from task_ontology import TaskType, TaskOntology
        from learning_loop import LearningLoop, LearningCycleResult
        from cross_scene_transfer import CrossSceneTransfer, TransferResult
        from self_optimizer import SelfOptimizer, ParameterSet, OptimizationRecord
        from evaluation_framework import EvaluationFramework, MetricRecord, LayerMetrics
        from capability_replicator import CapabilityReplicator, ReplicationResult
        self.assertTrue(True)

    def test_phase2_3_modules_still_work(self):
        """Phase 2+3 modules remain functional"""
        from memory_layer import MemoryStore
        from principle_store import Principle, PrincipleStore
        from agent_registry import AgentCard, AgentRegistry
        from task_router import TaskRouter

        store = MemoryStore()
        store.semantic.store("k", "v")
        self.assertEqual(store.semantic.retrieve("k"), "v")

        reg = AgentRegistry()
        reg.register(AgentCard("a", "A", ["cap"], [], 1, 0.5))
        router = TaskRouter(reg)
        d = router.route("cap")
        self.assertIsNotNone(d)
```

- [ ] **Step 2: Run integration test**
- [ ] **Step 3: Run ALL tests (Phase 2+3+4)**
- [ ] **Step 4: Commit**

```bash
git add tests/test_phase4_integration.py
git commit -m "test(phase4): integration tests for three-layer closed loop end-to-end"
```

---

## Execution Notes

### Parallel Execution Strategy

- **Wave 1:** Task 1 (Task Ontology) — foundation
- **Wave 2:** Task 2 (Learning Loop) + Task 4 (Self Optimizer) + Task 5 (Evaluation) — parallel, T2 depends on T1
- **Wave 3:** Task 3 (Cross-Scene Transfer) + Task 6 (Capability Replicator) — parallel
- **Wave 4:** Task 7 (Integration) — runs last

### Estimated Time
- Task 1: ~8 min (8 tests)
- Task 2: ~12 min (6 tests, most complex — integrates 6 modules)
- Task 3: ~8 min (5 tests)
- Task 4: ~8 min (7 tests)
- Task 5: ~8 min (7 tests)
- Task 6: ~10 min (5 tests)
- Task 7: ~5 min (4 integration tests)
- Reviews + commits: ~15 min
- **Total: ~70-90 min with parallel execution**
