# UCB 混合检索选择器设计方案

> 基于 Skill-SD 论文的 UCB 技能检索机制，适配非 RL 训练场景（API 调用 LLM）

## 1. 核心设计

### 1.1 问题定义

传统技能检索依赖纯语义相似度（如 `memory_search`），但"语义相似 ≠ 效果好"。UCB（Upper Confidence Bound）引入**效果反馈**维度，平衡探索（新技能）与利用（已验证的高效技能）。

核心挑战：UCB 原生于 RL 训练循环，reward 由环境自动给出。在非 RL 场景（API 调用 LLM），需要**人工或半自动**获取 reward 信号。

### 1.2 UCB 公式适配

#### 原始 UCB 公式

```
score(e) = r̄(e) + c × √(ln(N_total) / n(e))
```

#### 混合评分公式

```
final_score(e) = α × ucb_score(e) + β × semantic_sim(e, query)
```

其中：

| 符号 | 含义 | 默认值 |
|------|------|--------|
| `r̄(e)` | 技能 e 的历史平均奖励（avg_reward） | — |
| `n(e)` | 技能 e 的被选中次数（usage_count） | — |
| `N_total` | 所有技能卡的总使用次数 | 动态计算 |
| `c` | 探索系数 | 1.414（√2） |
| `α` | UCB 权重 | 0.6 |
| `β` | 语义相似度权重 | 0.4 |
| `semantic_sim(e, query)` | 查询与技能卡的语义相似度 | 0.0-1.0 |

**约束**：`α + β = 1.0`，确保分数归一化。

#### 归一化

UCB 分数和语义分数分别归一化到 [0, 1] 后再加权：

```python
# UCB 归一化：min-max scaling
ucb_raw(e) = r̄(e) + c × √(ln(max(N_total, 1)) / max(n(e), 1))
ucb_norm(e) = (ucb_raw(e) - ucb_min) / (ucb_max - ucb_min)  # → [0, 1]

# 语义相似度本身已在 [0, 1]
sem_norm(e) = semantic_sim(e, query)

# 最终分数
final_score(e) = α × ucb_norm(e) + β × sem_norm(e)
```

### 1.3 Reward 定义（非 RL 场景）

| Reward 来源 | 分值 | 触发方式 | 可靠性 |
|-------------|------|---------|--------|
| 任务成功完成 | +1.0 | 自动检测（exit code = 0） | 高 |
| 任务部分完成 | +0.5 | 人工标注或启发式推断 | 中 |
| 任务失败 | 0.0 | 自动检测（exit code ≠ 0 / 超时） | 高 |
| 人工反馈（👍/👎） | +1.0 / 0.0 | 用户显式反馈 | 最高 |

#### Reward 更新公式

```python
avg_reward_new = (avg_reward_old × usage_count_old + reward_new) / (usage_count_old + 1)
usage_count_new = usage_count_old + 1
```

#### 自动推断规则

1. **脚本/命令执行**：exit code 0 → reward=1.0，exit code ≠ 0 → reward=0.0
2. **文档生成任务**：生成的文档被引用/使用 → reward=1.0；被修改后使用 → reward=0.5；未使用 → reward=0.0
3. **搜索/检索任务**：用户采纳了检索结果 → reward=1.0；用户继续搜索 → reward=0.3
4. **默认回退**：无明确信号时 → reward=0.5（中性）

### 1.4 冷启动处理

新技能卡 `usage_count=0` 时的策略：

```python
if n(e) == 0:
    ucb_score(e) = ∞  # 实际实现：设为一个大数（如 999.0）
```

**优先级**：
1. `n(e) = 0` 的新技能卡 → 最高探索优先级（UCB = ∞）
2. 新技能之间按 `semantic_sim` 排序
3. 新技能的 `avg_reward` 初始值为 0.5（中性假设）

### 1.5 衰减机制

旧技能卡随时间降权，避免过时经验占据高位。

#### 时间衰减因子

```python
decay_weight(e) = exp(-λ × days_since_last_use(e))
```

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `λ` | 衰减速率 | 0.01（半衰期 ≈ 69 天） |
| `days_since_last_use` | 距上次使用的天数 | 动态计算 |

#### 融入最终分数

```python
final_score(e) = decay_weight(e) × (α × ucb_norm(e) + β × sem_norm(e))
```

#### 衰减建议值

| 场景 | λ | 半衰期 |
|------|---|--------|
| 快速迭代的技术栈 | 0.03 | ~23 天 |
| 稳定领域知识 | 0.005 | ~138 天 |
| 默认（通用） | 0.01 | ~69 天 |

## 2. 接口定义

### 2.1 输入

```json
{
  "query": "需要配置 A2A Gateway 与远程 agent 通信",
  "task_type": null,        // 可选：过滤特定 task_type
  "top_k": 3,               // 返回前 k 个结果
  "alpha": null,             // 可选：覆盖默认 α
  "beta": null,              // 可选：覆盖默认 β
  "exploration_c": null,     // 可选：覆盖默认探索系数 c
  "decay_lambda": null       // 可选：覆盖默认衰减速率 λ
}
```

### 2.2 输出

```json
{
  "results": [
    {
      "id": "sc-20260426-001",
      "title": "A2A Gateway 安装与调试工作流",
      "type": "workflow",
      "task_types": ["网络配置", "Agent 通信"],
      "final_score": 0.87,
      "score_breakdown": {
        "ucb_raw": 1.23,
        "ucb_norm": 0.95,
        "semantic_sim": 0.82,
        "decay_weight": 0.97,
        "alpha_contribution": 0.57,
        "beta_contribution": 0.33
      },
      "avg_reward": 0.85,
      "usage_count": 0,
      "last_used": null,
      "status": "draft"
    }
  ],
  "metadata": {
    "total_cards": 3,
    "filtered_cards": 3,
    "params": {
      "alpha": 0.6,
      "beta": 0.4,
      "c": 1.414,
      "lambda": 0.01,
      "N_total": 0
    }
  }
}
```

### 2.3 与 memory_search 的集成

```
┌─────────────┐
│  用户查询    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ 1. task_type 过滤    │ ← 可选，从输入参数获取
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐     ┌────────────────┐
│ 2. 语义相似度计算    │────→│ memory_search   │  ← 利用现有语义索引
│    semantic_sim(e,q) │     │ 或关键词匹配    │
└──────┬──────────────┘     └────────────────┘
       │
       ▼
┌─────────────────────┐
│ 3. 读取技能卡元数据  │ ← 从 skill-cards/*.md 的 YAML frontmatter
│    avg_reward, etc.  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 4. 计算 UCB 分数     │
│    ucb_raw → ucb_norm│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 5. 时间衰减          │
│    decay_weight(e)   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 6. 混合评分 + 排序   │
│    final_score → top_k│
└─────────────────────┘
```

**语义相似度获取方式**（按优先级）：
1. `memory_search` — 利用现有语义索引，查询与技能卡内容的相似度
2. **关键词匹配 fallback** — 简单 TF-IDF 或 Jaccard 相似度，不需要外部服务
3. **嵌入向量预计算** — 预先为每张技能卡计算 embedding，检索时只算 query embedding + cosine sim

## 3. 参数调优建议

### 3.1 α/β 权重

| 场景 | α (UCB) | β (语义) | 理由 |
|------|---------|---------|------|
| 初期（< 50 次检索） | 0.3 | 0.7 | 语义相似度更可靠，UCB 数据不足 |
| 成熟期（50-200 次） | 0.5 | 0.5 | 两者并重 |
| 后期（> 200 次） | 0.6 | 0.4 | UCB 数据充分，效果反馈更可靠 |

### 3.2 探索系数 c

| 值 | 行为 | 适用场景 |
|----|------|---------|
| 0.5 | 偏利用 | 技能库稳定，较少新增 |
| 1.414 (√2) | 均衡 | 默认 |
| 2.0 | 偏探索 | 技能库快速扩张期 |

### 3.3 衰减速率 λ

| 值 | 半衰期 | 适用场景 |
|----|--------|---------|
| 0.005 | ~138 天 | 稳定知识（数学、理论） |
| 0.01 | ~69 天 | 通用（默认） |
| 0.03 | ~23 天 | 快速迭代的技术（工具版本、API） |

## 4. 关键问题解答

### Q1: reward 如何在非训练场景获取？

**三级方案**：

1. **自动推断**（默认）：根据任务执行结果（exit code、是否被引用）自动打分
2. **人工反馈**（可选）：用户通过 👍/👎 或评分给出显式反馈
3. **启发式规则**（补充）：文档被修改后使用 → reward=0.5；直接使用 → reward=1.0

推荐：日常用自动推断，关键场景要求人工确认。

### Q2: 冷启动问题

- 新技能卡 `usage_count=0` → UCB = ∞ → 最高探索优先级
- 新卡之间按语义相似度排序
- 初始 `avg_reward=0.5`（中性假设），首次使用后更新

### Q3: 衰减机制

- `decay_weight = exp(-λ × days_since_last_use)`
- λ=0.01（默认），半衰期约 69 天
- 未使用的旧技能逐渐降权，但不被完全排除
- 新使用的技能 decay_weight 重置为 1.0

## 5. 实现路径

```
阶段 1（当前）：关键词匹配 fallback + 手动 reward 更新
    ↓
阶段 2：集成 memory_search 语义检索 + 自动 reward 推断
    ↓
阶段 3：预计算 embedding + 增量更新 + 可视化仪表盘
```

## 参考

- Skill-SD 论文：UCB 技能检索原论文
- `wiki-agent-system/wiki/entities/UCB技能检索.md`
- `wiki-agent-system/wiki/entities/动态技能生成.md`
- `notes/resources/templates/skill-card-schema.md`
