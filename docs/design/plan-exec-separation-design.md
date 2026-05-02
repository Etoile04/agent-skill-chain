# 规划-执行分离：间接经验传递架构设计

> 基于 Skill-SD 论文核心发现：经验直接注入会破坏探索能力（Sokoban 51.6% → 20.3%），需通过间接传递内化为策略偏好。

**创建日期**: 2026-05-02
**状态**: 设计阶段
**关联**: PRD `06-prd-draft.md`, 技术建议 `05-technical-implementation-openclaw.md`

---

## 1. 架构总览（ASCII）

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户 / 触发器                              │
│                    "完成 XXX 任务"                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     复杂度评估层                                  │
│              (判断是否需要规划-执行分离)                            │
│                                                                  │
│  简单任务 (< 3步, 无已知陷阱)  ──────→  直接执行 (退化模式)         │
│  复杂任务 (≥ 3步 或 有相关错误记录) ──→  进入分离架构              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 复杂任务
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Planning Agent (带经验)                         │
│                                                                  │
│  输入:                                                           │
│    ├── 任务描述 (task prompt)                                    │
│    ├── memory_search 结果 (相关错误、成功案例、procedures)         │
│    ├── skill-cards/ 匹配的经验 (when_to_use, common_failures)    │
│    └── .learnings/ERRORS.md 中的相关条目                          │
│                                                                  │
│  输出: StepPlan (JSON)                                           │
│    ├── steps: [{id, goal, strategy_hint, risk_notes, verify}]    │
│    ├── overall_approach: "策略偏好描述"                           │
│    └── fallback_triggers: [什么情况需要回退到规划层]               │
│                                                                  │
│  ⚠️ 输出约束:                                                    │
│    - strategy_hint 是「这类问题的一般解法思路」                    │
│    - 不是「执行这个具体命令」                                     │
│    - risk_notes 标注已知陷阱但不给具体规避指令                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ StepPlan
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Step Dispatcher                                │
│                                                                  │
│  遍历 StepPlan.steps，逐个 spawn Execution Agent                 │
│  每步完成后:                                                      │
│    ├── 成功 → 更新 SESSION-STATE.md, 进入下一步                  │
│    ├── 失败但可重试 → 回到 Planning Agent (携带错误上下文)         │
│    └── 触发 fallback_trigger → 回到 Planning Agent               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 每步
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Execution Agent (纯 prompt)                       │
│                                                                  │
│  输入:                                                           │
│    ├── step.goal: "这一步要达成什么"                              │
│    ├── step.strategy_hint: "这类问题的思路"                      │
│    ├── step.verify: "完成标准"                                   │
│    └── 必要的最小上下文 (文件路径、已有代码片段等)                 │
│                                                                  │
│  ❌ 绝对不包含:                                                   │
│    - memory_search 的原始结果                                     │
│    - ERRORS.md / LEARNINGS.md 的内容                              │
│    - 具体的历史命令/动作                                          │
│    - "上次用 XX 方法成功了" 这样的记忆                            │
│                                                                  │
│  输出: StepResult                                                │
│    ├── status: success | failed | blocked                        │
│    ├── artifacts: [产出的文件/变更]                               │
│    ├── evidence: "为什么认为完成了"                               │
│    └── error_context: (失败时) 错误描述 + 已尝试的方法             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Learning Writeback                              │
│                                                                  │
│  任务完成后自动:                                                  │
│    ├── 抽取 success/failure episode → .learnings/                 │
│    ├── 更新 skill-cards/ 中的 common_failures                    │
│    └── 记录到 memory/YYYY-MM-DD.md                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 接口定义

### 2.1 Planning Agent

#### 输入: PlanningInput

```typescript
interface PlanningInput {
  // 原始任务
  task: {
    description: string;        // 用户的任务描述
    context?: string;           // 必要的上下文 (如当前文件、项目结构)
    constraints?: string[];     // 显式约束
  };

  // 经验检索结果 — 仅 Planning Agent 可见
  experience: {
    relatedErrors: ErrorPattern[];      // 来自 .learnings/ERRORS.md
    relatedProcedures: Procedure[];     // 来自 skill-cards/ 
    similarCases: Episode[];            // 来自 memory_search
    activeWarnings: string[];           // 当前活跃的风险提示
  };

  // 已完成的步骤 (非首次规划时)
  completedSteps?: StepResult[];
}
```

#### 输出: StepPlan

```typescript
interface StepPlan {
  // 整体策略偏好 — 不是具体动作
  overall_approach: string;
  // 例: "这类多文件重构任务通常先建立类型定义，再逐文件替换，
  //      每步后运行类型检查确认无回归"

  steps: Step[];

  // 什么情况需要回到规划层
  fallback_triggers: string[];
  // 例: "类型检查报错超过5处", "发现依赖关系与预期不符"
}

interface Step {
  id: string;
  goal: string;                // 这一步要达成什么
                               // 例: "将 UserService 的认证逻辑抽取到独立模块"

  strategy_hint: string;       // 策略偏好 — 不是具体指令
                               // 例: "这类抽取通常先建新模块骨架，再迁移调用方"

  risk_notes?: string;         // 已知风险标注
                               // 例: "这个项目循环依赖敏感，注意 import 顺序"

  verify: string;              // 完成标准
                               // 例: "相关测试全部通过，无新增 lint error"

  tools_hint?: string[];       // 可用的工具提示 (可选)
                               // 例: ["exec", "read", "edit"]
}
```

### 2.2 Execution Agent

#### 输入: ExecutionInput

```typescript
interface ExecutionInput {
  step: {
    id: string;
    goal: string;              // 从 StepPlan 直接传递
    strategy_hint: string;     // 从 StepPlan 直接传递
    verify: string;            // 从 StepPlan 直接传递
  };

  // 最小必要上下文 — 不含任何经验
  context: {
    workingDirectory: string;
    relevantFiles?: string[];  // 相关文件路径 (不含内容, Agent 自行读取)
    previousStepArtifacts?: string[];  // 上一步产物的描述
  };
}
```

#### 输出: StepResult

```typescript
interface StepResult {
  stepId: string;
  status: "success" | "failed" | "blocked";

  // 成功时
  artifacts?: string[];        // 产出了什么 (文件路径、变更描述)
  evidence?: string;           // 验证证据 (如测试输出)

  // 失败时
  error?: {
    message: string;
    attempts: string[];        // 尝试了什么方法
    hypothesis: string;        // 失败原因假设
  };

  // 规划层建议 (Execution Agent 可选反馈)
  planningSuggestion?: string;
}
```

### 2.3 经验检索层

经验检索层 **仅在规划阶段** 被调用，且检索结果 **只传递给 Planning Agent**。

#### 检索策略

| 维度 | 内容 | 来源 | 粒度 |
|------|------|------|------|
| 错误模式 | 已知陷阱 & 预防规则 | `.learnings/ERRORS.md` | 按 tag/category 匹配 |
| 过程知识 | 任务类型的标准做法 | `skill-cards/*.md` | 按 when_to_use 匹配 |
| 案例经验 | 相似任务的执行记录 | `memory_search` | 语义相似度 top-5 |
| 活跃风险 | 当前 session 上下文 | `SESSION-STATE.md` | 全量 |

#### 检索时机

```
任务开始 → 触发检索 (一次性, 全量)
   │
   ├── 步骤间规划 → 增量检索 (仅新增相关错误)
   │
   └── 回退触发 → 全量重新检索 (情境可能变化)
```

#### 输出格式 (→ Planning Agent)

检索结果经过 **摘要化处理**，不是原始内容直接注入：

```typescript
interface ExperienceSummary {
  // 不是 "ERR-20260225-001: 并发数4→API限流，改为2"
  // 而是 "API 限流风险: 高并发场景建议控制并发数"
  errorPatterns: Array<{
    pattern: string;           // 错误模式摘要
    relevance: "high" | "medium";
  }>;

  // 不是具体的历史执行记录
  // 而是通用的策略提示
  proceduralHints: Array<{
    taskType: string;          // 任务类型
    approach: string;          // 推荐思路
    caveats: string[];         // 注意事项
  }>;
}
```

---

## 3. 关键约束

### C1: 执行层 prompt 中零经验检索结果

**硬性规则**: Execution Agent 的 prompt 中不允许出现任何来自 memory_search、.learnings/、skill-cards/ 的原始内容。

**检查机制**: Step Dispatcher 在构造 ExecutionInput 时，执行 schema 校验，拒绝包含经验字段的情况。

```yaml
# Execution prompt 的禁止模式
forbidden_patterns:
  - "上次.*成功了"
  - "ERR-\\d{8}"
  - "根据.*经验"
  - "之前.*踩过坑"
  - ".learnings/"
  - "common_failures"
```

### C2: 规划层输出是策略偏好，非具体动作

**判断标准**: 如果 StepPlan 中的 strategy_hint 可以直接复制粘贴为 shell 命令或代码片段，说明粒度过细。

**正确示例**:
- ✅ "这类重构通常先建接口，再逐个实现迁移"
- ✅ "配置文件通常在项目根目录，注意区分 dev/prod"
- ✅ "这类 API 有分页限制，大数据量需要分批"

**错误示例**:
- ❌ "运行 `mv src/old.ts src/new.ts`"
- ❌ "在 package.json 的 dependencies 中添加 lodash@4.17.21"
- ❌ "使用 sed -i 's/old/new/g' file.txt"

### C3: 与现有 subagent spawn 机制兼容

基于 `sessions_spawn` 实现，不引入新原语：

```yaml
# Planning Agent
sessions_spawn:
  runtime: subagent
  context: isolated
  task: |
    你是 Planning Agent。根据任务描述和经验参考，
    输出 StepPlan JSON。
  # 经验通过 task 字段注入 Planning Agent

# Execution Agent (每步)
sessions_spawn:
  runtime: subagent
  context: isolated
  task: |
    你是 Execution Agent。根据 step goal 和 strategy_hint，
    自主探索并完成任务。输出 StepResult JSON。
  # 无任何经验注入
```

---

## 4. 与现有系统的集成点

### 4.1 AGENTS.md 集成

在 AGENTS.md 的 `## Every Session` 段落中添加规划-执行分离规则：

```markdown
## 任务执行模式

### 复杂度评估
每接到一个任务，先评估：
- 步骤数 ≥ 3？→ 复杂任务
- .learnings/ 中有相关错误记录？→ 复杂任务
- skill-cards/ 中有匹配的 common_failures？→ 复杂任务
- 以上都不满足 → 简单任务，直接执行

### 规划-执行分离 (复杂任务)
1. 进入规划模式，检索经验
2. 生成 StepPlan (策略偏好，非具体动作)
3. 逐步 spawn Execution Agent (纯 prompt，无经验)
4. 收集结果，必要时回退到规划层
5. 任务完成后触发 Learning Writeback

### 硬性约束
- Execution Agent 的 prompt 中不得包含任何经验检索结果
- strategy_hint 必须是策略偏好，不得是具体命令
```

### 4.2 SESSION-STATE.md 配合

SESSION-STATE.md 增加任务状态跟踪字段：

```markdown
## 任务状态 (复杂任务)

### 当前任务
- task: "描述..."
- mode: planning | executing | completed
- currentStepId: "step-3"
- overallApproach: "策略偏好描述"

### 步骤进度
- [x] step-1: 完成 - 产出 artifact-1
- [x] step-2: 完成 - 产出 artifact-2  
- [ ] step-3: 执行中
- [ ] step-4: 待执行

### 回退记录
- step-2 曾触发回退，原因: ...
- 重新规划后策略调整: ...
```

### 4.3 skill-cards/ 作为经验源

Skill 卡片新增规划元数据字段：

```yaml
# skill-cards/某个技能.md 的扩展结构
metadata:
  name: "feishu-api-integration"
  when_to_use: ["飞书API调用", "多维表格操作", "日历集成"]
  when_not_to_use: ["纯前端任务", "无飞书依赖"]
  
  # 规划层专用 — Execution Agent 不可见
  planning_hints:
    common_failures:
      - pattern: "token 过期"
        hint: "飞书 API 需要处理 token 刷新"
      - pattern: "分页遗漏"
        hint: "飞书列表 API 通常需要分页遍历"
    typical_approach: "先确认权限和 token，再构建请求，最后处理响应格式"
    caveats:
      - "飞书 API 限流: 每秒 50 次"
      - "app_token 和 table_id 的区别"
```

---

## 5. 回退策略：何时退化为直接执行

### 5.1 退化条件

以下情况 **不需要** 规划-执行分离，直接执行即可：

| 条件 | 判断依据 | 示例 |
|------|---------|------|
| 简单单步任务 | 预估步骤 < 3，无已知陷阱 | "读一下这个文件" |
| 无经验可参考 | memory_search 返回空 + 无相关 error | "新建一个空项目" |
| 高确定性操作 | 产出完全确定，无探索空间 | "运行 git status" |
| 紧急/时间敏感 | 用户标记紧急 | "立刻重启 gateway" |
| 格式化/模板化 | 按固定模板执行 | "按 TEMPLATE.md 格式记录" |

### 5.2 退化决策流程

```
收到任务
  │
  ├─ 紧急标记? ────────────→ 直接执行
  │
  ├─ 预估步骤 < 3?
  │   ├─ 有相关错误记录? ──→ 分离模式
  │   └─ 无 ──────────────→ 直接执行
  │
  ├─ 预估步骤 ≥ 3? ────────→ 分离模式
  │
  └─ 不确定? ──────────────→ 先直接执行，如果遇到阻塞再升级为分离模式
```

### 5.3 退化实现

退化模式不需要额外代码 — 它就是当前的默认行为。分离模式是叠加的增强。

```yaml
# 退化 = 当前行为 (不改变)
# 分离 = 新增模式 (通过 AGENTS.md 规则触发)
```

---

## 6. 实施计划

### Phase 1: 基础分离框架 (1-2 天)

**目标**: 实现最小的规划-执行分离闭环。

**具体步骤**:

1. **定义 StepPlan schema**
   - 在 workspace 中创建 `schemas/step-plan.json`
   - 定义 Step、StepPlan、StepResult 的 JSON Schema

2. **编写 Planning Agent prompt 模板**
   - 创建 `templates/planning-agent.md`
   - 包含任务描述 + 经验注入的占位符
   - 输出格式要求为 StepPlan JSON

3. **编写 Execution Agent prompt 模板**
   - 创建 `templates/execution-agent.md`
   - 仅包含 step goal + strategy_hint + verify
   - 输出格式要求为 StepResult JSON

4. **编写 Step Dispatcher 脚本**
   - 创建 `scripts/step-dispatcher.md` (流程文档)
   - 用自然语言描述调度逻辑
   - 后续可自动化

5. **AGENTS.md 更新**
   - 添加复杂度评估规则
   - 添加规划-执行分离流程描述

6. **测试**
   - 用一个已知复杂任务 (如 "重构 memory 系统的存储层") 测试流程
   - 验证 Execution Agent prompt 中确实无经验内容

**交付物**:
- `schemas/step-plan.json`
- `templates/planning-agent.md`
- `templates/execution-agent.md`
- 更新后的 `AGENTS.md`

### Phase 2: 经验管道强化 (2-3 天)

**目标**: 打通经验检索 → 摘要化 → 规划层注入的完整管道。

**具体步骤**:

1. **Skill-cards 扩展**
   - 为现有 skill-cards 添加 `planning_hints` 字段
   - 优先处理高频使用场景的错误模式

2. **经验摘要化处理**
   - 编写经验摘要模板
   - 将 `.learnings/ERRORS.md` 的原始条目转化为策略偏好格式
   - 确保 "具体错误" → "一般模式" 的转换质量

3. **SESSION-STATE.md 扩展**
   - 添加任务状态跟踪字段
   - 记录步骤进度和回退历史

4. **回退机制实现**
   - 定义 fallback_trigger 的匹配规则
   - 实现失败 → 重新规划的自动流程

5. **Learning Writeback 自动化**
   - 任务完成后自动抽取 episode
   - 更新 .learnings/ 和 memory/

**交付物**:
- 扩展后的 skill-cards
- 经验摘要化模板
- 自动 Learning Writeback 流程

### Phase 3: 智能化与自优化 (3-5 天)

**目标**: 让系统从自身的规划-执行历史中学习优化。

**具体步骤**:

1. **规划质量追踪**
   - 记录每个 StepPlan 的执行成功率
   - 追踪回退率和回退原因
   - 建立规划 → 执行的反馈回路

2. **策略偏好自动调优**
   - 分析哪些 strategy_hint 实际上导致了更好的执行结果
   - 自动更新 planning_hints 中的提示

3. **复杂度评估校准**
   - 收集实际执行数据
   - 调整 "简单/复杂" 的判断阈值
   - 减少不必要的分离开销

4. **跨任务经验迁移**
   - 识别不同任务间的共同模式
   - 在规划层实现模式匹配和策略复用

5. **元认知层**
   - Planning Agent 反思自身规划质量
   - Execution Agent 反馈执行中的发现
   - 形成双向改进循环

**交付物**:
- 规划质量追踪仪表板
- 自动调优机制
- 元认知反馈循环

---

## 附录 A: Skill-SD 核心教训映射

| Skill-SD 发现 | 本架构对应 |
|--------------|-----------|
| 直接注入破坏探索 (51.6% → 20.3%) | Execution Agent 禁止接收经验 (约束 C1) |
| 间接蒸馏有效 (62.5%) | 经验通过 strategy_hint 间接传递 |
| 动态 Teacher 同步 | Planning Agent 每次重新检索经验 |
| UCB 技能检索平衡探索-利用 | 复杂度评估层的退化机制 |
| (e_success, e_mistake, e_workflow) | ExperienceSummary 的三维度结构 |

## 附录 B: 与现有系统概念映射

| PRD 概念 | 本架构对应 |
|---------|-----------|
| Task State Object | SESSION-STATE.md 的任务状态字段 |
| Verification Hook | Step.verify 字段 + Execution Agent 的 evidence 输出 |
| Skill Metadata + Trigger | skill-cards 的 planning_hints 扩展 |
| Learning Writeback Pipeline | Phase 2 的 Learning Writeback 自动化 |
| Error Pattern Library | .learnings/ERRORS.md + ExperienceSummary.errorPatterns |
| Global Position Tracker | StepPlan 步骤进度 + SESSION-STATE.md |

## 附录 C: 反模式清单

以下模式在本架构中被视为反模式，应避免：

1. **经验泄漏**: Execution Agent prompt 中出现 memory_search 结果
2. **过度具体**: strategy_hint 包含可直接执行的代码/命令
3. **强制分离**: 简单任务也走规划-执行分离（浪费资源）
4. **冻结规划**: StepPlan 生成后不允许修改（应支持回退重规划）
5. **经验堆积**: 向 Planning Agent 注入过多低相关经验（噪声干扰）
6. **跳过验证**: Execution Agent 完成后不做 verify 检查就进入下一步
