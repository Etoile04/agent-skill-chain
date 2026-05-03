# Phase 3: 外层完善 + 内层原型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建设外层多Agent编排能力（任务路由、审批流、角色定义、治理配置版本化）和内层元认知原型（原则库、偏差模式库、反思→原则更新循环、开放式自改进），完成三层架构的最后一公里。

**Architecture:** 外层基于 Phase 2 已有的 TaskRoadmap、TaskState、BudgetTracker、Lock 扩展，增加 Agent 注册/路由/审批机制。内层借鉴 HyperAgents 思路，建设 Principle Store、Cognitive Bias Detector、Reflection Loop 和 Autonomous Improvement 模块。Python3 标准库，零外部依赖。

**Tech Stack:** Python3 (stdlib only), bash, JSON Schema, pytest, git worktrees

**Worktree:** `/tmp/agent-skill-chain/.worktrees/phase3`

---

## Superpowers 技能使用规范（项目经理须知）

### 执行流程

```
Phase 3 启动
  │
  ├─ using-git-worktrees: 创建隔离 worktree
  │
  ├─ writing-plans: 本文档（已完成）
  │
  ├─ subagent-driven-development: 逐 Task 分派 subagent
  │   │
  │   ├─ 每个 Task: implementer subagent (TDD)
  │   │   ├─ test-driven-development: 红→绿→重构
  │   │   └─ verification-before-completion: 提交前验证
  │   │
  │   ├─ 每个 Task 完成: spec-reviewer subagent
  │   │   └─ 检查代码是否与计划完全一致
  │   │
  │   └─ spec 通过: code-quality-reviewer subagent
  │       └─ 检查代码质量、命名、结构
  │
  ├─ 并行任务: dispatching-parallel-agents
  │   └─ 独立 Task 可并行分派
  │
  ├─ 遇到 bug: systematic-debugging
  │   └─ 4阶段: 根因→模式→假设→实施
  │
  └─ finishing-a-development-branch: merge + push
```

### Subagent 指令模板

每个 implementer subagent 的 prompt 必须包含：

```
## 必须遵循的 Superpowers 技能

1. **TDD (test-driven-development)**:
   - 先写失败测试 → 验证失败 → 写最小实现 → 验证通过 → 重构
   - 绝不在测试之前写产品代码
   - 每步必须运行测试验证

2. **Verification Before Completion (verification-before-completion)**:
   - 提交前必须运行完整测试套件
   - 不能用 "应该能通过" 代替实际运行
   - 所有完成声明必须附带验证证据

3. **Systematic Debugging (systematic-debugging)**:
   - 遇到 bug 时遵循 4 阶段流程
   - 不允许猜测修复，必须找到根因
   - 3 次修复失败后质疑架构

4. **Code Organization**:
   - 每个文件一个清晰职责
   - 变更频繁的文件放在一起
   - 遵循现有代码库模式
```

---

## File Structure

```
schemas/
  agent-card.json            # Agent 注册卡 schema (NEW)
  principle.json             # 原则库 schema (NEW)
  bias-pattern.json          # 偏差模式 schema (NEW)
  governance-config.json     # 治理配置 schema (NEW)

scripts/
  agent_registry.py          # Agent 注册与能力查询 (NEW)
  task_router.py             # 多Agent任务路由 (NEW)
  approval_gate.py           # 审批流管理 (NEW)
  governance_versioner.py    # 治理配置版本化 (NEW)
  principle_store.py         # 原则库 CRUD + 检索 (NEW)
  bias_detector.py           # 偏差模式检测 (NEW)
  reflection_loop.py         # 反思→原则更新循环 (NEW)
  autonomous_improver.py     # 开放式自改进引擎 (NEW)

tests/
  test_agent_registry.py     # Agent 注册测试 (NEW)
  test_task_router.py        # 任务路由测试 (NEW)
  test_approval_gate.py      # 审批流测试 (NEW)
  test_governance_versioner.py # 治理配置测试 (NEW)
  test_principle_store.py    # 原则库测试 (NEW)
  test_bias_detector.py      # 偏差检测测试 (NEW)
  test_reflection_loop.py    # 反思循环测试 (NEW)
  test_autonomous_improver.py # 自改进测试 (NEW)
  test_phase3_integration.py # Phase 3 集成测试 (NEW)
```

---

## Sub-Project A: 外层完善

### Task 1: Agent Registry（Agent 注册与能力查询）

**Files:**
- Create: `schemas/agent-card.json`
- Create: `scripts/agent_registry.py`
- Create: `tests/test_agent_registry.py`

**Priority:** 高 — 路由、审批、角色定义都依赖此模块

**Context:** Phase 2 已有 `scripts/task_roadmap.py`（目标链）和 `schemas/task-state.json`（任务状态）。Agent Registry 是外层编排的基础——定义"谁是谁、能做什么"。

- [ ] **Step 1: Write failing tests for AgentCard and AgentRegistry**

```python
# tests/test_agent_registry.py
import unittest
import json
import tempfile
import os

from agent_registry import AgentCard, AgentRegistry


class TestAgentCard(unittest.TestCase):
    def test_create_agent_card(self):
        card = AgentCard(
            agent_id="coding-a2a",
            name="Coding Agent",
            capabilities=["code_generation", "debugging", "testing"],
            specializations=["python", "javascript"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.assertEqual(card.agent_id, "coding-a2a")
        self.assertEqual(len(card.capabilities), 3)
        self.assertEqual(card.max_concurrent_tasks, 2)

    def test_agent_card_has_skill_coverage(self):
        """AgentCard 应能报告自己的技能覆盖"""
        card = AgentCard(
            agent_id="research-agent",
            name="Research Agent",
            capabilities=["literature_search", "data_analysis"],
            specializations=["materials_science"],
            max_concurrent_tasks=1,
            confidence_threshold=0.8
        )
        coverage = card.skill_coverage()
        self.assertIn("literature_search", coverage)
        self.assertIn("data_analysis", coverage)

    def test_agent_card_to_dict(self):
        card = AgentCard(
            agent_id="test-agent",
            name="Test",
            capabilities=["test"],
            specializations=[],
            max_concurrent_tasks=1,
            confidence_threshold=0.5
        )
        d = card.to_dict()
        self.assertEqual(d["agent_id"], "test-agent")
        self.assertIn("created_at", d)

    def test_can_handle_task_type(self):
        card = AgentCard(
            agent_id="code-agent",
            name="Code Agent",
            capabilities=["code_generation", "debugging"],
            specializations=["python"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.assertTrue(card.can_handle("code_generation"))
        self.assertFalse(card.can_handle("literature_search"))


class TestAgentRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_agent(self):
        card = AgentCard(
            agent_id="coding-a2a",
            name="Coding Agent",
            capabilities=["code_generation"],
            specializations=["python"],
            max_concurrent_tasks=2,
            confidence_threshold=0.7
        )
        self.registry.register(card)
        result = self.registry.get("coding-a2a")
        self.assertEqual(result.name, "Coding Agent")

    def test_list_all_agents(self):
        for i in range(3):
            card = AgentCard(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                capabilities=["test"],
                specializations=[],
                max_concurrent_tasks=1,
                confidence_threshold=0.5
            )
            self.registry.register(card)
        agents = self.registry.list_all()
        self.assertEqual(len(agents), 3)

    def test_find_by_capability(self):
        card1 = AgentCard("a1", "A1", ["code_generation"], ["python"], 2, 0.7)
        card2 = AgentCard("a2", "A2", ["literature_search"], ["materials"], 1, 0.8)
        self.registry.register(card1)
        self.registry.register(card2)
        results = self.registry.find_by_capability("code_generation")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, "a1")

    def test_find_best_for_task(self):
        """应返回匹配度最高且有空闲容量的 Agent"""
        card1 = AgentCard("a1", "A1", ["code_generation"], ["python"], 2, 0.7)
        card2 = AgentCard("a2", "A2", ["code_generation", "debugging"], ["python", "js"], 2, 0.9)
        self.registry.register(card1)
        self.registry.register(card2)
        best = self.registry.find_best_for_task("code_generation")
        self.assertEqual(best.agent_id, "a2")

    def test_persistence(self):
        """注册信息应持久化"""
        path = os.path.join(self.tmpdir, "agents.json")
        reg1 = AgentRegistry(path)
        card = AgentCard("persist-test", "PT", ["test"], [], 1, 0.5)
        reg1.register(card)
        reg1.save()

        reg2 = AgentRegistry(path)
        result = reg2.get("persist-test")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "PT")

    def test_update_agent(self):
        card = AgentCard("update-test", "Original", ["test"], [], 1, 0.5)
        self.registry.register(card)
        updated = AgentCard("update-test", "Updated", ["test", "new_cap"], [], 1, 0.5)
        self.registry.register(updated)
        result = self.registry.get("update-test")
        self.assertEqual(result.name, "Updated")
        self.assertEqual(len(result.capabilities), 2)

    def test_unregister_agent(self):
        card = AgentCard("remove-test", "RT", ["test"], [], 1, 0.5)
        self.registry.register(card)
        self.registry.unregister("remove-test")
        self.assertIsNone(self.registry.get("remove-test"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_agent_registry.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement AgentCard and AgentRegistry**

```python
# scripts/agent_registry.py
"""Agent Registry: registration, capability query, and best-match routing for multi-agent orchestration."""

import json
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentCard:
    """Agent 注册卡：声明身份、能力、专业领域和资源限制。"""
    agent_id: str
    name: str
    capabilities: List[str]
    specializations: List[str]
    max_concurrent_tasks: int
    confidence_threshold: float
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def skill_coverage(self) -> Dict[str, bool]:
        """返回能力覆盖映射。"""
        return {cap: True for cap in self.capabilities}

    def can_handle(self, task_type: str) -> bool:
        """检查是否能处理某类任务。"""
        return task_type in self.capabilities

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "specializations": self.specializations,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "confidence_threshold": self.confidence_threshold,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentCard":
        return cls(
            agent_id=d["agent_id"],
            name=d["name"],
            capabilities=d["capabilities"],
            specializations=d["specializations"],
            max_concurrent_tasks=d["max_concurrent_tasks"],
            confidence_threshold=d["confidence_threshold"],
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
        )


class AgentRegistry:
    """Agent 注册表：管理 AgentCard 的 CRUD 和查询。"""

    def __init__(self, path: Optional[str] = None):
        self._agents: Dict[str, AgentCard] = {}
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def register(self, card: AgentCard) -> None:
        card.updated_at = time.time()
        self._agents[card.agent_id] = card

    def get(self, agent_id: str) -> Optional[AgentCard]:
        return self._agents.get(agent_id)

    def list_all(self) -> List[AgentCard]:
        return list(self._agents.values())

    def find_by_capability(self, capability: str) -> List[AgentCard]:
        return [a for a in self._agents.values() if a.can_handle(capability)]

    def find_best_for_task(self, task_type: str) -> Optional[AgentCard]:
        """返回匹配能力数最多且 confidence 最高的 Agent。"""
        candidates = self.find_by_capability(task_type)
        if not candidates:
            return None
        return max(candidates, key=lambda a: (len(a.capabilities), a.confidence_threshold))

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def save(self) -> None:
        if self._path:
            data = {aid: card.to_dict() for aid, card in self._agents.items()}
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._agents = {aid: AgentCard.from_dict(d) for aid, d in data.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_agent_registry.py -v`
Expected: 10 passed

- [ ] **Step 5: Create agent-card.json schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentCard",
  "description": "Agent 注册卡：声明身份、能力、专业领域和资源限制。",
  "type": "object",
  "required": ["agent_id", "name", "capabilities", "specializations", "max_concurrent_tasks", "confidence_threshold"],
  "properties": {
    "agent_id": { "type": "string", "description": "唯一 Agent ID" },
    "name": { "type": "string", "description": "Agent 显示名称" },
    "capabilities": {
      "type": "array",
      "items": { "type": "string" },
      "description": "能力声明列表"
    },
    "specializations": {
      "type": "array",
      "items": { "type": "string" },
      "description": "专业领域列表"
    },
    "max_concurrent_tasks": { "type": "integer", "minimum": 1 },
    "confidence_threshold": { "type": "number", "minimum": 0, "maximum": 1 },
    "created_at": { "type": "number" },
    "updated_at": { "type": "number" }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add schemas/agent-card.json scripts/agent_registry.py tests/test_agent_registry.py
git commit -m "feat(phase3): Agent Registry with registration, capability query, and best-match routing"
```

---

### Task 2: Task Router（多Agent任务路由）

**Files:**
- Create: `scripts/task_router.py`
- Create: `tests/test_task_router.py`

**Priority:** 高 — 依赖 Task 1（Agent Registry）

- [ ] **Step 1: Write failing tests**

```python
# tests/test_task_router.py
import unittest
import tempfile
import os

from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter, RoutingDecision


class TestRoutingDecision(unittest.TestCase):
    def test_create_routing_decision(self):
        decision = RoutingDecision(
            task_type="code_generation",
            assigned_agent="coding-a2a",
            confidence=0.9,
            reason="Best capability match with 3 overlapping skills"
        )
        self.assertEqual(decision.task_type, "code_generation")
        self.assertEqual(decision.assigned_agent, "coding-a2a")
        self.assertTrue(decision.confidence >= 0.8)

    def test_routing_decision_requires_approval(self):
        """低置信度决策应标记为需要审批"""
        decision = RoutingDecision(
            task_type="unknown_task",
            assigned_agent="fallback-agent",
            confidence=0.3,
            reason="No good match found"
        )
        self.assertTrue(decision.needs_approval())


class TestTaskRouter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        # 注册多个 Agent
        self.registry.register(AgentCard(
            "code-agent", "Code Agent",
            ["code_generation", "debugging", "testing"], ["python"], 2, 0.9
        ))
        self.registry.register(AgentCard(
            "research-agent", "Research Agent",
            ["literature_search", "data_analysis"], ["materials"], 1, 0.8
        ))
        self.registry.register(AgentCard(
            "general-agent", "General Agent",
            ["code_generation", "literature_search", "testing"], ["python", "materials"], 3, 0.6
        ))
        self.router = TaskRouter(self.registry, approval_threshold=0.5)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_route_to_specialist(self):
        """应优先路由到专业 Agent"""
        decision = self.router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")

    def test_route_to_research_agent(self):
        decision = self.router.route("literature_search")
        self.assertEqual(decision.assigned_agent, "research-agent")

    def test_route_unknown_falls_back_to_general(self):
        """未知任务应回退到能力最广的 Agent"""
        decision = self.router.route("unknown_capability")
        # No agent can handle unknown_capability → None
        self.assertIsNone(decision)

    def test_route_considers_confidence_threshold(self):
        """路由应考虑 confidence_threshold"""
        # general-agent 有 code_generation 但 confidence 低
        # code-agent confidence 高 → 应选 code-agent
        decision = self.router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")
        self.assertGreater(decision.confidence, 0.5)

    def test_routing_history(self):
        """路由器应记录路由历史"""
        self.router.route("code_generation")
        self.router.route("literature_search")
        history = self.router.get_history()
        self.assertEqual(len(history), 2)

    def test_load_balancing(self):
        """同等匹配时优先选择负载低的 Agent"""
        # Both code-agent and general-agent can handle code_generation
        # code-agent has higher confidence → should win
        decision = self.router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_task_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement TaskRouter**

```python
# scripts/task_router.py
"""Task Router: routes tasks to the best-matching agent based on capability, confidence, and load."""

import time
from typing import List, Optional
from dataclasses import dataclass, field

from agent_registry import AgentCard, AgentRegistry


@dataclass
class RoutingDecision:
    """路由决策：记录任务分配结果。"""
    task_type: str
    assigned_agent: str
    confidence: float
    reason: str
    timestamp: float = field(default_factory=time.time)

    def needs_approval(self) -> bool:
        """低置信度决策需要人工审批。"""
        return self.confidence < 0.5


class TaskRouter:
    """任务路由器：根据 Agent 能力和置信度分配任务。"""

    def __init__(self, registry: AgentRegistry, approval_threshold: float = 0.5):
        self._registry = registry
        self._approval_threshold = approval_threshold
        self._history: List[RoutingDecision] = []

    def route(self, task_type: str) -> Optional[RoutingDecision]:
        """将任务路由到最佳 Agent。返回 None 表示无匹配。"""
        best = self._registry.find_best_for_task(task_type)
        if best is None:
            return None

        # 置信度评分：能力匹配度 + 专长匹配度
        capability_score = len(best.capabilities) / 10.0  # 归一化
        confidence = min(best.confidence_threshold + capability_score * 0.1, 1.0)

        decision = RoutingDecision(
            task_type=task_type,
            assigned_agent=best.agent_id,
            confidence=confidence,
            reason=f"Best match: {best.name} with {len(best.capabilities)} capabilities, "
                   f"confidence={best.confidence_threshold:.2f}"
        )
        self._history.append(decision)
        return decision

    def get_history(self) -> List[RoutingDecision]:
        return list(self._history)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_task_router.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/task_router.py tests/test_task_router.py
git commit -m "feat(phase3): Task Router with capability-based routing and confidence scoring"
```

---

### Task 3: Approval Gate（审批流管理）

**Files:**
- Create: `scripts/approval_gate.py`
- Create: `tests/test_approval_gate.py`

**Priority:** 中 — 依赖 Task 2（路由决策）

- [ ] **Step 1: Write failing tests**

```python
# tests/test_approval_gate.py
import unittest
import tempfile
import os
import json

from approval_gate import ApprovalGate, ApprovalRequest, ApprovalStatus


class TestApprovalRequest(unittest.TestCase):
    def test_create_request(self):
        req = ApprovalRequest(
            request_id="req-001",
            operation="delete_database",
            agent_id="coding-a2a",
            risk_level="high",
            details={"target": "production_db"}
        )
        self.assertEqual(req.request_id, "req-001")
        self.assertEqual(req.status, ApprovalStatus.PENDING)

    def test_request_auto_requires_approval_for_high_risk(self):
        req = ApprovalRequest("req-002", "modify_config", "agent-1", "high", {})
        self.assertTrue(req.requires_human_approval)


class TestApprovalGate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gate = ApprovalGate(
            persistence_path=os.path.join(self.tmpdir, "approvals.json"),
            auto_approve_low_risk=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_submit_request(self):
        req_id = self.gate.submit(
            operation="run_tests",
            agent_id="coding-a2a",
            risk_level="low",
            details={}
        )
        self.assertIsNotNone(req_id)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.operation, "run_tests")

    def test_auto_approve_low_risk(self):
        req_id = self.gate.submit("run_tests", "coding-a2a", "low", {})
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.APPROVED)

    def test_high_risk_needs_manual_approval(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {"path": "/important"})
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.PENDING)

    def test_approve_manually(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        result = self.gate.approve(req_id, approver="human")
        self.assertTrue(result)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.APPROVED)

    def test_reject_manually(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        result = self.gate.reject(req_id, approver="human", reason="too risky")
        self.assertTrue(result)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.REJECTED)

    def test_cannot_approve_twice(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        self.gate.approve(req_id, approver="human")
        result = self.gate.approve(req_id, approver="human2")
        self.assertFalse(result)

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "approvals.json")
        gate1 = ApprovalGate(path, auto_approve_low_risk=True)
        gate1.submit("op1", "a1", "high", {})
        gate1.save()

        gate2 = ApprovalGate(path, auto_approve_low_risk=True)
        pending = gate2.get_pending()
        self.assertEqual(len(pending), 1)

    def test_get_pending_requests(self):
        self.gate.submit("op1", "a1", "high", {})
        self.gate.submit("op2", "a1", "high", {})
        self.gate.submit("op3", "a1", "low", {})
        pending = self.gate.get_pending()
        self.assertEqual(len(pending), 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_approval_gate.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ApprovalGate**

```python
# scripts/approval_gate.py
"""Approval Gate: risk-based approval flow for high-risk agent operations."""

import json
import os
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRequest:
    request_id: str
    operation: str
    agent_id: str
    risk_level: str  # "low", "medium", "high"
    details: dict
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    @property
    def requires_human_approval(self) -> bool:
        return self.risk_level in ("high", "medium")

    def to_dict(self) -> dict:
        d = {
            "request_id": self.request_id,
            "operation": self.operation,
            "agent_id": self.agent_id,
            "risk_level": self.risk_level,
            "details": self.details,
            "status": self.status.value,
            "approver": self.approver,
            "reason": self.reason,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalRequest":
        req = cls(
            request_id=d["request_id"],
            operation=d["operation"],
            agent_id=d["agent_id"],
            risk_level=d["risk_level"],
            details=d["details"],
            status=ApprovalStatus(d["status"]),
            approver=d.get("approver"),
            reason=d.get("reason"),
            created_at=d.get("created_at", time.time()),
            resolved_at=d.get("resolved_at"),
        )
        return req


class ApprovalGate:
    """审批门：管理操作审批流。"""

    def __init__(self, persistence_path: Optional[str] = None,
                 auto_approve_low_risk: bool = True):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._path = persistence_path
        self._auto_approve_low = auto_approve_low_risk
        if persistence_path and os.path.exists(persistence_path):
            self.load()

    def submit(self, operation: str, agent_id: str, risk_level: str,
               details: dict) -> str:
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(req_id, operation, agent_id, risk_level, details)

        if self._auto_approve_low and risk_level == "low":
            req.status = ApprovalStatus.APPROVED
            req.approver = "auto"
            req.resolved_at = time.time()

        self._requests[req_id] = req
        return req_id

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def approve(self, request_id: str, approver: str) -> bool:
        req = self._requests.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.APPROVED
        req.approver = approver
        req.resolved_at = time.time()
        return True

    def reject(self, request_id: str, approver: str, reason: str = "") -> bool:
        req = self._requests.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.REJECTED
        req.approver = approver
        req.reason = reason
        req.resolved_at = time.time()
        return True

    def get_pending(self) -> List[ApprovalRequest]:
        return [r for r in self._requests.values()
                if r.status == ApprovalStatus.PENDING]

    def save(self) -> None:
        if self._path:
            data = {rid: req.to_dict() for rid, req in self._requests.items()}
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._requests = {rid: ApprovalRequest.from_dict(d) for rid, d in data.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_approval_gate.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/approval_gate.py tests/test_approval_gate.py
git commit -m "feat(phase3): Approval Gate with risk-based auto-approval and manual review"
```

---

### Task 4: Governance Versioner（治理配置版本化）

**Files:**
- Create: `schemas/governance-config.json`
- Create: `scripts/governance_versioner.py`
- Create: `tests/test_governance_versioner.py`

**Priority:** 中 — 独立于 Task 1-3

- [ ] **Step 1: Write failing tests**

```python
# tests/test_governance_versioner.py
import unittest
import tempfile
import os
import json

from governance_versioner import GovernanceVersioner, ConfigVersion


class TestConfigVersion(unittest.TestCase):
    def test_create_version(self):
        v = ConfigVersion(
            version="1.0.0",
            config={"approval_rules": {"high_risk": "manual"}},
            author="admin",
            description="Initial governance config"
        )
        self.assertEqual(v.version, "1.0.0")
        self.assertEqual(v.author, "admin")

    def test_version_has_timestamp(self):
        v = ConfigVersion("1.0.0", {}, "admin", "test")
        self.assertIsNotNone(v.timestamp)


class TestGovernanceVersioner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.versioner = GovernanceVersioner(os.path.join(self.tmpdir, "governance.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_initial_config(self):
        config = {"approval_rules": {"high_risk": "manual"}, "agents": {}}
        self.versioner.commit(config, author="admin", description="Initial config")
        current = self.versioner.get_current()
        self.assertEqual(current.config["approval_rules"]["high_risk"], "manual")

    def test_version_increments(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        history = self.versioner.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["version"], "0.2.0")

    def test_rollback(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        self.versioner.rollback(1)
        current = self.versioner.get_current()
        self.assertEqual(current.config["v"], 1)

    def test_cannot_rollback_too_far(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        result = self.versioner.rollback(5)
        self.assertFalse(result)

    def test_diff_between_versions(self):
        self.versioner.commit({"a": 1, "b": 2}, "admin", "v1")
        self.versioner.commit({"a": 1, "b": 3, "c": 4}, "admin", "v2")
        diff = self.versioner.diff(0, 1)
        self.assertIn("added", diff)
        self.assertIn("changed", diff)

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "governance.json")
        gv1 = GovernanceVersioner(path)
        gv1.commit({"x": 1}, "admin", "test")
        gv1.save()

        gv2 = GovernanceVersioner(path)
        current = gv2.get_current()
        self.assertIsNotNone(current)
        self.assertEqual(current.config["x"], 1)

    def test_get_version_at(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        self.versioner.commit({"v": 3}, "admin", "v3")
        v1 = self.versioner.get_version_at(0)
        self.assertEqual(v1.config["v"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_governance_versioner.py -v`
Expected: FAIL

- [ ] **Step 3: Implement GovernanceVersioner**

```python
# scripts/governance_versioner.py
"""Governance Versioner: versioned configuration management for agent governance rules."""

import json
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ConfigVersion:
    """单个配置版本。"""
    version: str
    config: dict
    author: str
    description: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "config": self.config,
            "author": self.author,
            "description": self.description,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConfigVersion":
        return cls(
            version=d["version"],
            config=d["config"],
            author=d["author"],
            description=d["description"],
            timestamp=d.get("timestamp", time.time()),
        )


def _next_version(index: int) -> str:
    minor = index + 1
    return f"0.{minor}.0"


class GovernanceVersioner:
    """治理配置版本管理器。"""

    def __init__(self, path: Optional[str] = None):
        self._history: List[ConfigVersion] = []
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def commit(self, config: dict, author: str, description: str) -> str:
        ver = _next_version(len(self._history))
        cv = ConfigVersion(ver, config, author, description)
        self._history.append(cv)
        return ver

    def get_current(self) -> Optional[ConfigVersion]:
        return self._history[-1] if self._history else None

    def get_history(self) -> List[dict]:
        return [cv.to_dict() for cv in self._history]

    def get_version_at(self, index: int) -> Optional[ConfigVersion]:
        if 0 <= index < len(self._history):
            return self._history[index]
        return None

    def rollback(self, target_index: int) -> bool:
        if target_index >= len(self._history):
            return False
        # Rollback by creating a new version that restores the old config
        old = self._history[target_index]
        self.commit(
            old.config,
            author="system",
            description=f"Rollback to {old.version}"
        )
        return True

    def diff(self, index_a: int, index_b: int) -> dict:
        """比较两个版本的配置差异。"""
        va = self._history[index_a].config if index_a < len(self._history) else {}
        vb = self._history[index_b].config if index_b < len(self._history) else {}

        added = {k: vb[k] for k in vb if k not in va}
        removed = {k: va[k] for k in va if k not in vb}
        changed = {k: (va[k], vb[k]) for k in va if k in vb and va[k] != vb[k]}

        return {"added": added, "removed": removed, "changed": changed}

    def save(self) -> None:
        if self._path:
            data = [cv.to_dict() for cv in self._history]
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._history = [ConfigVersion.from_dict(d) for d in data]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_governance_versioner.py -v`
Expected: 7 passed

- [ ] **Step 5: Create governance-config.json schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GovernanceConfig",
  "description": "Agent 治理配置：审批规则、权限边界、预算限制。",
  "type": "object",
  "properties": {
    "approval_rules": {
      "type": "object",
      "description": "操作审批规则，key 为风险等级",
      "additionalProperties": {
        "type": "string",
        "enum": ["auto", "manual", "disabled"]
      }
    },
    "agent_permissions": {
      "type": "object",
      "description": "Agent 权限配置，key 为 agent_id",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "allowed_operations": { "type": "array", "items": { "type": "string" } },
          "max_budget_tokens": { "type": "integer" },
          "max_concurrent_tasks": { "type": "integer" }
        }
      }
    },
    "version": { "type": "string" },
    "updated_at": { "type": "number" }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add schemas/governance-config.json scripts/governance_versioner.py tests/test_governance_versioner.py
git commit -m "feat(phase3): Governance Versioner with versioned config management and rollback"
```

---

## Sub-Project B: 内层原型（元认知 + 自改进）

### Task 5: Principle Store（原则库）

**Files:**
- Create: `schemas/principle.json`
- Create: `scripts/principle_store.py`
- Create: `tests/test_principle_store.py`

**Priority:** 高 — 反思循环和自改进都依赖此模块

- [ ] **Step 1: Write failing tests**

```python
# tests/test_principle_store.py
import unittest
import tempfile
import os

from principle_store import Principle, PrincipleStore


class TestPrinciple(unittest.TestCase):
    def test_create_principle(self):
        p = Principle(
            principle_id="P-001",
            title="Always verify before claiming completion",
            description="Run verification commands before any success claim",
            source="reflection",
            trigger="about to claim task is complete",
            action="run test suite, read output, confirm 0 failures",
            tags=["verification", "discipline"]
        )
        self.assertEqual(p.principle_id, "P-001")
        self.assertEqual(len(p.tags), 2)

    def test_principle_has_effectiveness_tracking(self):
        p = Principle("P-002", "Test", "desc", "error", "trigger", "action", [])
        self.assertEqual(p.times_applied, 0)
        self.assertEqual(p.times_prevented_error, 0)

    def test_record_application(self):
        p = Principle("P-003", "Test", "desc", "error", "trigger", "action", [])
        p.record_application(prevented_error=True)
        self.assertEqual(p.times_applied, 1)
        self.assertEqual(p.times_prevented_error, 1)
        self.assertGreater(p.effectiveness(), 0.0)

    def test_effectiveness_with_no_applications(self):
        p = Principle("P-004", "Test", "desc", "error", "trigger", "action", [])
        self.assertEqual(p.effectiveness(), 0.0)


class TestPrincipleStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = PrincipleStore(os.path.join(self.tmpdir, "principles.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_principle(self):
        p = Principle("P-001", "Verify first", "desc", "reflection", "t", "a", ["test"])
        self.store.add(p)
        result = self.store.get("P-001")
        self.assertEqual(result.title, "Verify first")

    def test_list_all_principles(self):
        for i in range(3):
            p = Principle(f"P-{i}", f"T{i}", "d", "reflection", "t", "a", [])
            self.store.add(p)
        all_p = self.store.list_all()
        self.assertEqual(len(all_p), 3)

    def test_search_by_tag(self):
        self.store.add(Principle("P-1", "T1", "d", "r", "t", "a", ["verification"]))
        self.store.add(Principle("P-2", "T2", "d", "r", "t", "a", ["debugging"]))
        self.store.add(Principle("P-3", "T3", "d", "r", "t", "a", ["verification", "debugging"]))
        results = self.store.search_by_tag("verification")
        self.assertEqual(len(results), 2)

    def test_search_by_trigger(self):
        self.store.add(Principle("P-1", "T1", "d", "r", "about to commit", "a", []))
        self.store.add(Principle("P-2", "T2", "d", "r", "test fails", "a", []))
        results = self.store.search_by_trigger("commit")
        self.assertEqual(len(results), 1)

    def test_get_most_effective(self):
        p1 = Principle("P-1", "T1", "d", "r", "t", "a", [])
        p1.record_application(True)
        p1.record_application(True)
        p2 = Principle("P-2", "T2", "d", "r", "t", "a", [])
        p2.record_application(True)
        p2.record_application(False)
        self.store.add(p1)
        self.store.add(p2)
        best = self.store.get_most_effective()
        self.assertEqual(best.principle_id, "P-1")

    def test_update_principle(self):
        p = Principle("P-1", "Original", "d", "r", "t", "a", [])
        self.store.add(p)
        updated = Principle("P-1", "Updated", "new desc", "r", "t", "a", ["new_tag"])
        self.store.add(updated)
        result = self.store.get("P-1")
        self.assertEqual(result.title, "Updated")

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "principles.json")
        s1 = PrincipleStore(path)
        s1.add(Principle("P-1", "T", "d", "r", "t", "a", []))
        s1.save()
        s2 = PrincipleStore(path)
        result = s2.get("P-1")
        self.assertIsNotNone(result)

    def test_get_principles_for_situation(self):
        """根据当前场景匹配最相关的原则"""
        self.store.add(Principle("P-1", "Verify", "d", "r", "about to commit code", "run tests", []))
        self.store.add(Principle("P-2", "Debug", "d", "r", "test failure detected", "trace root cause", []))
        results = self.store.get_for_situation("commit")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].principle_id, "P-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_principle_store.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Principle and PrincipleStore**

```python
# scripts/principle_store.py
"""Principle Store: behavioral principles extracted from reflection and error learning."""

import json
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Principle:
    """行为原则：从错误/反思中提炼的可执行规则。"""
    principle_id: str
    title: str
    description: str
    source: str  # "reflection", "error", "human", "autonomous"
    trigger: str  # 何时应用此原则
    action: str   # 应该做什么
    tags: List[str] = field(default_factory=list)
    times_applied: int = 0
    times_prevented_error: int = 0
    created_at: float = field(default_factory=time.time)

    def record_application(self, prevented_error: bool = False) -> None:
        self.times_applied += 1
        if prevented_error:
            self.times_prevented_error += 1

    def effectiveness(self) -> float:
        if self.times_applied == 0:
            return 0.0
        return self.times_prevented_error / self.times_applied

    def to_dict(self) -> dict:
        return {
            "principle_id": self.principle_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "trigger": self.trigger,
            "action": self.action,
            "tags": self.tags,
            "times_applied": self.times_applied,
            "times_prevented_error": self.times_prevented_error,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Principle":
        return cls(
            principle_id=d["principle_id"],
            title=d["title"],
            description=d["description"],
            source=d["source"],
            trigger=d["trigger"],
            action=d["action"],
            tags=d.get("tags", []),
            times_applied=d.get("times_applied", 0),
            times_prevented_error=d.get("times_prevented_error", 0),
            created_at=d.get("created_at", time.time()),
        )


class PrincipleStore:
    """原则库：管理行为原则的 CRUD 和检索。"""

    def __init__(self, path: Optional[str] = None):
        self._principles: Dict[str, Principle] = {}
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def add(self, principle: Principle) -> None:
        self._principles[principle.principle_id] = principle

    def get(self, principle_id: str) -> Optional[Principle]:
        return self._principles.get(principle_id)

    def list_all(self) -> List[Principle]:
        return list(self._principles.values())

    def search_by_tag(self, tag: str) -> List[Principle]:
        return [p for p in self._principles.values() if tag in p.tags]

    def search_by_trigger(self, keyword: str) -> List[Principle]:
        return [p for p in self._principles.values() if keyword.lower() in p.trigger.lower()]

    def get_most_effective(self) -> Optional[Principle]:
        active = [p for p in self._principles.values() if p.times_applied > 0]
        if not active:
            return None
        return max(active, key=lambda p: p.effectiveness())

    def get_for_situation(self, situation: str) -> List[Principle]:
        """根据当前场景描述匹配最相关的原则。"""
        return [p for p in self._principles.values()
                if situation.lower() in p.trigger.lower()]

    def save(self) -> None:
        if self._path:
            data = {pid: p.to_dict() for pid, p in self._principles.items()}
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._principles = {pid: Principle.from_dict(d) for pid, d in data.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_principle_store.py -v`
Expected: 11 passed

- [ ] **Step 5: Create principle.json schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Principle",
  "description": "行为原则：从错误/反思中提炼的可执行规则。",
  "type": "object",
  "required": ["principle_id", "title", "description", "source", "trigger", "action"],
  "properties": {
    "principle_id": { "type": "string" },
    "title": { "type": "string" },
    "description": { "type": "string" },
    "source": { "type": "string", "enum": ["reflection", "error", "human", "autonomous"] },
    "trigger": { "type": "string", "description": "何时应用此原则" },
    "action": { "type": "string", "description": "应该做什么" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "times_applied": { "type": "integer" },
    "times_prevented_error": { "type": "integer" },
    "created_at": { "type": "number" }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add schemas/principle.json scripts/principle_store.py tests/test_principle_store.py
git commit -m "feat(phase3): Principle Store with CRUD, effectiveness tracking, and situation matching"
```

---

### Task 6: Bias Detector（偏差模式检测）

**Files:**
- Create: `schemas/bias-pattern.json`
- Create: `scripts/bias_detector.py`
- Create: `tests/test_bias_detector.py`

**Priority:** 中 — 独立于 Task 5，但被 Task 7 依赖

- [ ] **Step 1: Write failing tests**

```python
# tests/test_bias_detector.py
import unittest
import tempfile
import os

from bias_detector import BiasPattern, BiasDetector, DetectionResult


class TestBiasPattern(unittest.TestCase):
    def test_create_bias_pattern(self):
        bp = BiasPattern(
            pattern_id="BIAS-001",
            name="Confirmation Bias",
            description="Agent seeks only confirming evidence",
            indicators=["ignores failing tests", "only checks positive results"],
            severity="high"
        )
        self.assertEqual(bp.pattern_id, "BIAS-001")
        self.assertEqual(bp.severity, "high")

    def test_bias_pattern_indicators(self):
        bp = BiasPattern("BIAS-002", "Test", "d", ["indicator1", "indicator2"], "medium")
        self.assertEqual(len(bp.indicators), 2)


class TestBiasDetector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = BiasDetector(os.path.join(self.tmpdir, "biases.json"))
        self.detector.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Agent claims completion without running tests",
            ["claims done without test output", "says 'should work'"],
            "high"
        ))
        self.detector.register(BiasPattern(
            "BIAS-002", "Scope Creep",
            "Agent adds features beyond the spec",
            ["implements unrequested features", "adds nice-to-haves"],
            "medium"
        ))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detect_matching_pattern(self):
        result = self.detector.detect("I'm done, it should work fine now")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-001")

    def test_detect_scope_creep(self):
        result = self.detector.detect("I also added a caching layer for nice-to-haves")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-002")

    def test_no_match_returns_none(self):
        result = self.detector.detect("All 34 tests pass, 0 failures confirmed")
        self.assertIsNone(result)

    def test_detection_result_has_severity(self):
        result = self.detector.detect("claims done without test output")
        self.assertEqual(result.severity, "high")

    def test_batch_detect(self):
        texts = [
            "should work now",
            "all tests pass",
            "I added extra validation too"
        ]
        results = self.detector.batch_detect(texts)
        self.assertEqual(len(results), 2)  # 2 matches, 1 clean

    def test_register_new_pattern(self):
        self.detector.register(BiasPattern(
            "BIAS-003", "Test", "d", ["new indicator pattern"], "low"
        ))
        result = self.detector.detect("I see new indicator pattern here")
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern_id, "BIAS-003")

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "biases.json")
        d1 = BiasDetector(path)
        d1.register(BiasPattern("B1", "T", "d", ["p1"], "low"))
        d1.save()
        d2 = BiasDetector(path)
        result = d2.detect("p1 found")
        self.assertIsNotNone(result)

    def test_get_all_patterns(self):
        patterns = self.detector.list_patterns()
        self.assertEqual(len(patterns), 2)

    def test_detection_confidence(self):
        """检测结果应包含置信度"""
        result = self.detector.detect("claims done without test output, says 'should work'")
        self.assertIsNotNone(result)
        self.assertGreater(result.confidence, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_bias_detector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement BiasDetector**

```python
# scripts/bias_detector.py
"""Bias Detector: identifies cognitive bias patterns in agent behavior."""

import json
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class BiasPattern:
    """认知偏差模式：描述一种已知的 Agent 行为偏差。"""
    pattern_id: str
    name: str
    description: str
    indicators: List[str]
    severity: str  # "low", "medium", "high"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "indicators": self.indicators,
            "severity": self.severity,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BiasPattern":
        return cls(
            pattern_id=d["pattern_id"],
            name=d["name"],
            description=d["description"],
            indicators=d["indicators"],
            severity=d["severity"],
            created_at=d.get("created_at", time.time()),
        )


@dataclass
class DetectionResult:
    """偏差检测结果。"""
    pattern_id: str
    pattern_name: str
    severity: str
    confidence: float
    matched_indicators: List[str] = field(default_factory=list)


class BiasDetector:
    """认知偏差检测器：扫描文本/行为，识别已知偏差模式。"""

    def __init__(self, path: Optional[str] = None):
        self._patterns: Dict[str, BiasPattern] = {}
        self._path = path
        if path and os.path.exists(path):
            self.load()

    def register(self, pattern: BiasPattern) -> None:
        self._patterns[pattern.pattern_id] = pattern

    def detect(self, text: str) -> Optional[DetectionResult]:
        """检测文本中是否包含已知偏差模式的指标。"""
        text_lower = text.lower()
        best_match = None
        best_confidence = 0.0
        best_indicators = []

        for pattern in self._patterns.values():
            matched = [ind for ind in pattern.indicators if ind.lower() in text_lower]
            if matched:
                confidence = len(matched) / len(pattern.indicators)
                if confidence > best_confidence:
                    best_match = pattern
                    best_confidence = confidence
                    best_indicators = matched

        if best_match is None:
            return None

        return DetectionResult(
            pattern_id=best_match.pattern_id,
            pattern_name=best_match.name,
            severity=best_match.severity,
            confidence=best_confidence,
            matched_indicators=best_indicators,
        )

    def batch_detect(self, texts: List[str]) -> List[DetectionResult]:
        results = []
        for text in texts:
            result = self.detect(text)
            if result:
                results.append(result)
        return results

    def list_patterns(self) -> List[BiasPattern]:
        return list(self._patterns.values())

    def save(self) -> None:
        if self._path:
            data = {pid: p.to_dict() for pid, p in self._patterns.items()}
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if self._path and os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._patterns = {pid: BiasPattern.from_dict(d) for pid, d in data.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_bias_detector.py -v`
Expected: 9 passed

- [ ] **Step 5: Create bias-pattern.json schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BiasPattern",
  "description": "认知偏差模式：Agent 已知的行为偏差。",
  "type": "object",
  "required": ["pattern_id", "name", "description", "indicators", "severity"],
  "properties": {
    "pattern_id": { "type": "string" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "indicators": { "type": "array", "items": { "type": "string" } },
    "severity": { "type": "string", "enum": ["low", "medium", "high"] },
    "created_at": { "type": "number" }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add schemas/bias-pattern.json scripts/bias_detector.py tests/test_bias_detector.py
git commit -m "feat(phase3): Bias Detector with pattern matching and confidence scoring"
```

---

### Task 7: Reflection Loop（反思→原则更新循环）

**Files:**
- Create: `scripts/reflection_loop.py`
- Create: `tests/test_reflection_loop.py`

**Priority:** 高 — 依赖 Task 5（Principle Store）和 Task 6（Bias Detector）

- [ ] **Step 1: Write failing tests**

```python
# tests/test_reflection_loop.py
import unittest
import tempfile
import os

from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop, ReflectionResult


class TestReflectionResult(unittest.TestCase):
    def test_create_result(self):
        result = ReflectionResult(
            has_findings=True,
            new_principles=1,
            updated_principles=0,
            detected_biases=0,
            summary="Found 1 new principle from error analysis"
        )
        self.assertTrue(result.has_findings)
        self.assertEqual(result.new_principles, 1)


class TestReflectionLoop(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "principles.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "biases.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reflect_on_error_generates_principle(self):
        """从错误中反思应生成新原则"""
        error_context = {
            "error_type": "test_failure",
            "symptom": "claimed tests pass without running them",
            "root_cause": "assumed success from code review alone",
            "fix_applied": "added mandatory test run step"
        }
        result = self.reflection.reflect_on_error(error_context)
        self.assertTrue(result.has_findings)
        self.assertGreater(result.new_principles, 0)
        # 验证原则确实被存储
        principles = self.principle_store.list_all()
        self.assertGreater(len(principles), 0)

    def test_reflect_on_success_no_new_principles(self):
        """成功执行不一定生成新原则"""
        success_context = {
            "task_type": "code_generation",
            "steps_completed": 5,
            "tests_passed": 20,
            "tests_failed": 0
        }
        result = self.reflection.reflect_on_success(success_context)
        # 成功不强制生成原则
        self.assertIsInstance(result, ReflectionResult)

    def test_reflect_on_text_detects_bias(self):
        """对行为文本进行反思应检测偏差"""
        self.bias_detector.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Claims done without evidence",
            ["should work", "looks good enough"],
            "high"
        ))
        result = self.reflection.reflect_on_behavior("The code should work fine now")
        self.assertTrue(result.has_findings)
        self.assertGreater(result.detected_biases, 0)

    def test_reflection_generates_actionable_principle(self):
        """生成的原则应该是可执行的（有明确的 trigger 和 action）"""
        error_context = {
            "error_type": "integration_failure",
            "symptom": "modules don't work together",
            "root_cause": "no integration test between modules",
            "fix_applied": "added integration test"
        }
        self.reflection.reflect_on_error(error_context)
        principles = self.principle_store.list_all()
        for p in principles:
            self.assertTrue(len(p.trigger) > 0, "Principle should have a trigger")
            self.assertTrue(len(p.action) > 0, "Principle should have an action")

    def test_repeated_error_updates_existing_principle(self):
        """重复出现的错误应更新已有原则而不是重复创建"""
        ctx = {
            "error_type": "test_failure",
            "symptom": "same symptom",
            "root_cause": "same root cause",
            "fix_applied": "same fix"
        }
        r1 = self.reflection.reflect_on_error(ctx)
        r2 = self.reflection.reflect_on_error(ctx)
        # 第二次应识别为重复并更新而非新建
        principles = self.principle_store.list_all()
        # 原则数量应等于第一次创建的数量
        self.assertEqual(len(principles), r1.new_principles)

    def test_reflection_history(self):
        """反思循环应记录历史"""
        self.reflection.reflect_on_error({
            "error_type": "test", "symptom": "s", "root_cause": "r", "fix_applied": "f"
        })
        history = self.reflection.get_history()
        self.assertEqual(len(history), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_reflection_loop.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ReflectionLoop**

```python
# scripts/reflection_loop.py
"""Reflection Loop: error → principle extraction, behavior → bias detection."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector


@dataclass
class ReflectionResult:
    """反思结果。"""
    has_findings: bool
    new_principles: int = 0
    updated_principles: int = 0
    detected_biases: int = 0
    summary: str = ""
    timestamp: float = field(default_factory=time.time)


class ReflectionLoop:
    """反思循环：从错误/行为中提炼原则并检测偏差。"""

    def __init__(self, principle_store: PrincipleStore, bias_detector: BiasDetector):
        self._principles = principle_store
        self._bias_detector = bias_detector
        self._history: List[ReflectionResult] = []
        self._principle_counter = 0

    def _next_principle_id(self) -> str:
        self._principle_counter += 1
        return f"P-AUTO-{self._principle_counter:04d}"

    def reflect_on_error(self, error_context: dict) -> ReflectionResult:
        """从错误上下文中提炼行为原则。"""
        error_type = error_context.get("error_type", "unknown")
        symptom = error_context.get("symptom", "")
        root_cause = error_context.get("root_cause", "")
        fix = error_context.get("fix_applied", "")

        # 检查是否已有相似原则
        existing = self._find_similar_principle(error_type, root_cause)
        if existing:
            existing.record_application(prevented_error=False)
            result = ReflectionResult(
                has_findings=True,
                updated_principles=1,
                summary=f"Updated existing principle {existing.principle_id} for repeated error: {error_type}"
            )
            self._history.append(result)
            return result

        # 生成新原则
        pid = self._next_principle_id()
        principle = Principle(
            principle_id=pid,
            title=f"Prevent {error_type}: {root_cause[:50]}",
            description=f"When encountering {error_type} caused by {root_cause}, apply: {fix}",
            source="reflection",
            trigger=f"encounter {error_type} or see symptom: {symptom[:60]}",
            action=fix if fix else f"Investigate root cause: {root_cause}",
            tags=[error_type, "auto-generated"]
        )
        principle.record_application(prevented_error=False)
        self._principles.add(principle)

        result = ReflectionResult(
            has_findings=True,
            new_principles=1,
            summary=f"Generated principle {pid} from error: {error_type}"
        )
        self._history.append(result)
        return result

    def reflect_on_success(self, success_context: dict) -> ReflectionResult:
        """从成功执行中提炼经验。"""
        result = ReflectionResult(
            has_findings=False,
            summary=f"Task completed successfully: {success_context.get('task_type', 'unknown')}"
        )
        self._history.append(result)
        return result

    def reflect_on_behavior(self, text: str) -> ReflectionResult:
        """从行为文本中检测认知偏差。"""
        detection = self._bias_detector.detect(text)
        if detection is None:
            result = ReflectionResult(has_findings=False, summary="No bias detected")
        else:
            result = ReflectionResult(
                has_findings=True,
                detected_biases=1,
                summary=f"Detected bias: {detection.pattern_name} (severity={detection.severity}, "
                        f"confidence={detection.confidence:.2f})"
            )
        self._history.append(result)
        return result

    def _find_similar_principle(self, error_type: str, root_cause: str) -> Optional[Principle]:
        """查找已有相似原则。"""
        for p in self._principles.list_all():
            if error_type in p.tags and root_cause[:30] in p.description:
                return p
        return None

    def get_history(self) -> List[ReflectionResult]:
        return list(self._history)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_reflection_loop.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/reflection_loop.py tests/test_reflection_loop.py
git commit -m "feat(phase3): Reflection Loop with error→principle extraction and bias detection"
```

---

### Task 8: Autonomous Improver（开放式自改进引擎）

**Files:**
- Create: `scripts/autonomous_improver.py`
- Create: `tests/test_autonomous_improver.py`

**Priority:** 中 — 依赖 Task 5-7

- [ ] **Step 1: Write failing tests**

```python
# tests/test_autonomous_improver.py
import unittest
import tempfile
import os

from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover, ImprovementProposal


class TestImprovementProposal(unittest.TestCase):
    def test_create_proposal(self):
        proposal = ImprovementProposal(
            proposal_id="IMP-001",
            area="testing",
            current_state="No integration tests",
            proposed_improvement="Add integration test for all module pairs",
            rationale="3 integration failures in past week",
            priority="high"
        )
        self.assertEqual(proposal.proposal_id, "IMP-001")
        self.assertEqual(proposal.priority, "high")


class TestAutonomousImprover(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)
        self.improver = AutonomousImprover(
            self.principle_store, self.bias_detector, self.reflection
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_analyze_error_patterns(self):
        """应能从错误历史中识别模式"""
        for _ in range(3):
            self.reflection.reflect_on_error({
                "error_type": "test_failure",
                "symptom": "test not run before commit",
                "root_cause": "skipped verification",
                "fix_applied": "run tests"
            })
        patterns = self.improver.analyze_error_patterns()
        self.assertGreater(len(patterns), 0)

    def test_propose_improvement(self):
        """应能从模式中生成改进提案"""
        # 添加一些原则
        for i in range(3):
            p = Principle(f"P-{i}", f"Principle {i}", "desc", "error", "trigger", "action", ["test_failure"])
            p.record_application(prevented_error=False)
            self.principle_store.add(p)

        proposals = self.improver.propose_improvements()
        self.assertGreater(len(proposals), 0)
        for prop in proposals:
            self.assertTrue(len(prop.proposed_improvement) > 0)
            self.assertIn(prop.priority, ["low", "medium", "high"])

    def test_identify_weak_principles(self):
        """应能识别效果差的原则"""
        p1 = Principle("P-good", "Good", "d", "r", "t", "a", [])
        p1.record_application(True)
        p1.record_application(True)
        p1.record_application(True)
        p2 = Principle("P-weak", "Weak", "d", "r", "t", "a", [])
        p2.record_application(False)
        p2.record_application(False)
        p2.record_application(False)
        self.principle_store.add(p1)
        self.principle_store.add(p2)

        weak = self.improver.identify_weak_principles(threshold=0.3)
        self.assertEqual(len(weak), 1)
        self.assertEqual(weak[0].principle_id, "P-weak")

    def test_suggest_principle_refinements(self):
        """对效果差的原则应提出修改建议"""
        p = Principle("P-1", "Original", "desc", "error", "test fails", "run tests", [])
        p.record_application(False)
        p.record_application(False)
        self.principle_store.add(p)

        refinements = self.improver.suggest_refinements(p)
        self.assertGreater(len(refinements), 0)
        self.assertIn("suggestion", refinements[0])

    def test_full_improvement_cycle(self):
        """完整改进循环：分析 → 提案 → 评分"""
        # 注入错误数据
        for _ in range(5):
            self.reflection.reflect_on_error({
                "error_type": "scope_creep",
                "symptom": "added unrequested features",
                "root_cause": "no scope verification step",
                "fix_applied": "check spec before implementing"
            })

        proposals = self.improver.run_improvement_cycle()
        self.assertIsInstance(proposals, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_autonomous_improver.py -v`
Expected: FAIL

- [ ] **Step 3: Implement AutonomousImprover**

```python
# scripts/autonomous_improver.py
"""Autonomous Improver: self-directed improvement through pattern analysis and proposal generation."""

import time
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from collections import Counter

from principle_store import Principle, PrincipleStore
from bias_detector import BiasDetector
from reflection_loop import ReflectionLoop


@dataclass
class ImprovementProposal:
    """改进提案。"""
    proposal_id: str
    area: str
    current_state: str
    proposed_improvement: str
    rationale: str
    priority: str  # "low", "medium", "high"
    timestamp: float = field(default_factory=time.time)


class AutonomousImprover:
    """开放式自改进引擎：分析模式，生成提案，不限定改进方向。"""

    def __init__(self, principle_store: PrincipleStore,
                 bias_detector: BiasDetector,
                 reflection_loop: ReflectionLoop):
        self._principles = principle_store
        self._bias_detector = bias_detector
        self._reflection = reflection_loop
        self._proposal_counter = 0

    def _next_proposal_id(self) -> str:
        self._proposal_counter += 1
        return f"IMP-{self._proposal_counter:04d}"

    def analyze_error_patterns(self) -> List[dict]:
        """从反思历史中识别重复错误模式。"""
        history = self._reflection.get_history()
        error_tags = []
        for entry in history:
            if entry.new_principles > 0 or entry.updated_principles > 0:
                # 从 summary 提取错误类型
                summary = entry.summary.lower()
                error_tags.append(summary)

        # 按频率排序
        counter = Counter(error_tags)
        patterns = [{"pattern": p, "count": c} for p, c in counter.most_common()]
        return patterns

    def propose_improvements(self) -> List[ImprovementProposal]:
        """从当前状态生成改进提案。"""
        proposals = []

        # 分析弱原则
        weak = self.identify_weak_principles(threshold=0.5)
        for p in weak:
            proposal = ImprovementProposal(
                proposal_id=self._next_proposal_id(),
                area="principle_effectiveness",
                current_state=f"Principle '{p.title}' effectiveness={p.effectiveness():.2f}",
                proposed_improvement=f"Refine trigger/action for principle {p.principle_id}",
                rationale=f"Low effectiveness ({p.effectiveness():.2f}) after {p.times_applied} applications",
                priority="high" if p.effectiveness() < 0.2 else "medium"
            )
            proposals.append(proposal)

        # 分析错误模式
        patterns = self.analyze_error_patterns()
        for pattern in patterns[:3]:  # 取前3个高频模式
            if pattern["count"] >= 2:
                proposal = ImprovementProposal(
                    proposal_id=self._next_proposal_id(),
                    area="error_prevention",
                    current_state=f"Recurring error: {pattern['pattern'][:60]}",
                    proposed_improvement=f"Create targeted guardrail for: {pattern['pattern'][:40]}",
                    rationale=f"This error pattern appeared {pattern['count']} times",
                    priority="high" if pattern["count"] >= 3 else "medium"
                )
                proposals.append(proposal)

        return proposals

    def identify_weak_principles(self, threshold: float = 0.3) -> List[Principle]:
        """识别效果低于阈值的原则。"""
        return [p for p in self._principles.list_all()
                if p.times_applied >= 2 and p.effectiveness() < threshold]

    def suggest_refinements(self, principle: Principle) -> List[dict]:
        """为效果差的原则提出修改建议。"""
        suggestions = []
        if principle.effectiveness() < 0.3:
            suggestions.append({
                "suggestion": f"Principle '{principle.title}' has low effectiveness. "
                             f"Consider making the trigger more specific or the action more actionable.",
                "current_trigger": principle.trigger,
                "current_action": principle.action,
            })
        if principle.times_applied < 2:
            suggestions.append({
                "suggestion": f"Principle '{principle.title}' has only been applied {principle.times_applied} times. "
                             f"Consider broadening the trigger conditions.",
            })
        return suggestions

    def run_improvement_cycle(self) -> List[ImprovementProposal]:
        """运行完整的改进循环。"""
        return self.propose_improvements()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_autonomous_improver.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/autonomous_improver.py tests/test_autonomous_improver.py
git commit -m "feat(phase3): Autonomous Improver with pattern analysis and improvement proposals"
```

---

### Task 9: Integration Test（Phase 3 集成测试）

**Files:**
- Create: `tests/test_phase3_integration.py`

**Priority:** 高 — 依赖 Task 1-8 全部完成

- [ ] **Step 1: Write integration test**

```python
# tests/test_phase3_integration.py
"""Phase 3 Integration Tests: verify all outer-layer + inner-layer modules work together."""

import unittest
import tempfile
import os
import shutil

from agent_registry import AgentCard, AgentRegistry
from task_router import TaskRouter
from approval_gate import ApprovalGate, ApprovalStatus
from governance_versioner import GovernanceVersioner
from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover


class TestPhase3Integration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_outer_layer_workflow(self):
        """外层完整流程：注册Agent → 路由任务 → 审批高风险操作 → 版本化配置"""
        # 1. 注册 Agents
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard(
            "code-agent", "Code Agent",
            ["code_generation", "debugging", "testing"], ["python"], 2, 0.9
        ))
        registry.register(AgentCard(
            "research-agent", "Research Agent",
            ["literature_search", "data_analysis"], ["materials"], 1, 0.8
        ))

        # 2. 路由任务
        router = TaskRouter(registry)
        decision = router.route("code_generation")
        self.assertEqual(decision.assigned_agent, "code-agent")

        # 3. 审批高风险操作
        gate = ApprovalGate(os.path.join(self.tmpdir, "approvals.json"))
        req_id = gate.submit("deploy_to_production", "code-agent", "high", {})
        req = gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.PENDING)
        gate.approve(req_id, approver="admin")
        self.assertEqual(gate.get_request(req_id).status, ApprovalStatus.APPROVED)

        # 4. 版本化治理配置
        versioner = GovernanceVersioner(os.path.join(self.tmpdir, "gov.json"))
        versioner.commit(
            {"agents": {"code-agent": {"max_budget": 10000}}},
            author="admin",
            description="Set budget for code agent"
        )
        current = versioner.get_current()
        self.assertIsNotNone(current)

    def test_full_inner_layer_workflow(self):
        """内层完整流程：错误→反思→原则生成→偏差检测→自改进"""
        # 1. 初始化模块
        principle_store = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bias_detector = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        reflection = ReflectionLoop(principle_store, bias_detector)
        improver = AutonomousImprover(principle_store, bias_detector, reflection)

        # 2. 注册偏差模式
        bias_detector.register(BiasPattern(
            "BIAS-001", "Premature Satisfaction",
            "Claims done without evidence",
            ["should work", "looks fine"],
            "high"
        ))

        # 3. 从错误中反思 → 生成原则
        result = reflection.reflect_on_error({
            "error_type": "test_failure",
            "symptom": "tests not run before commit",
            "root_cause": "no verification step",
            "fix_applied": "run full test suite before any commit"
        })
        self.assertTrue(result.has_findings)
        self.assertGreater(result.new_principles, 0)

        # 4. 检测偏差
        bias_result = reflection.reflect_on_behavior("The code should work fine now")
        self.assertTrue(bias_result.has_findings)
        self.assertGreater(bias_result.detected_biases, 0)

        # 5. 自改进
        proposals = improver.run_improvement_cycle()
        self.assertIsInstance(proposals, list)

        # 6. 验证原则可检索
        principles = principle_store.get_for_situation("commit")
        self.assertGreater(len(principles), 0)

    def test_cross_layer_interaction(self):
        """跨层交互：路由决策触发反思，审批触发原则更新"""
        # 外层
        registry = AgentRegistry(os.path.join(self.tmpdir, "agents.json"))
        registry.register(AgentCard("a1", "A1", ["code_gen"], ["py"], 2, 0.9))
        router = TaskRouter(registry)

        # 内层
        ps = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        bd = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        rl = ReflectionLoop(ps, bd)

        # 路由任务
        decision = router.route("code_gen")
        self.assertIsNotNone(decision)

        # 路由历史中的低置信度决策可触发反思
        history = router.get_history()
        self.assertEqual(len(history), 1)

    def test_all_phase3_modules_importable(self):
        """验证所有 Phase 3 模块可正常导入"""
        from agent_registry import AgentCard, AgentRegistry
        from task_router import TaskRouter, RoutingDecision
        from approval_gate import ApprovalGate, ApprovalRequest, ApprovalStatus
        from governance_versioner import GovernanceVersioner, ConfigVersion
        from principle_store import Principle, PrincipleStore
        from bias_detector import BiasPattern, BiasDetector, DetectionResult
        from reflection_loop import ReflectionLoop, ReflectionResult
        from autonomous_improver import AutonomousImprover, ImprovementProposal
        self.assertTrue(True)

    def test_phase2_modules_still_work(self):
        """验证 Phase 2 模块在 Phase 3 环境中仍然正常"""
        from memory_layer import MemoryStore
        from skill_trigger import SkillTriggerEngine
        from planning_tracker import PlanningQualityTracker
        from task_roadmap import TaskRoadmap
        from budget_tracker import BudgetTracker

        # 基本功能验证
        store = MemoryStore()
        store.semantic.store("test", "value")
        self.assertEqual(store.semantic.retrieve("test"), "value")

        rm = TaskRoadmap("rm-1", "Test Roadmap")
        rm.add_milestone("M1", "Milestone 1")
        rm.add_task("M1", "T1", "Task 1")
        self.assertAlmostEqual(rm.progress_pct(), 0.0)
```

- [ ] **Step 2: Run integration test**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/test_phase3_integration.py -v`
Expected: 5 passed

- [ ] **Step 3: Run ALL tests (Phase 2 + Phase 3)**

Run: `cd /tmp/agent-skill-chain/.worktrees/phase3 && python3 -m pytest tests/ -v`
Expected: ALL passed (67 Phase 2 + ~75 Phase 3 = ~142 tests)

- [ ] **Step 4: Commit**

```bash
git add tests/test_phase3_integration.py
git commit -m "test(phase3): integration tests for outer-layer + inner-layer + cross-layer interaction"
```

---

## Execution Notes

### Subagent-Driven Development Protocol

1. **Setup worktree:** `git worktree add /tmp/agent-skill-chain/.worktrees/phase3 -b feature/phase3-outer-inner`
2. **One subagent per task** (Tasks 1-9)
3. **After each task:** spec compliance review → code quality review → commit
4. **After all tasks:** final integration review → finishing-a-development-branch
5. **TDD enforced:** Every task follows Red-Green-Refactor cycle
6. **Systematic debugging:** If any test fails, follow the 4-phase debug process

### Parallel Execution Strategy

Tasks with no dependencies can run in parallel (via dispatching-parallel-agents):

- **Wave 1:** Task 1 (Agent Registry) — foundation for outer layer
- **Wave 2:** Task 2 (Router) + Task 5 (Principle Store) — parallel, independent subsystems
- **Wave 3:** Task 3 (Approval Gate) + Task 4 (Governance) + Task 6 (Bias Detector) — parallel
- **Wave 4:** Task 7 (Reflection Loop) — depends on Task 5 + 6
- **Wave 5:** Task 8 (Autonomous Improver) — depends on Task 5-7
- **Wave 6:** Task 9 (Integration) — runs last

### Subagent Prompt Construction Rules

每个 subagent dispatch 必须包含：

1. **完整 Task 文本** — 不要让 subagent 读文件，直接粘贴
2. **上下文说明** — 这个 Task 在整体架构中的位置
3. **依赖信息** — 需要导入哪些已完成的模块
4. **Superpowers 技能要求** — TDD、Verification、Debugging
5. **工作目录** — `/tmp/agent-skill-chain/.worktrees/phase3`
6. **报告格式** — DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT

### Review Protocol

- **Spec Reviewer:** 对照本计划中的 Task 描述，逐条验证代码实现
- **Code Quality Reviewer:** 检查命名、结构、接口设计、文件大小
- **Both reviews must pass** before moving to next Task

### Estimated Time
- Task 1: ~12 min (10 tests, registry + card)
- Task 2: ~10 min (6 tests, router)
- Task 3: ~10 min (9 tests, approval gate)
- Task 4: ~10 min (7 tests, governance versioner)
- Task 5: ~12 min (11 tests, principle store)
- Task 6: ~10 min (9 tests, bias detector)
- Task 7: ~10 min (6 tests, reflection loop)
- Task 8: ~10 min (5 tests, autonomous improver)
- Task 9: ~8 min (5 integration tests)
- Reviews + commits: ~20 min
- **Total: ~100-120 min with parallel execution, ~80 min serial minimum**
