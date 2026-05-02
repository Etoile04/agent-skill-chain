# 三层架构蓝图：长时复杂任务智能体能力增强系统

> 基于 Skill-SD、HyperAgents、Paperclip 三源整合的架构重设计

**创建日期**: 2026-05-02
**状态**: 蓝图设计
**前置文档**:
- PRD 草案 `06-prd-draft.md`
- 技术改造建议 `05-technical-implementation-openclaw.md`
- 规划-执行分离设计 `notes/projects/plan-exec-separation-design.md`
- Paperclip 项目分析 `wiki-agent-system/wiki/sources/2026-05-02-paperclip-project.md`

---

## 1. 三层架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│ 外层：编排控制面（Paperclip 思路）                                │
│                                                                  │
│ 职责：多 Agent 协调、目标链管理、原子锁、预算治理、审批流        │
│ 粒度：组织级 / 项目级                                            │
│ 核心问题：谁做什么、什么时候做、花多少钱                          │
│                                                                  │
│ 关键抽象：Company → Project → Goal → Issue → Task               │
├─────────────────────────────────────────────────────────────────┤
│ 中层：经验传递（Skill-SD 思路）                                   │
│                                                                  │
│ 职责：间接知识传递、三维技能卡、UCB 检索、经验摘要化              │
│ 粒度：任务类型级 / 技能级                                        │
│ 核心问题：如何让经验从"做过的人"流向"正在做的人"而不破坏探索     │
│                                                                  │
│ 关键抽象：Skill-Card → Strategy Hint → Experience Summary       │
├─────────────────────────────────────────────────────────────────┤
│ 内层：Agent 能力（HyperAgents 思路）                              │
│                                                                  │
│ 职责：元认知自修改、开放式自改进、错误学习、规划-执行分离         │
│ 粒度：单个 Agent / 单次执行                                      │
│ 核心问题：单个 Agent 如何变得更聪明、更稳定、更自主               │
│                                                                  │
│ 关键抽象：StepPlan → Execution → Verification → Reflection      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 每层职责与边界

| 层 | 职责 | 不做什么 | 技术来源 |
|---|---|---|---|
| **外层** | 多 Agent 编排、目标分解、并发控制、预算审计、审批流 | 不关心单个 Agent 怎么执行 | Paperclip |
| **中层** | 经验存储、检索、摘要化、技能卡管理、知识传承 | 不直接执行任务，不编排 Agent | Skill-SD |
| **内层** | 任务执行、规划-执行分离、验证、自反思、错误学习 | 不管理其他 Agent，不关心组织结构 | HyperAgents |

### 1.2 层间依赖关系

```
外层 ──调用──→ 内层（编排 Agent 执行任务）
外层 ──查询──→ 中层（获取组织级经验汇总）
中层 ──注入──→ 内层（间接传递策略偏好，不直接注入经验）
内层 ──回写──→ 中层（执行结果提炼为技能卡）
中层 ──聚合──→ 外层（个体经验升级为组织知识）
```

关键约束：**中层到内层的传递是间接的**（Skill-SD 核心发现）。经验经过摘要化变成策略偏好（strategy_hint），而不是原始记忆直接注入。

---

## 2. PRD 模块重映射

原 PRD 定义了 10 个模块，现在映射到三层架构中：

### 2.1 内层（Agent 能力）

| # | 模块 | 原优先级 | 状态 | 说明 |
|---|------|---------|------|------|
| M1 | 执行约束与验证 Runtime | P0 | 🟡 进行中 | 规划-执行分离设计中已定义 Step.verify、Execution Agent 验证机制。基础版可通过 AGENTS.md 规则 + 模板实现 |
| M2 | 群体错误学习系统 | P0 | 🟡 进行中 | `.learnings/ERRORS.md` + 错误模板已运行。需要：(1) 自动 writeback 管道 (2) 错误模式→guardrail 绑定 |
| M8 | 元认知能力层 | P2 | ⚪ 待启动 | HyperAgents 核心贡献。包括：自反思→原则更新、偏差模式库、二阶优化。Phase 3 原型 |
| M9 | 泛化与跨场景迁移能力 | P2 | ⚪ 待启动 | 任务本体 + 潜在模式库 + 相似场景映射器。Phase 4 |

### 2.2 中层（经验传递）

| # | 模块 | 原优先级 | 状态 | 说明 |
|---|------|---------|------|------|
| M3 | 长期记忆与场景触发系统 | P0 | 🟡 进行中 | memory_search + SESSION-STATE.md + 每日笔记已运行。需要：结构化 recall bundle、触发式记忆加载 |
| M4 | Skill 演化与能力共享网络 | P1 | 🟢 部分完成 | 三维技能卡系统已设计（`skill-cards/` 目录：domains/patterns/workflows），3 张卡已创建。需要：UCB 检索、版本管理、技能触发引擎 |
| M5 | 智能体训练与能力复制体系 | P1 | ⚪ 待启动 | 训练 workspace + golden/failure traces + 能力报告。依赖中层技能卡系统成熟后启动 |

### 2.3 外层（编排控制面）

| # | 模块 | 原优先级 | 状态 | 说明 |
|---|------|---------|------|------|
| M6 | 长时任务状态系统 | P1 | ⚪ 待启动 | 对应 Paperclip 的持久 Agent 状态 + 原子执行锁。需要：Task State Object 一等公民、跨 session 恢复 |
| M7 | 全局意识 / 路径感知系统 | P1 | ⚪ 待启动 | 对应 Paperclip 的目标链执行。需要：Task Roadmap Schema、Global Position Tracker |
| M10 | 评测与闭环优化系统 | P2 | ⚪ 待启动 | 跨层评测：内层（单步验证）→ 中层（技能卡效果）→ 外层（项目目标达成）。Phase 4 |

### 2.4 状态汇总

| 状态 | 数量 | 模块 |
|------|------|------|
| 🟢 部分完成 | 1 | M4 Skill 演化 |
| 🟡 进行中 | 2 | M1 执行验证、M2 错误学习、M3 长期记忆 |
| ⚪ 待启动 | 6 | M5-M10 |
| ❌ 已完成 | 0 | — |

**实际情况**：M3 也在进行中，所以是 3 个进行中、5 个待启动。M1/M2/M3 虽然有基础但都缺少关键子功能。

---

## 3. 层间接口定义

### 3.1 内层→中层：执行结果提炼为技能卡

Agent 执行完一个任务后，产出会被提炼为结构化的经验存入中层。

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Execution Agent    │     │  Learning Writeback  │     │    中层存储          │
│                      │     │      Pipeline        │     │                      │
│  输出: StepResult    │────→│                      │────→│ skill-cards/         │
│  - status            │     │  抽取:               │     │ .learnings/          │
│  - artifacts         │     │  - error pattern     │     │ memory/              │
│  - evidence          │     │  - procedure delta   │     │                      │
│  - error_context     │     │  - success episode   │     │                      │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**提炼规则**：

| 原始产出 | 提炼产物 | 存储位置 | 格式 |
|---------|---------|---------|------|
| 成功执行的完整 trace | success episode | `memory/YYYY-MM-DD.md` | 自然语言 + 标签 |
| 失败的错误上下文 | failure episode → error pattern | `.learnings/ERRORS.md` | TEMPLATE.md 格式 |
| 新发现的过程知识 | procedure delta | `skill-cards/{type}/` | 三维技能卡 |
| 验证通过的策略 | planning_hint 更新 | `skill-cards/*/planning_hints` | YAML 字段 |

**摘要化公式**（核心约束）：

```
原始经验: "用 acpx 0.5.3 执行时，--cwd 是全局选项不是子命令选项，要 cd 到目录再执行"
    ↓ 摘要化
策略偏好: "外部工具的命令行参数位置（全局 vs 子命令）需查文档确认，不能假设"
    ↓ 存入技能卡
planning_hint: { pattern: "CLI 参数位置假设", hint: "外部工具全局选项与子命令选项可能不同" }
```

**实现方式**：
- 当前：Learning Writeback 通过 AGENTS.md 规则手动触发（"错误发生 → 立即记录"）
- 短期：Step Dispatcher 在每步完成后自动触发 writeback
- 中期：独立的 writeback pipeline 脚本，批量处理

### 3.2 中层→内层：技能卡间接传递给 Agent

**这是 Skill-SD 的核心创新点**——经验不直接给执行者，而是通过规划层间接传递。

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│     中层存储         │     │  Planning Agent      │     │  Execution Agent    │
│                      │     │                      │     │                      │
│  skill-cards/        │     │  输入:               │     │  输入:               │
│  .learnings/         │────→│  - 任务描述          │     │  - step.goal        │
│  memory/             │     │  - ExperienceSummary │     │  - strategy_hint    │
│                      │     │                      │     │  - verify           │
│  经验检索:            │     │  输出: StepPlan      │────→│                      │
│  - semantic match    │     │  - steps[]           │     │  ❌ 无任何经验原文    │
│  - UCB selection     │     │  - strategy_hint     │     │                      │
│  - tag/category      │     │  - risk_notes        │     │  输出: StepResult    │
│                      │     │                      │     │                      │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**接口契约**：

```typescript
// 中层输出 → Planning Agent
interface ExperienceSummary {
  errorPatterns: Array<{
    pattern: string;       // "API 限流风险"
    relevance: "high" | "medium";
  }>;
  proceduralHints: Array<{
    taskType: string;      // "多文件重构"
    approach: string;      // "先建接口再逐文件迁移"
    caveats: string[];     // ["注意循环依赖"]
  }>;
  activeWarnings: string[];  // 来自 SESSION-STATE.md
}

// Planning Agent → Execution Agent（每步）
interface ExecutionInput {
  step: {
    goal: string;            // "将认证逻辑抽取到独立模块"
    strategy_hint: string;   // "这类抽取先建骨架再迁移调用方"
    verify: string;          // "相关测试通过，无新增 lint error"
  };
  context: {
    workingDirectory: string;
    relevantFiles?: string[];
  };
}
```

**关键约束**：
1. ExecutionInput 中 `strategy_hint` 不可包含可直接执行的命令
2. ExperienceSummary 是原始经验的摘要化产物，非原文
3. UCB 检索平衡：用得多的技能卡权重高（利用），但未充分验证的也会被选中（探索）

### 3.3 中层→外层：经验聚合为组织知识

单个 Agent 的经验汇总为组织级知识，供外层做编排决策。

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   中层（个体经验）    │     │   聚合引擎           │     │  外层（组织知识）     │
│                      │     │                      │     │                      │
│  Agent-A 的技能卡    │     │  统计:               │     │  能力矩阵:            │
│  Agent-B 的技能卡    │────→│  - 错误频率分析       │────→│  - 哪个 Agent 擅长什么│
│  .learnings/ 汇总    │     │  - 技能覆盖度         │     │  - 哪类任务需要审批   │
│  memory/ 汇总        │     │  - 成功率趋势         │     │  - 预算分配建议       │
│                      │     │                      │     │                      │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**聚合维度**：

| 维度 | 计算 | 用途 |
|------|------|------|
| 技能覆盖率 | 哪些任务类型有对应的 skill-card | 决定任务路由 |
| 错误热力图 | 哪些错误模式出现频率最高 | 决定 guardrail 优先级 |
| 学习速率 | 新技能卡生成速度 → 稳定的速度 | 决定是否需要人工干预 |
| 成本效率 | 每类任务的 token 消耗 / 完成率 | 预算分配 |

**当前实现**：这一层还未建设。在 1-2 个 Agent 场景下，聚合就是手动审查 `.learnings/` 和 `skill-cards/` 目录。

### 3.4 外层→中层：组织知识分发到个体 Agent

外层根据组织知识决定如何向个体 Agent 分发经验。

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   外层（编排决策）    │     │   分发引擎           │     │  中层（个体技能卡）   │
│                      │     │                      │     │                      │
│  "Agent-A 做飞书任务" │     │  根据角色注入:       │     │  Agent-A 的技能卡库   │
│  "Agent-B 做代码任务" │────→│  - 角色相关技能卡    │────→│  - 飞书 API 集成卡    │
│  "预算 5000 tokens"  │     │  - 预算约束          │     │  - 错误模式库         │
│                      │     │  - 审批规则          │     │  - 预算上限           │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**分发规则**：

| 规则 | 说明 | 时机 |
|------|------|------|
| 角色匹配 | 只分发与 Agent 角色相关的技能卡 | Agent 初始化时 |
| 预算注入 | 在技能卡中标注预算上限 | 任务分配时 |
| 审批注入 | 高风险操作的审批要求 | 任务分配时 |
| 经验更新 | 组织级学习结果下发到个体 | 定期同步 |

**当前实现**：还未建设。单 Agent 场景下不需要分发——所有技能卡都在同一个 workspace。

---

## 4. 实施路线图

### Phase 0：知识库建设 ✅ 已完成

**时间**：2026-04-22 ~ 2026-05-02
**产出**：
- [x] Skill-SD 论文分析（`wiki-agent-system/`）
- [x] HyperAgents 论文分析（`raw/.../18-hyperagents-*.md`）
- [x] Paperclip 项目分析（`wiki-agent-system/wiki/sources/2026-05-02-paperclip-project.md`）
- [x] PRD 草案 v1（`raw/.../06-prd-draft.md`）
- [x] 技术改造建议（`raw/.../05-technical-implementation-openclaw.md`）
- [x] 知识库索引（`wiki-agent-system/index.md`，21 页）
- [x] 三维技能卡系统设计（`skill-cards/`）
- [x] 规划-执行分离架构设计（`notes/projects/plan-exec-separation-design.md`）
- [x] 三层架构蓝图（本文档）

### Phase 1：中层落地 🟡 当前阶段

**时间**：2026-05-03 起，预计 2-3 周

#### W1：规划-执行分离原型

**目标**：最小闭环——Planning Agent 生成 StepPlan，Execution Agent 执行并返回结果。

| 任务 | 交付物 | 依赖 |
|------|--------|------|
| 定义 StepPlan/StepResult JSON Schema | `schemas/step-plan.json` | 无 |
| 编写 Planning Agent prompt 模板 | `templates/planning-agent.md` | Schema |
| 编写 Execution Agent prompt 模板 | `templates/execution-agent.md` | Schema |
| 实现复杂度评估逻辑 | AGENTS.md 规则更新 | 无 |
| 端到端测试（1 个真实复杂任务） | 测试报告 | 全部 |

**退出标准**：一个真实多步任务（如"重构 memory 系统存储层"）成功通过规划-执行分离完成。

#### W2：技能卡系统强化

**目标**：技能卡不再是静态文档，而是带检索能力的结构化知识。

| 任务 | 交付物 | 依赖 |
|------|--------|------|
| 为现有 3 张技能卡添加 `planning_hints` 字段 | 更新后的技能卡 | W1 |
| 扩展技能卡覆盖到高频错误场景（目标 +5 张） | 新技能卡 | `.learnings/ERRORS.md` |
| 编写技能卡提取脚本 | `scripts/extract-skill-card.sh` 更新 | 无 |
| 定义 UCB 检索接口 | `schemas/ucb-retrieval.json` | 无 |

**退出标准**：技能卡数 ≥ 8 张，每张带 `planning_hints`，Planning Agent 能自动检索匹配的技能卡。

#### W3：经验管道 + UCB 检索

**目标**：从"手动记录经验"进化到"自动提炼+智能检索"。

| 任务 | 交付物 | 依赖 |
|------|--------|------|
| 实现 Learning Writeback 自动化 | writeback pipeline | W1 |
| 经验摘要化处理（原始→策略偏好） | 摘要化模板 | W2 |
| UCB 检索原型 | 检索脚本 | W2 UCB schema |
| SESSION-STATE.md 任务状态扩展 | 模板更新 | W1 |

**退出标准**：任务完成后自动生成技能卡更新建议，UCB 检索能在 3 个以上场景中匹配到相关技能卡。

### Phase 2：中层强化 + 外层原型

**时间**：Phase 1 完成后 3-4 周

#### 中层强化

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 四层记忆架构实现 | semantic + episodic + procedural + trigger | 高 |
| 技能卡版本管理 | lineage + 变体 + 失败模式绑定 | 中 |
| 技能触发引擎 | 任务开始时自动推荐/加载 skill | 高 |
| 规划质量追踪 | 记录 StepPlan 成功率、回退率 | 中 |

#### 外层原型（单 Agent 简化版）

> **关键判断**：当前 1-2 个 Agent 规模，不引入完整 Paperclip，而是借鉴其 3 个核心概念做轻量实现。

| 借鉴概念 | 轻量实现 | 对应模块 |
|---------|---------|---------|
| 目标链 | Task Roadmap JSON（goal→milestone→step 层级） | M7 全局意识 |
| 原子锁 | 文件锁（`.task-lock`）防止并发冲突 | M6 长时状态 |
| 持久状态 | JSON 状态文件 + 自动 checkpoint | M6 长时状态 |

**具体交付**：

| 任务 | 交付物 |
|------|--------|
| Task State Object 定义 | `schemas/task-state.json` |
| Task Roadmap Schema | `schemas/task-roadmap.json` |
| Checkpoint/Resume 机制 | 脚本 + AGENTS.md 规则 |
| Global Position Tracker | 轻量版，嵌入 SESSION-STATE.md |
| 预算追踪（token 级） | 简单计数器 + 阈值告警 |

**退出标准**：
- 一个跨 session 的长时任务（>1 天）能成功 checkpoint/resume
- Agent 始终知道自己在全局目标中的位置
- Token 消耗有可见的追踪

### Phase 3：外层完善 + 内层原型

**时间**：Phase 2 完成后 4-6 周

#### 外层完善

| 任务 | 说明 |
|------|------|
| 多 Agent 任务路由 | 根据技能覆盖矩阵分发任务 |
| 审批流 | 高风险操作需要人工确认 |
| Agent 角色定义 | 能力声明 + 权限边界 |
| 治理配置版本化 | 配置变更可回滚 |

#### 内层原型（元认知 + 自改进）

| 任务 | 说明 | 来源 |
|------|------|------|
| 原则库（Principle Store） | 存储从错误中提炼的行为原则 | HyperAgents |
| 偏差模式库 | 记录 Agent 的认知偏差 | HyperAgents |
| 反思→原则更新循环 | 执行后自动反思→生成/更新原则 | HyperAgents |
| 开放式自改进 | 不限定改进方向，Agent 自主发现可优化点 | HyperAgents |

**退出标准**：
- Agent 能自主识别重复犯错模式并生成预防原则
- 至少 3 个通过自反思产生的新原则被验证有效
- 多 Agent 场景下任务能自动路由到合适的 Agent

### Phase 4：三层闭环

**时间**：Phase 3 完成后 4-8 周

| 任务 | 说明 |
|------|------|
| 组织级学习闭环 | 个体经验 → 组织知识 → 分发到个体 → 新经验 |
| 自优化循环 | 系统自动调优参数（复杂度阈值、检索权重、策略偏好） |
| 跨场景迁移 | 任务本体 + 潜在模式识别 |
| 评测体系 | 跨层 KPI：稳定性、学习效率、迁移成功率 |
| 能力复制 | 新 Agent 上线时自动继承组织知识 |

**退出标准**：
- 新 Agent 上线到达到平均能力水平 < 3 天
- 重复错误率 < 5%
- 跨场景迁移成功率 > 60%

---

## 5. 关键决策

### 5.1 当前 Agent 规模（1-2 个）是否需要外层？

**判断：需要，但简化版。**

| 考量 | 分析 |
|------|------|
| 多 Agent 协调 | 当前不需要。1 个 coding agent 足够 |
| 目标链 | **需要**。长时任务（>1 天）需要知道自己在哪里，即使只有一个 Agent |
| 原子锁 | **需要**。并发场景已出现（A2A 请求 + 主会话同时操作） |
| 持久状态 | **需要**。跨 session 恢复是核心需求 |
| 预算治理 | **需要**。token 成本需要追踪 |
| 审批流 | 暂时不需要，AGENTS.md 的 "ask first" 规则够用 |
| 组织级学习 | 暂时不需要，个体学习优先 |

**结论**：借鉴 Paperclip 的目标链、原子锁、持久状态 3 个概念，做文件级的轻量实现。不引入 Paperclip 本身（它是为多 Agent 公司设计的，单 Agent 场景太重）。

### 5.2 状态持久化方案：文件 vs DB

**判断：文件优先，按需升级。**

| 方案 | 优点 | 缺点 | 适用阶段 |
|------|------|------|---------|
| JSON 文件 | 零依赖、人可读、git 可追踪 | 无事务、无并发控制 | Phase 1-2 |
| SQLite | 轻量、有事务、查询灵活 | 需要 schema 管理 | Phase 2-3 |
| PostgreSQL | 完整 DB、Paperclip 用这个 | 重量级、运维成本 | Phase 3+（多 Agent） |

**策略**：
- Phase 1-2：纯文件（JSON + Markdown）。符合 OpenClaw 的文件优先哲学
- Phase 2 末：评估 SQLite 是否必要（如果并发写入成为瓶颈）
- Phase 3：多 Agent 场景下考虑 SQLite 或 PostgreSQL
- Paperclip 的 PostgreSQL embedded 方案可作为参考，但不是当前选项

**文件结构设计**：

```
workspace-coding/
├── schemas/
│   ├── step-plan.json          # StepPlan/StepResult schema
│   ├── task-state.json         # Task State Object schema
│   ├── task-roadmap.json       # 目标链 schema
│   └── ucb-retrieval.json      # UCB 检索接口
├── templates/
│   ├── planning-agent.md       # Planning Agent prompt
│   └── execution-agent.md      # Execution Agent prompt
├── skill-cards/
│   ├── domains/                # 领域知识卡
│   ├── patterns/               # 错误模式卡
│   └── workflows/              # 工作流卡
├── .learnings/
│   ├── ERRORS.md               # 错误记录
│   ├── LEARNINGS.md            # 经验记录
│   └── TEMPLATE.md             # 记录模板
├── memory/
│   └── YYYY-MM-DD.md           # 每日笔记
└── .task-state/                # 任务状态（Phase 2 新增）
    ├── current.json            # 当前活跃任务状态
    └── history/                # 已完成任务归档
```

### 5.3 自建 vs 复用 Paperclip

**判断：自建核心，借鉴 Paperclip 设计。**

| 维度 | 自建 | Paperclip |
|------|------|-----------|
| **适用规模** | 1-3 个 Agent | 5+ 个 Agent |
| **依赖** | 零（纯文件） | Node.js + PostgreSQL |
| **可定制性** | 完全控制 | 配置化，但核心逻辑固定 |
| **维护成本** | 自己维护 | 社区维护 |
| **当前匹配度** | 高（需要的目标链/原子锁/持久状态） | 低（大部分功能用不上） |
| **未来扩展** | 可控升级 | 生态成熟 |

**策略**：
1. **Phase 1-2**：纯自建。Paperclip 的 12 个子系统中我们只需要 3 个，不值得引入整个项目
2. **Phase 2 末**：评估。如果多 Agent 需求增长到 5+，考虑引入 Paperclip 作为外层
3. **设计对齐**：自建的 schema 和接口设计参考 Paperclip 的数据模型，确保未来兼容

**借鉴清单**（直接复用设计思路，不复用代码）：

| Paperclip 概念 | 自建实现 |
|---------------|---------|
| Goal Chain | `task-roadmap.json` 中的 goal→milestone→step |
| Atomic Checkout | `.task-lock` 文件锁 |
| Persistent Agent State | `.task-state/current.json` |
| Budget Tracking | JSON 计数器 + 阈值检查 |
| Heartbeat Execution | OpenClaw cron（已有） |
| Runtime Skill Injection | Planning Agent + ExperienceSummary |

### 5.4 技术栈选择

| 组件 | 选择 | 理由 |
|------|------|------|
| Schema 定义 | JSON Schema | 零依赖、工具链成熟 |
| Prompt 模板 | Markdown + 占位符 | 与现有 AGENTS.md 一致 |
| 状态存储 | JSON 文件 | 人可读、git 友好 |
| 技能卡存储 | Markdown + YAML frontmatter | 三维技能卡已是这个格式 |
| 检索引擎 | memory_search + 文件匹配 | 复用 OpenClaw 已有能力 |
| 编排调度 | sessions_spawn | 复用 OpenClaw subagent 机制 |
| 错误追踪 | `.learnings/ERRORS.md` | 已在运行 |

---

## 6. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解 |
|------|--------|------|------|
| 规划-执行分离增加延迟 | 高 | 中 | 简单任务退化模式（已有设计） |
| 技能卡质量不够，检索噪声大 | 中 | 高 | UCB 探索-利用平衡 + 人工审核首批卡 |
| 文件级并发控制不够 | 中 | 中 | Phase 2 监控，需要时升级 SQLite |
| Agent prompt 膨胀 | 中 | 高 | 严格限制 Planning Agent 注入量，ExperienceSummary 有上限 |
| 三层边界模糊，职责泄漏 | 低 | 高 | 接口 schema 强制校验，定期审查 |

---

## 7. 成功指标

### Phase 1 完成标准
- [ ] 规划-执行分离：至少 3 个真实复杂任务通过分离模式完成
- [ ] 技能卡数 ≥ 8 张，每张带 planning_hints
- [ ] UCB 检索准确率 > 70%（人工评估）
- [ ] Learning Writeback 自动化率 > 80%

### Phase 2 完成标准
- [ ] 跨 session 任务恢复成功率 > 90%
- [ ] Global Position Tracker 在所有长时任务中启用
- [ ] 重复错误率 < 15%（相比无系统基线）

### Phase 3 完成标准
- [ ] 自反思产生 ≥ 3 个验证有效的原则
- [ ] 多 Agent 任务路由准确率 > 80%
- [ ] 重复错误率 < 10%

### Phase 4 完成标准
- [ ] 新 Agent 上线到平均能力 < 3 天
- [ ] 跨场景迁移成功率 > 60%
- [ ] 重复错误率 < 5%

---

## 附录 A：原 PRD 模块到三层映射详表

```
原 PRD 10 模块                    三层架构映射              当前进度
─────────────────────────────────────────────────────────────────────
M1  执行约束与验证 Runtime    →   内层 / 执行验证          🟡 30%
M2  群体错误学习系统          →   内层 / 错误学习          🟡 25%
M3  长期记忆与场景触发        →   中层 / 记忆系统          🟡 40%
M4  Skill 演化与共享网络      →   中层 / 技能卡系统        🟢 50%
M5  训练与能力复制            →   中层 / 能力传承          ⚪ 5%
M6  长时任务状态系统          →   外层 / 持久状态          ⚪ 0%
M7  全局意识/路径感知         →   外层 / 目标链            ⚪ 0%
M8  元认知能力层              →   内层 / 元认知            ⚪ 0%
M9  泛化与跨场景迁移          →   内层 / 迁移              ⚪ 0%
M10 评测与闭环优化            →   跨层 / 评测体系          ⚪ 0%
```

## 附录 B：三层架构 vs 论文概念映射

```
Skill-SD 贡献 → 中层
├── 技能条件化自蒸馏 → 技能卡只给 Planning Agent，不直接注入 Execution Agent
├── 三维经验结构 → skill-cards/domains, patterns, workflows
├── UCB 检索 → 平衡已知技能（利用）和未验证技能（探索）
└── 间接知识传递 → strategy_hint 机制

HyperAgents 贡献 → 内层
├── 元认知自修改 → Principle Store + 反思循环
├── 开放式自改进 → 不限定改进方向，自主发现优化点
├── 错误学习 → 错误→原则自动提炼
└── 存档机制 → Task State checkpoint

Paperclip 贡献 → 外层
├── 目标链执行 → Task Roadmap (goal→milestone→step)
├── 原子执行锁 → .task-lock 文件锁
├── 持久 Agent 状态 → .task-state/ JSON
├── 预算治理 → token 计数器 + 阈值
└── 组织级学习（Roadmap）→ Phase 4 目标
```

## 附录 C：与现有 OpenClaw 机制的关系

| OpenClaw 已有 | 本架构对应 | 关系 |
|--------------|-----------|------|
| `sessions_spawn` | Execution Agent 调度 | 直接复用，不引入新原语 |
| `memory_search` | 经验检索层 | 直接复用，增加摘要化后处理 |
| AGENTS.md | 复杂度评估 + 执行模式 | 扩展，不替换 |
| SESSION-STATE.md | Task State Object | 扩展字段，不替换 |
| `.learnings/` | 错误模式库 | 直接复用，增加自动 writeback |
| `skill-cards/` | 技能卡系统 | 直接复用，增加 planning_hints |
| OpenClaw cron | Heartbeat Execution | 直接复用 |

**设计原则**：所有新功能都是现有机制的扩展，不引入并行体系。退化模式下系统行为与当前完全一致。
