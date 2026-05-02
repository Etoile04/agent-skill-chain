---
id: sc-20260428-001
type: pattern
category: patterns
task_types:
  - A2A 通信
  - 异步任务
  - Agent 协作
  - 超时处理
avg_reward: 0.30
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
transfer_mode: indirect
sources:
  - memory/2026-04-28-a2a-kb.md
planning_hints:
  common_failures:
    - pattern: "A2A 复杂任务稳定超时"
      hint: "预估耗时 > 30s 的任务不要走 main agent，直接路由到 dedicated agent（writer）"
    - pattern: "同步派发入口超时"
      hint: "始终使用 --non-blocking 非阻塞投递，再通过 task_id 轮询状态"
    - pattern: "重复尝试同质方案浪费时间"
      hint: "同步→异步→极短指令本质是同一问题，一次失败后直接切换策略级别"
  typical_approach: "先评估任务复杂度（<30s 走 main / >30s 走 dedicated），非阻塞投递，定期查状态"
  caveats:
    - "A2A 任务失败多是超时问题，不是授权问题，不要在权限排查上浪费时间"
    - "A2A 全部失败时可退回本地 agent 执行，不走 A2A"
---

# A2A Gateway 复杂任务超时模式

## ✅ 成功经验 (e_success)

### 经验传递分级
```yaml
experiences:
  direct:
    - "A2A main agent 路由不支持耗时 > 30s 的任务，会稳定超时"
  indirect:
    - "预估耗时 > 30s 的任务路由到 dedicated agent，非阻塞投递再轮询状态"
    - "同步→异步→极短指令是同一问题的重复尝试，一次失败后直接切换策略级别"
  forbidden:
    - "具体 A2A 命令和参数见 e_workflow"
```

### 有效的策略
- **A2A Gateway 能正确送达 main agent**：ping/pong 和简单任务可以成功
- **非阻塞投递（non-blocking）**：可以避免入口超时，任务能进入 `working` 状态
- **确认了 main agent 具备所需能力**：llm-wiki、wiki_search/wiki_get/wiki_apply/wiki_lint、feishu_* 工具都可用

### 关键决策
- 尝试了 3 种发送方式（直接长任务 / 异步 non-blocking + wait / 极短指令），确认了问题边界

### 验证过的工具/方法
- A2A Gateway JSON-RPC 端点
- 非阻塞投递模式（`--non-blocking --wait --timeout-ms 600000`）

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **同步派发超时**：复杂任务（如"完善知识库"）发给 main agent 时，稳定超时
- **异步投递虽然能进入 working，但最终仍失败**：Agent dispatch failed: gateway request timed out
- **A2A 任务落盘有竞争**：出现过 ENOENT rename 错误（一次性问题）
- **多次尝试同一方案浪费了时间**：3 种方式本质上是同一个问题

### 错误模式
- **A2A 复杂任务超时**：症状（dispatch timeout）→ 根因（main agent 无法在网关超时窗口内完成复杂任务）→ 临时方案（改投 dedicated agent / writer）
- **任务落盘竞争**：症状（ENOENT rename）→ 根因（A2A 任务目录并发操作）→ 修复（重试）

### 需要避免的做法
- 不要对 A2A Gateway 的 main agent 路由发送耗时 > 30s 的任务
- 不要重复尝试同质方案（同步→异步→极短，本质同一问题）
- 不要假设 A2A 任务失败是授权问题（实际是超时）

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **评估任务复杂度** — 预估耗时 < 30s → 可以走 main agent；> 30s → 走 dedicated agent
2. **选择路由** — 简单任务 → main agent；复杂任务 → dedicated agent（writer）
3. **非阻塞投递** — 始终使用 `--non-blocking`，避免入口超时
4. **监控状态** — 定期查询 task_id 状态
5. **失败处理** — 超时 → 切换 agent 重试

### 触发条件
- 需要通过 A2A Gateway 派发任务给其他 agent
- 任务涉及知识库操作、文档生成等耗时操作

### 前置条件
- A2A Gateway 运行中
- 目标 agent 有空闲 session
- 任务描述已准备好

### 预期结果
- 任务成功派发并完成
- 或在 30s 内返回明确的失败原因

### 回退方案
- main agent 超时 → 切换到 dedicated agent（writer）
- A2A 全部失败 → 直接在本地 agent 执行，不走 A2A
- 落盘错误 → 重试 + 检查 `~/.openclaw/a2a-tasks/` 目录
