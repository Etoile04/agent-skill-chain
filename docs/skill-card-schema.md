# 技能卡 Schema（三维技能卡 v1.0）

> 基于 Skill-SD 论文的 `(e_success, e_mistake, e_workflow)` 三维结构，用于从对话轨迹中提炼结构化经验。

## 设计原则

1. **不存原始轨迹，只存结构化摘要** — 原始对话流水账留在 `memory/YYYY-MM-DD.md`
2. **三维覆盖** — 正例（什么有效）、反例（什么失败）、策略（推荐流程）
3. **与现有系统互补** — 技能卡是 `.learnings/` 的上层抽象，不是替代

## YAML Frontmatter

```yaml
---
id: sc-YYYYMMDD-NNN          # 唯一标识，格式：sc-日期-序号
type: workflow | pattern | domain  # 技能类型
category: workflows | patterns | domains  # 对应 skill-cards/ 子目录
task_types:                    # 适用的任务类型标签
  - 配置调试
  - 系统集成
avg_reward: 0.0-1.0           # 历史成功率（初始 0.5）
usage_count: 0                # 被检索/引用次数
created: YYYY-MM-DD           # 创建日期
updated: YYYY-MM-DD           # 最后更新日期
status: draft | active | deprecated  # 生命周期状态
sources:                       # 原始轨迹来源
  - memory/2026-04-26.md
related_learnings:             # 关联的 .learnings/ 条目
  - ERR-20260426-001
related_cards:                 # 关联的其他技能卡
  - sc-20260429-001
---
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 唯一标识，自动生成 |
| `type` | ✅ | workflow（工作流）、pattern（模式）、domain（领域） |
| `category` | ✅ | 对应存储目录，必须与 type 一致映射 |
| `task_types` | ✅ | 至少一个，用于检索匹配 |
| `avg_reward` | ✅ | 0.0-1.0，每次使用后更新 |
| `usage_count` | ✅ | 引用计数，UCB 检索用 |
| `created` | ✅ | ISO 日期 |
| `updated` | ✅ | 最后更新 |
| `last_used` | ❌ | 最后一次被检索使用的日期（ISO 格式），用于时间衰减。未填写时 fallback 到 `updated` |
| `decay_weight` | ❌ | 时间衰减因子（0.0-1.0），由检索脚本自动计算，不需要手动填写。公式：`exp(-λ × days_since_last_use)`，默认 λ=0.01 |
| `status` | ✅ | 生命周期 |
| `sources` | ❌ | 原始对话轨迹来源 |
| `related_learnings` | ❌ | 关联 `.learnings/` 条目 |
| `related_cards` | ❌ | 关联其他技能卡 |

## 正文结构

### 1. e_success：什么做法有效

```markdown
## ✅ 成功经验 (e_success)

### 有效的策略
- [策略描述 1]
- [策略描述 2]

### 关键决策
- **决策点 A**：选择了 X，原因是 Y
- **决策点 B**：...

### 验证过的工具/方法
- [工具名 + 具体用法]
```

### 2. e_mistake：什么做法失败

```markdown
## ❌ 失败教训 (e_mistake)

### 踩过的坑
- [坑描述 + 根因]
- [坑描述 + 根因]

### 错误模式
- **模式名**：[症状 → 根因 → 修复]

### 需要避免的做法
- [不要做 X，因为 Y]
```

### 3. e_workflow：推荐工作流

```markdown
## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. [步骤 1 — 预检查]
2. [步骤 2 — 执行]
3. [步骤 3 — 验证]
4. [步骤 4 — 收尾]

### 触发条件
- 当遇到 [场景描述] 时使用本技能

### 前置条件
- [需要的环境/权限/工具]

### 预期结果
- [成功标准]

### 回退方案
- 如果 [步骤 N] 失败 → [替代方案]
```

## 与现有系统的关系

```
memory/YYYY-MM-DD.md          ← 原始轨迹（时间线流水账）
        ↓ 提取
skill-cards/{category}/{name}.md  ← 结构化技能卡（三维摘要）
        ↓ 引用
.learnings/ERRORS.md          ← 错误明细（5-Why、预防规则）
.learnings/LEARNINGS.md       ← 通用学习记录
        ↓ 检索
AGENTS.md WAL 协议            ← 实时扫描触发
```

### 关系说明

| 系统 | 内容 | 粒度 | 生命周期 |
|------|------|------|---------|
| `memory/` | 原始对话轨迹 | 细（逐条记录） | 按日归档 |
| `skill-cards/` | 三维结构化摘要 | 中（主题聚合） | 持续更新 |
| `.learnings/` | 错误/学习明细 | 细（单条错误） | 持续追加 |

- `memory/` 是**原料**
- `skill-cards/` 是**精炼产品**
- `.learnings/` 是**副产品**（聚焦错误与学习）

## UCB 检索公式

### 基础 UCB 公式

```
ucb_raw(e) = r̄(e) + c × √(ln(N_total) / n(e))
```

- `r̄(e)` = avg_reward
- `n(e)` = usage_count
- `N_total` = 所有技能卡的总使用次数
- `c` = 探索系数（默认 √2 ≈ 1.414）

新技能卡（usage_count=0）自动获得最高探索优先级（ucb_raw = ∞）。

### UCB 混合检索公式

```
final_score(e) = decay_weight(e) × (α × ucb_norm(e) + β × semantic_sim(e, query))
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `α` | 0.6 | UCB 归一化分数权重 |
| `β` | 0.4 | 语义相似度权重 |
| `decay_weight(e)` | `exp(-λ × days_since_last_use)` | 时间衰减因子 |
| `λ` | 0.01 | 衰减速率（半衰期 ≈ 69 天） |
| `c` | 1.414 | UCB 探索系数 |

### UCB 相关字段说明

#### `last_used`（ISO 日期，可选）

- 技能卡最后一次被检索使用的日期
- 格式：`YYYY-MM-DD`
- 用于计算 `decay_weight`
- 如果未填写，检索脚本 fallback 到 `updated` 字段
- 每次技能被采用时更新：`last_used = 今天`
- **更新时机**：当用户/Agent 实际采用了该技能卡的建议时更新，不仅仅是检索到

#### `decay_weight`（浮点数，自动计算）

- 范围 0.0-1.0
- 由检索脚本根据 `last_used` 自动计算，**不需要手动维护**
- 计算公式：`exp(-λ × days_since_last_use)`
- 作用：让长时间未使用的旧技能逐渐降权
- 当技能被再次使用时，衰减重置为 1.0

#### `avg_reward` 更新规则

```python
avg_reward_new = (avg_reward_old × usage_count_old + reward_new) / (usage_count_old + 1)
```

Reward 来源（非 RL 场景）：

| 信号 | Reward 值 | 触发方式 |
|------|----------|----------|
| 任务成功 | 1.0 | exit code = 0 / 用户确认 |
| 部分成功 | 0.5 | 人工标注 / 启发式推断 |
| 任务失败 | 0.0 | exit code ≠ 0 / 超时 |
| 用户反馈 | 1.0 / 0.0 | 👍/👎 显式反馈 |
| 无信号 | 0.5 | 中性默认值 |

#### `usage_count` 更新规则

- 每次技能卡被**实际采用**（不仅是检索到）时 +1
- 同一任务同一会话内不重复计数

### YAML Frontmatter 完整示例

```yaml
---
id: sc-20260426-001
type: workflow
category: workflows
task_types:
  - 网络配置
  - Agent 通信
avg_reward: 0.85
usage_count: 3
created: 2026-04-26
updated: 2026-05-02
last_used: 2026-05-02      # ← 最后被采用的日期
status: active
sources:
  - memory/2026-04-26.md
---
```

### 检索流程

1. **加载**：读取 `skill-cards/` 下所有 `.md` 的 YAML frontmatter
2. **过滤**：可选按 `task_type` 过滤
3. **语义计算**：计算 `semantic_sim(query, card)`
4. **UCB 计算**：`ucb_raw → ucb_norm`（min-max 归一化）
5. **衰减计算**：`decay_weight = exp(-λ × days_since_last_use)`
6. **混合评分**：`final_score = decay × (α × ucb_norm + β × semantic_sim)`
7. **排序输出**：按 `final_score` 降序，返回 top-k

### 参数调优建议

| 阶段 | α | β | c | λ |
|------|---|---|---|---|
| 初期（<50 次检索） | 0.3 | 0.7 | 1.414 | 0.01 |
| 成熟期（50-200 次） | 0.5 | 0.5 | 1.414 | 0.01 |
| 后期（>200 次） | 0.6 | 0.4 | 1.0 | 0.01 |

## 完整示例

```markdown
---
id: sc-20260426-001
type: workflow
category: workflows
task_types:
  - 网络配置
  - Agent 通信
avg_reward: 0.85
usage_count: 3
created: 2026-04-26
updated: 2026-05-02
status: active
sources:
  - memory/2026-04-26.md
related_learnings:
  - ERR-20260426-001
---

# A2A Gateway 安装与调试工作流

## ✅ 成功经验 (e_success)

### 有效的策略
- 安装前先备份配置，创建独立测试目录
- 发现 session 互斥后，将 defaultAgentId 改为独立 agent（writer）
- 用回环 ping/pong 作为首个连通性测试

### 关键决策
- **agent 选择**：默认 agent 活跃时阻塞 A2A dispatch → 分配独立 writer agent
- **安全策略**：npm 被安全策略拦截 → 改用源码 + --dangerously-force-unsafe-install

### 验证过的工具/方法
- openclaw-a2a-gateway v1.4.0
- 并发测试：5 请求全部成功（max_active=4）

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- REST 端点 v1.4.0 未注册，只有 JSON-RPC 和 gRPC 可用
- 残留任务需重启 Gateway 才能清理
- SSRF 防护需显式配置 fileUriAllowlist

### 错误模式
- **Agent session 互斥**：同一 agent 活跃 session 阻塞 A2A dispatch → 分配专用 agent

### 需要避免的做法
- 不要用默认 agent 路由 A2A 任务（会阻塞）
- 不要假设 REST 端点可用（v1.4.0 未注册）

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. 备份配置 + 创建测试目录
2. 安装 A2A Gateway 插件
3. 配置 Agent Card（端口、认证、路由）
4. 将 defaultAgentId 设为独立 agent（非活跃 agent）
5. 回环 ping/pong 测试连通性
6. 异步任务测试
7. 并发压力测试
8. 更新 TOOLS.md + 测试报告

### 触发条件
- 需要安装或调试 A2A Gateway
- 需要配置 agent 间通信

### 前置条件
- OpenClaw Gateway 运行中
- 有独立的 agent 可分配给 A2A

### 预期结果
- A2A Gateway 正常响应 ping/pong
- 异步任务可投递和完成
- 并发请求不丢失

### 回退方案
- 如果 dispatch 超时 → 检查 agent session 是否互斥，换独立 agent
- 如果任务残留 → 重启 Gateway 清理
```
