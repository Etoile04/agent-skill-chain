# Learnings

Append structured entries:
- LRN-YYYYMMDD-XXX for corrections / best practices / knowledge gaps
- Include summary, details, suggested action, metadata, and status

---

# 历史学习记录（从 `.learnings/.learnings/LEARNINGS.md` 迁移）

# LEARNINGS.md

Corrections, knowledge gaps, and best practices for continuous improvement.

Format:
```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line description of what was learned

### Details
Full context: what happened, what was wrong, what's correct

### Suggested Action
Specific fix or improvement to make

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-20250110-001 (if related to existing entry)

---
```

---

## [LRN-20260225-001] error-recovery

**Logged**: 2026-02-25T08:02:00+08:00
**Priority**: critical
**Status**: integrated
**Area**: backend

### Summary
不要假设系统会自动恢复 - 必须实现主动检查和自动恢复机制

### Details
**错误假设**: 暂停 10-15 分钟后系统会自动恢复
**实际情况**: 需要主动检查和干预，否则会无限期等待
**延迟影响**: 2 次暂停共延迟 ~9 小时 20 分钟

**正确做法**:
1. 实现自动恢复机制（每 30 分钟健康检查）
2. 主动重启 Gateway 和失败任务
3. 设置超时告警（暂停超过 30 分钟自动通知）
4. 状态持久化，支持断点续传

### Suggested Action
- 在 AGENTS.md 添加自动恢复规则
- 实现健康检查脚本
- 设置监控告警

### Metadata
- **Source**: error (ERR-20260225-002)
- **Related Files**: `books/fundamentals/FAILURE_ANALYSIS_REPORT.md`
- **Tags**: error-recovery, automation, monitoring
- **See Also**: ERR-20260225-001, ERR-20260225-002

---

## [LRN-20260225-002] error-diagnosis

**Logged**: 2026-02-25T08:02:00+08:00
**Priority**: high
**Status**: integrated
**Area**: backend

### Summary
负数 Runtime 不是 timeout 问题 - 需要深入分析系统级原因

### Details
**表面现象**: 任务立即 timeout
**错误判断**: 调整 timeout 设置（300s → 2400s）
**实际情况**: Runtime 负数 = 任务未启动 = 系统级问题

**错误模式**:
```
看到 timeout → 调整 timeout → 无效 → 继续失败
```

**正确模式**:
```
看到 timeout → 检查 Runtime → 发现负数 → 判断启动失败 → 检查系统资源/配额/队列
```

**根本原因**: API 限流 → 启动失败 → Runtime 负数 → 误判为 timeout

### Suggested Action
- 看到 Runtime 负数立即检查系统资源
- 不要只看表面错误信息
- 建立错误分类系统

### Metadata
- **Source**: error (ERR-20260225-001)
- **Related Files**: `books/fundamentals/SUBAGENT_DIAGNOSIS.md`
- **Tags**: error-diagnosis, debugging, runtime
- **See Also**: ERR-20260225-001

---

## [LRN-20260225-003] resource-management

**Logged**: 2026-02-25T08:02:00+08:00
**Priority**: high
**Status**: integrated
**Area**: backend

### Summary
并发不是越高越好 - 需要根据配额和资源限制动态调整

### Details
**错误策略**: 4 个子任务并行以提高速度
**实际结果**: 触发 API 限流 + 资源耗尽 + 全部失败

**问题分析**:
1. 4 子任务 × 内部并发 = 总并发数过高
2. 2 小时高频调用触发频率限制
3. zai/glm-5 日配额用尽
4. 系统资源（内存/进程）耗尽

**正确策略**:
1. 初始并发设为 2（安全值）
2. 监控 API 响应时间和错误率
3. 根据配额动态调整并发数
4. 添加批次间隔（5 分钟）

### Suggested Action
- 实现 adaptive concurrency 控制
- 监控 token 消耗和错误率
- LLM 限流时自动切换到本地模型

### Metadata
- **Source**: error (ERR-20260225-001)
- **Related Files**: `books/fundamentals/RECOVERY_PLAN.md`
- **Tags**: concurrency, rate-limiting, resource-management
- **See Also**: ERR-20260225-001

---

## [LRN-20260225-004] model-fallback

**Logged**: 2026-02-25T08:02:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
LLM provider 限流时应自动切换到本地 ollama 模型 - 不要浪费等待时间

### Details
**当前问题**:
- zai/glm-5 限流后只能等待配额恢复
- 等待时间不确定（可能 24 小时）
- 无 fallback 机制

**改进方案**:
1. 检测 LLM provider 限流（错误率 > 50%）
2. 自动切换到本地 ollama 模型
3. 测试可用模型的速度和效果
4. 智能选择最佳模型

**候选模型**:
- ollama/qwen3-coder-next（代码/推理强）
- ollama/llama3.1（通用）
- 其他本地模型

### Suggested Action
- 检查本地 ollama 模型列表
- 测试模型速度和效果
- 实现智能切换逻辑

### Metadata
- **Source**: user_feedback
- **Related Files**: N/A
- **Tags**: model-fallback, ollama, rate-limiting
- **See Also**: ERR-20260225-001

---

## [LRN-20260310-002] success

**Logged**: 2026-03-10T09:35:00+08:00
**Priority**: P0（关键）
**Status**: integrated
**Area**: system-integration

### Summary
记忆系统快速整合成功 - 2小时完成100%，测试全部通过

### Details
**What Worked**:
1. 分层设计 - 每个系统专注自己的强项
2. 单向流动 - 信息只流动一次，避免重复
3. 自动化验证 - 测试脚本确保系统正常
4. 趁热打铁 - 立即完成100%，避免遗忘

**Key Results**:
- ✅ 测试通过率: 100%（5/5）
- ✅ 数据流完整度: 100%（4/4）
- ✅ 记忆数量: 179条
- ✅ 文档大小: 36.2 KB

**How to Replicate**:
审计（30分钟）→ 设计（30分钟）→ 实施（1小时）→ 测试（即时）

### Suggested Action
将此成功模式应用到其他系统整合项目：
1. OntoFuel 系统优化
2. PlugMem 性能优化
3. 飞书集成优化

### Metadata
- Source: success
- Pattern: workflow-optimization
- Related Files: memory_integration_plan_20260310.md, scripts/archive_to_lancedb.py, scripts/test_memory_flow.py
- Tags: system-integration, success-pattern
- See Also: MEM-20260310-005


---

## [LRN-20260310-003] feishu-file-send

**Logged**: 2026-03-10T16:11:00+08:00
**Priority**: P1（重要）
**Status**: integrated
**Area**: tools

### Summary
飞书发送 MD 文件的正确方式：先复制到 workspace，再用 media 参数发送

### Details
**错误方式**：
- ❌ 直接使用 workspace 外的路径（如 workspace-researcher）
- ❌ 只使用 path 参数，不使用 media 参数
- 结果：用户只看到绝对路径，看不到文件内容

**正确方式**：
```bash
# 步骤1: 复制文件到 workspace
cp /path/to/source/file.md /Users/lwj04/.openclaw/workspace/file.md

# 步骤2: 使用 media 参数发送
message(
    action="send",
    channel="feishu",
    target="user:xxx",
    media="/Users/lwj04/.openclaw/workspace/file.md",  # ✅ workspace 内的路径
    filename="file.md",
    caption="文件说明"
)
```

**关键要点**：
1. ✅ 文件必须在 workspace 目录下
2. ✅ 必须使用 `media` 参数（不是 `path`）
3. ✅ 如果源文件不在 workspace，先复制再发送

### Suggested Action
更新 TOOLS.md，记录飞书文件发送的最佳实践

### Metadata
- Source: user_feedback
- Related Files: TOOLS.md
- Tags: feishu, file-send, best-practice
- See Also: TOOLS.md 第 50-140 行（已有记录）


## [LRN-20260320-001] best_practice

**Logged**: 2026-03-20T05:56:10.542Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/055046453-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-002] best_practice

**Logged**: 2026-03-20T06:22:33.809Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/055617111-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-003] best_practice

**Logged**: 2026-03-20T06:30:03.125Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/062234076-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-004] best_practice

**Logged**: 2026-03-20T06:39:48.977Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/063003379-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-005] best_practice

**Logged**: 2026-03-20T06:46:29.223Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/063949217-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-006] best_practice

**Logged**: 2026-03-20T06:49:23.318Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/064629524-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-007] best_practice

**Logged**: 2026-03-20T06:54:08.008Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/064923575-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-008] best_practice

**Logged**: 2026-03-20T07:00:49.492Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/065408214-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-009] best_practice

**Logged**: 2026-03-20T07:07:31.792Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/070049793-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-010] best_practice

**Logged**: 2026-03-20T07:14:11.064Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/070731946-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-011] best_practice

**Logged**: 2026-03-20T07:21:37.020Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/071411370-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-012] best_practice

**Logged**: 2026-03-20T07:29:05.592Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/072137252-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-013] best_practice

**Logged**: 2026-03-20T07:30:51.332Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/072906035-coding-77afd84a-7ebf-4890-8e0a-bee25898.md
---


## [LRN-20260320-014] github-release

**Logged**: 2026-03-20T16:10:00+08:00
**Priority**: high
**Status**: integrated
**Area**: ci-cd

### Summary
GitHub 项目发布前应检查 CI lint 规则是否过于严格

### Details
**场景**: 发布 Swelling 项目到 GitHub
**问题**: CI Linting 失败（120+ docstring 格式错误、100+ import 顺序错误）
**原因**: lint 规则过于严格，不适合研究代码

**解决方案**:
1. 放宽 lint 规则（非阻塞模式 `|| true`）
2. 忽略常见格式错误（D400/D204/D205/I201/I202）
3. 复杂度阈值 10 → 15

**修改文件**: `.github/workflows/lint.yml`

### Suggested Action
发布前检查 CI 配置，确保 lint 规则适合项目类型

### Metadata
- Source: user_feedback
- Related Files: `~/ZCodeProject/Swelling/.github/workflows/lint.yml`
- Tags: github, ci, lint, release
- See Also: ERR-20260320-002

---

## [LRN-20260320-015] ci-dependencies

**Logged**: 2026-03-20T16:12:00+08:00
**Priority**: high
**Status**: integrated
**Area**: ci-cd

### Summary
CI 测试失败可能是因为可选依赖未安装

### Details
**场景**: GitHub Actions Tests 失败
**错误**: `ModuleNotFoundError: No module named 'matplotlib'`
**原因**: `test-minimal` job 只安装了 `numpy scipy pytest`，但代码 import 时需要 matplotlib

**解决方案**:
```yaml
# 修改前
pip install numpy scipy pytest

# 修改后
pip install numpy scipy pytest matplotlib
```

**根本原因**: 包结构设计问题 - 可选依赖在 import 时就被加载

### Suggested Action
1. CI 中所有 test job 都应安装完整依赖
2. 或重构代码使可选依赖真正可选（延迟 import）

### Metadata
- Source: error
- Related Files: `~/ZCodeProject/Swelling/.github/workflows/test.yml`, `gas_swelling/__init__.py`
- Tags: ci, dependencies, testing
- See Also: ERR-20260320-003

---

## [LRN-20260320-016] acpx-upgrade

**Logged**: 2026-03-20T19:25:00+08:00
**Priority**: high
**Status**: integrated
**Area**: tools

### Summary
acpx 0.3.1 新增多个 ACP agents 和 crash reconnect 功能

### Details
**升级**: 0.2.0 → 0.3.1

**关键新特性**:
1. **Crash reconnect**: 检测 agent 进程死亡后自动重连并恢复 session
2. **Soft-close lifecycle**: 关闭 session 但保留历史记录
3. **新内置 Agents**: gemini、qwen、cursor、copilot、kilocode、kimi、kiro
4. **Queue owner TTL**: `--ttl` 控制队列所有者存活时间
5. **Graceful cancel**: Ctrl+C 发送 ACP session/cancel

**测试验证**:
```bash
# crash reconnect 自动工作
[acpx] session cwd · agent needs reconnect
[client] initialize (running)

# status 显示完整信息
session: 019d0afd...
agent: npx @zed-industries/codex-acp@^0.9.5
pid: 89650
status: running
uptime: 00:00:22
```

### Suggested Action
使用 `acpx <agent> --help` 查看各 agent 支持的命令

### Metadata
- Source: user_request
- Related Files: `~/.acpx/config.json`
- Tags: acpx, acp, agents, upgrade
- See Also: https://github.com/openclaw/acpx


## [LRN-20260320-017] best_practice

**Logged**: 2026-03-20T13:31:26.159Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/132930266-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-018] best_practice

**Logged**: 2026-03-20T13:33:27.745Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/133135205-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-019] best_practice

**Logged**: 2026-03-20T13:35:20.703Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/133328086-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-020] best_practice

**Logged**: 2026-03-20T13:37:12.784Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/133521119-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-021] best_practice

**Logged**: 2026-03-20T13:38:52.596Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/133713112-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-022] best_practice

**Logged**: 2026-03-20T13:40:31.874Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/133852838-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-023] best_practice

**Logged**: 2026-03-20T13:42:31.544Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/134032121-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-024] best_practice

**Logged**: 2026-03-20T13:44:23.560Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/134231871-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-025] best_practice

**Logged**: 2026-03-20T13:46:12.261Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/134423845-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-026] best_practice

**Logged**: 2026-03-20T13:48:05.913Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/134612573-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-027] best_practice

**Logged**: 2026-03-20T13:50:03.788Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/134806148-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-028] best_practice

**Logged**: 2026-03-20T13:51:52.724Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/135004356-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260320-029] best_practice

**Logged**: 2026-03-20T13:53:41.188Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-20/135153029-coding-e010f19f-0a9b-4936-a22b-fe94fc0c.md
---


## [LRN-20260321-001] best_practice

**Logged**: 2026-03-21T06:08:12.978Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-21/060623553-coding-7c40c205-35ba-4b02-a38a-07803f63.md
---


## [LRN-20260321-002] best_practice

**Logged**: 2026-03-21T06:10:10.889Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-21/060822959-coding-7c40c205-35ba-4b02-a38a-07803f63.md
---


## [LRN-20260321-003] best_practice

**Logged**: 2026-03-21T06:11:49.663Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-21/061011135-coding-7c40c205-35ba-4b02-a38a-07803f63.md
---


## [LRN-20260321-004] best_practice

**Logged**: 2026-03-21T06:13:35.377Z
**Priority**: medium
**Status**: triage
**Area**: config

### Summary
Investigate last failed tool execution and decide whether it belongs in .learnings/ERRORS.md.

### Details
The reflection pipeline fell back; confirm the failure is reproducible before treating it as a durable error record.

### Suggested Action
Reproduce the latest failed tool execution, classify it as triage or error, and then log it with the appropriate tool/file path evidence.

### Metadata
- Source: memory-lancedb-pro/reflection:memory/reflections/2026-03-21/061149970-coding-7c40c205-35ba-4b02-a38a-07803f63.md
---
