---
id: sc-20260502-003
type: pattern
category: patterns
task_types:
  - 批量任务执行
  - API 限流处理
  - 并发控制
  - 子任务管理
avg_reward: 0.5
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
sources:
  - .learnings/ERRORS.md
  - .learnings/LEARNINGS.md
related_learnings:
  - ERR-20260225-001
  - LRN-20260225-003
  - LRN-20260225-004
planning_hints:
  common_failures:
    - pattern: "批量子任务全部失败"
      hint: "可能是并发过高触发 API 限流。先降并发到 2，监控错误率，再逐步调高"
    - pattern: "LLM provider 限流后长时间等待"
      hint: "不要空等配额恢复。准备本地 ollama 模型作为 fallback，限流时自动切换"
    - pattern: "负数 Runtime 被误判为 timeout"
      hint: "负数 Runtime = 任务未启动 = 系统级问题（限流/配额/资源），不是 timeout 配置问题"
  typical_approach: "从低并发开始（2），监控 API 错误率，根据配额动态调整；限流时切换本地模型"
  caveats:
    - "4 并发已证实触发 zai/glm-5 的日配额限制"
    - "批次间至少 5 分钟间隔可显著降低限流风险"
    - "日配额耗尽后等待时间不确定（可能 24h），必须准备 fallback"
---

# 并发与 API 限流管理模式

## ✅ 成功经验 (e_success)

### 有效的策略
- **保守起步**：初始并发设为 2（安全值），根据实际表现调整
- **批次间隔**：每批任务之间间隔 5 分钟，给 API 配额恢复时间
- **模型 fallback**：LLM 限流时自动切换到本地 ollama 模型

### 关键决策
- **并发数从 4 降到 2**：避免触发 zai/glm-5 的日配额限制
- **监控优先于假设**：监控 API 响应时间和错误率，而不是凭感觉调参

### 验证过的工具/方法
- 2 并发 + 5 分钟间隔：OntoFuel 任务稳定性显著提升
- ollama/qwen3-coder-next：本地 fallback 模型
- 每 30 分钟健康检查：及时发现异常

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **4 并发导致全量失败**：4 子任务 × 内部并发 = 总并发过高，触发 API 限流
- **负数 Runtime 误判**：以为是 timeout 配置问题，实际是启动失败（限流→配额耗尽→任务未启动）
- **无限期等待配额恢复**：zai/glm-5 日配额用尽后等了 24 小时

### 错误模式
- **并发过高**：症状（全部失败）→ 根因（API 限流 + 资源耗尽）→ 修复（降并发 + 加间隔）
- **Runtime 误判**：症状（timeout 报错）→ 根因（任务未启动，Runtime 负数）→ 修复（检查系统资源/配额）
- **无 fallback**：症状（长时间等待）→ 根因（无本地模型备选）→ 修复（配置 ollama fallback）

### 需要避免的做法
- 不要上来就用 4+ 并发
- 不要把负数 Runtime 当作 timeout 问题处理
- 不要空等 API 配额恢复

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **评估配额** — 确认 API provider 的日配额和频率限制
2. **保守配置** — 初始并发 = 2，批次间隔 = 5 分钟
3. **配置 fallback** — 准备本地 ollama 模型作为备选
4. **执行监控** — 每 30 分钟检查错误率和响应时间
5. **动态调整** — 根据监控数据调整并发和间隔
6. **异常处理** — 错误率 > 50% → 切换本地模型 + 降低并发

### 触发条件
- 需要批量执行 LLM 调用任务
- API 调用出现 429 或限流错误
- 子任务出现负数 Runtime

### 前置条件
- 知道 API provider 的配额限制
- 本地 ollama 已安装并可用
- 有监控和告警机制

### 预期结果
- 批量任务稳定完成
- 错误率 < 10%
- API 配额不耗尽

### 回退方案
- API 限流 → 切换本地 ollama 模型
- 任务未启动（Runtime 负数）→ 检查系统资源和配额
- 全量失败 → 降低并发到 1 + 增加间隔到 10 分钟
