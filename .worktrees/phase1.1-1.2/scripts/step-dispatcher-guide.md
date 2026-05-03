# Step Dispatcher 流程指南

> 规划-执行分离架构 · Step Dispatcher
> 描述完整的调度流程，供主 Agent（主会话）手动或半自动执行。

---

## 1. 完整调度流程

### 1.1 复杂度评估

收到任务后，先评估是否需要进入分离模式：

```
收到任务
  │
  ├─ 用户标记紧急？ ──────────→ 直接执行，不走分离模式
  │
  ├─ 预估步骤数 < 3？
  │   ├─ .learnings/ 有相关错误？ ──→ 分离模式
  │   └─ 无相关错误 ──────────────→ 直接执行
  │
  ├─ 预估步骤数 ≥ 3？ ──────────→ 分离模式
  │
  └─ 不确定？ ─────────────────→ 先直接执行，遇阻再升级
```

评估输出一个 `ComplexityAssessment` JSON。

### 1.2 经验检索（仅规划阶段）

进入分离模式后，进行一次性经验检索：

1. **`.learnings/ERRORS.md`**：按 tag/category 搜索相关错误模式
2. **`memory_search`**：语义搜索相似任务的历史记录（top-5）
3. **`skill-cards/`**：匹配 when_to_use 字段，提取 common_failures

检索结果经过 **摘要化处理**，转为 `ExperienceSummary` 格式：
- 原始错误 → 错误模式摘要
- 历史记录 → 策略提示
- 具体案例 → 通用注意事项

### 1.3 规划（Planning Agent）

将任务描述 + ExperienceSummary 填入 `templates/planning-agent.md` 模板，spawn Planning Agent：

```
sessions_spawn(
  runtime: "subagent",
  context: "isolated",
  task: 填充后的 planning-agent.md 内容
)
```

等待 Planning Agent 返回 `StepPlan` JSON。

**校验 StepPlan**：
- steps 不为空
- 每个 step 的 strategy_hint 不包含可执行命令（正则检查）
- fallback_triggers 不为空
- verify 标准可客观判断

### 1.4 逐步执行（Execution Agent × N）

遍历 StepPlan.steps，逐个 spawn Execution Agent：

```
对于每个 step:
  1. 构造 ExecutionInput
     - step.id, step.goal, step.strategy_hint, step.verify
     - context: 工作目录 + 相关文件路径 + 上一步 artifacts

  2. 填入 templates/execution-agent.md 模板

  3. sessions_spawn(
       runtime: "subagent",
       context: "isolated",
       task: 填充后的 execution-agent.md 内容
     )

  4. 等待返回 StepResult

  5. 处理结果：
     ├─ success → 更新 SESSION-STATE.md，继续下一步
     ├─ failed  → 检查是否触发 fallback_trigger
     │           ├─ 触发 → 回到规划层（携带错误上下文）
     │           └─ 未触发 → 重试一次，仍失败则回退到规划层
     └─ blocked → 回退到规划层，携带 planningSuggestion
```

**关键**：Execution Agent 的 prompt 中 **不得** 包含任何经验检索结果。Dispatcher 在构造 prompt 时负责过滤。

### 1.5 收集结果

所有步骤完成后：

1. 汇总所有 StepResult
2. 检查整体任务是否完成
3. 运行最终验证（如有）
4. 更新 SESSION-STATE.md 标记任务完成

### 1.6 Learning Writeback

任务完成后自动触发：

1. 抽取 success/failure episode → `.learnings/`
2. 如有新的错误模式，记录到 `.learnings/ERRORS.md`
3. 记录到 `memory/YYYY-MM-DD.md`

---

## 2. 何时回退到规划层

以下情况需要回到 Planning Agent 重新规划：

| 情况 | 触发条件 | 携带信息 |
|------|---------|---------|
| Execution Agent 失败 | StepResult.status = "failed" | error.message + error.attempts + error.hypothesis |
| 触发 fallback_trigger | StepResult 中的信息匹配任一 fallback_trigger | 触发的 trigger + 当前上下文 |
| Execution Agent 被阻塞 | StepResult.status = "blocked" | planningSuggestion |
| 连续两步失败 | 同一 Planning 周期内 ≥ 2 步失败 | 所有失败步骤的 error 信息 |
| 发现前提错误 | 执行中发现规划的前提假设不成立 | 具体哪些前提不成立 + 实际情况 |

回退时，重新进行经验检索（全量），生成新的 StepPlan。新计划可以：
- 调整剩余步骤
- 修改 strategy_hint
- 添加新的 fallback_triggers
- 标记已完成的步骤（completedSteps）

---

## 3. 如何在 AGENTS.md 中触发

在主会话的 AGENTS.md 中添加以下规则即可启用：

```markdown
## 任务执行模式

### 复杂度评估
每接到一个任务，先评估：
- 步骤数 ≥ 3？→ 复杂任务
- .learnings/ 中有相关错误记录？→ 复杂任务
- 以上都不满足 → 简单任务，直接执行

### 规划-执行分离 (复杂任务)
1. 进入规划模式，检索经验
2. 使用 templates/planning-agent.md 生成 StepPlan
3. 逐步使用 templates/execution-agent.md spawn Execution Agent
4. 收集结果，必要时回退到规划层
5. 任务完成后触发 Learning Writeback

### 硬性约束
- Execution Agent 的 prompt 中不得包含任何经验检索结果
- strategy_hint 必须是策略偏好，不得是具体命令
```

触发条件：AGENTS.md 规则 + 主 Agent 的判断。无需额外配置。

---

## 4. 端到端示例：重构 memory 系统

**任务描述**："重构 memory 系统的存储层，从文件系统迁移到 LanceDB，保持向后兼容。"

### Step 1: 复杂度评估

```json
{
  "isComplex": true,
  "reason": "预估 5+ 步骤，涉及多文件修改和数据迁移，.learnings/ 中有相关错误（LanceDB 相关）",
  "estimatedSteps": 5,
  "hasRelevantErrors": true
}
```

### Step 2: 经验检索

- `.learnings/ERRORS.md`: 找到 LanceDB 相关错误 3 条（jiti 缓存、插件路径、并发写入）
- `memory_search`: 找到 2 个相似案例（memory 插件迁移、存储层重构）
- `skill-cards/`: 无直接匹配

摘要化：
```json
{
  "errorPatterns": [
    { "pattern": "LanceDB 插件代码变更后需清 jiti 缓存", "relevance": "high" },
    { "pattern": "插件路径容易混淆 memory-lancedb 和 memory-lancedb-pro", "relevance": "medium" },
    { "pattern": "LanceDB 并发写入可能导致锁冲突", "relevance": "medium" }
  ],
  "proceduralHints": [
    {
      "taskType": "存储层迁移",
      "approach": "先建新的存储抽象层接口，再实现 LanceDB 后端，最后做数据迁移脚本",
      "caveats": ["保持旧接口可用直到迁移完成", "数据迁移需处理格式差异"]
    }
  ]
}
```

### Step 3: Planning Agent 输出

```json
{
  "overall_approach": "存储层迁移通常遵循接口抽象 → 新后端实现 → 数据迁移 → 切换 → 清理的路径，每步保持系统可运行",
  "steps": [
    {
      "id": "step-define-interface",
      "goal": "定义存储抽象层接口，将现有文件系统实现适配到该接口",
      "strategy_hint": "这类重构通常先定义统一接口，再让旧实现适配，确保不破坏现有功能",
      "verify": "现有所有存储相关测试通过，接口类型定义完整"
    },
    {
      "id": "step-implement-lancedb",
      "goal": "实现 LanceDB 存储后端",
      "strategy_hint": "新后端实现通常先写核心 CRUD，再处理边缘情况如并发和错误恢复",
      "risk_notes": "LanceDB 插件代码变更后 jiti 缓存可能导致加载旧代码",
      "verify": "LanceDB 后端通过单元测试，包括并发写入场景"
    },
    {
      "id": "step-migration-script",
      "goal": "编写数据迁移脚本，将文件系统数据导入 LanceDB",
      "strategy_hint": "数据迁移脚本通常需要处理格式转换、增量同步和回滚能力",
      "verify": "迁移脚本能完整迁移测试数据，迁移前后数据一致性验证通过"
    },
    {
      "id": "step-switch-backend",
      "goal": "切换默认存储后端为 LanceDB，保持文件系统作为 fallback",
      "strategy_hint": "这类切换通常通过配置开关实现，确保可快速回退",
      "risk_notes": "切换后首次启动可能触发自动迁移",
      "verify": "配置切换后系统正常启动，读写功能正常"
    },
    {
      "id": "step-cleanup",
      "goal": "清理旧文件系统代码的 fallback 逻辑，更新文档",
      "strategy_hint": "清理通常在确认新系统稳定运行一段时间后进行，先标记 deprecated 再移除",
      "verify": "无残留的文件系统 fallback 代码，README 和 AGENTS.md 已更新"
    }
  ],
  "fallback_triggers": [
    "LanceDB 后端测试失败率 > 30%",
    "数据迁移脚本无法处理现有数据格式",
    "切换后端后现有功能回归测试失败"
  ],
  "complexity_assessment": {
    "isComplex": true,
    "reason": "多步骤重构涉及数据迁移和后端切换",
    "estimatedSteps": 5,
    "hasRelevantErrors": true
  }
}
```

### Step 4: 逐步执行

Dispatcher 依次 spawn 5 个 Execution Agent，每个只收到对应 step 的 goal + strategy_hint + verify + 最小上下文。

**Execution Agent 不知道**：
- LanceDB 的具体错误编号
- jiti 缓存的具体清理命令
- 历史上的迁移案例详情

**Execution Agent 只知道**：
- 这一步要做什么
- 这类问题的一般思路
- 怎么验证完成了

### Step 5: 结果收集 & Writeback

假设 step-2（LanceDB 后端实现）首次失败：
```json
{
  "stepId": "step-implement-lancedb",
  "status": "failed",
  "error": {
    "message": "LanceDB 并发写入测试超时",
    "attempts": ["单线程写入（通过）", "2 并发写入（超时）", "添加重试逻辑（仍超时）"],
    "hypothesis": "可能是 LanceDB 的锁机制与测试环境的 I/O 调度冲突"
  },
  "planningSuggestion": "考虑在测试中模拟并发而非真实并发，或检查 LanceDB 版本兼容性"
}
```

Dispatcher 检查 fallback_triggers → "LanceDB 后端测试失败率 > 30%" 匹配 → 回退到规划层。

Planning Agent 重新规划，可能将 step-2 拆分为 "核心写入" + "并发处理" 两步，并调整 strategy_hint。

---

## 5. 实现状态

| 组件 | 路径 | 状态 |
|------|------|------|
| JSON Schema | `schemas/step-plan.json` | ✅ 已创建 |
| Planning Agent 模板 | `templates/planning-agent.md` | ✅ 已创建 |
| Execution Agent 模板 | `templates/execution-agent.md` | ✅ 已创建 |
| Step Dispatcher 指南 | `scripts/step-dispatcher-guide.md` | ✅ 本文档 |
| AGENTS.md 集成 | 待 Phase 1 完成后手动添加 | ⏳ |
