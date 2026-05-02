# Agent Skill Chain

> 基于间接知识传递的智能体长时任务能力增强系统

## 核心理念

来自 Skill-SD 论文的关键发现：**直接注入经验会破坏 Agent 探索能力**（Sokoban 51.6% → 20.3%）。

本系统采用**间接知识传递**架构：经验经过摘要化变成策略偏好（strategy_hint），通过规划层间接影响执行层。

## 三层架构

```
┌─────────────────────────────────────────┐
│ 外层：编排控制面（Paperclip 思路）         │
│ 多Agent协调、目标链、原子锁、预算治理     │
├─────────────────────────────────────────┤
│ 中层：经验传递（Skill-SD 思路）           │
│ 间接知识传递、三维技能卡、UCB 检索        │
├─────────────────────────────────────────┤
│ 内层：Agent 能力（HyperAgents 思路）      │
│ 元认知自修改、开放式自改进、错误学习      │
└─────────────────────────────────────────┘
```

## 项目结构

```
├── schemas/          # JSON Schema（StepPlan, StepResult）
├── templates/        # Prompt 模板（Planning/Execution Agent）
├── scripts/          # 工具脚本（UCB检索, Writeback, 提取）
├── skill-cards/      # 三维技能卡库（workflows/patterns/domains）
│   ├── workflows/    # 完整工作流
│   ├── patterns/     # 错误模式与解决方案
│   ├── domains/      # 领域知识
│   └── pending/      # Writeback 自动生成的 draft 卡
└── docs/
    ├── design/       # 架构设计文档
    ├── blueprint/    # 三层架构蓝图
    ├── learnings/    # 错误/学习记录
    └── skill-card-schema.md
```

## 中层闭环流程

```
任务描述 → UCB 检索 → 匹配技能卡 → ExperienceSummary
    → Planning Agent（带经验）→ StepPlan（策略偏好）
    → Execution Agent（零经验）→ StepResult
    → Writeback Pipeline → 错误/技能卡/日志
    → 技能卡更新 → 回到检索（闭环）
```

## 关键约束

1. **C1**：执行层 prompt 不包含任何经验检索结果
2. **C2**：规划层输出必须是策略偏好，不是具体动作指令
3. **C3**：与现有 sessions_spawn 机制兼容

## 技术来源

| 来源 | 贡献 |
|------|------|
| [Skill-SD](https://arxiv.org/abs/2604.10674) | 间接知识传递、UCB 检索、技能条件化 |
| [HyperAgents](https://arxiv.org/abs/2503.14408) | 元认知自修改、开放式自改进 |
| [Paperclip](https://github.com/paperclipai/paperclip) | 编排控制面、目标链、原子锁 |

## 许可

MIT
