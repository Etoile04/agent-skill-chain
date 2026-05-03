# Errors

Append structured entries:
- ERR-YYYYMMDD-XXX for command/tool/integration failures
- Include symptom, context, probable cause, and prevention

## ERR-20260319-001 read ENOENT due to expected memory/config files missing
- **Date:** 2026-03-19
- **Symptom:** `read` returned ENOENT when checking `memory/YYYY-MM-DD.md`, `MEMORY.md`, and `SELF_IMPROVEMENT_REMINDER.md` during memory-system inspection.
- **Context:** Workspace rules expected daily memory files and reminder file, but filesystem state was incomplete/inconsistent.
- **Probable cause:** Memory bootstrap/config drift: rules referenced files that had not been created yet or were injected from another source.
- **Prevention:** Before reporting on memory status, verify actual filesystem state, create missing baseline files (`memory/`, daily notes, heartbeat state, reminder file), and distinguish missing files from disabled modules.

## ERR-20260319-002 nested .learnings directory caused split records
- **Date:** 2026-03-19
- **Symptom:** `.learnings/ERRORS.md` and `.learnings/LEARNINGS.md` in the root had only minimal content, while the real historical records lived under `.learnings/.learnings/`.
- **Context:** During memory-system cleanup, the learnings directory showed a nested duplicate structure with divergent content.
- **Probable cause:** Earlier file operations wrote into `.learnings/.learnings/` instead of `.learnings/`, creating two active-looking locations.
- **Prevention:** Keep `.learnings/` as the sole canonical write target, verify exact destination paths before writes, and migrate nested content before any deletion.

## ERR-20260319-003 memory-pro JSON output mixed with plugin logs
- **Date:** 2026-03-19
- **Symptom:** `openclaw memory-pro ... --json | python3 -m json.tool` failed because stdout contained plugin log lines before JSON payload.
- **Context:** While validating `memory-pro stats/list/search`, CLI output included `[plugins] ...` registration logs, which broke downstream JSON parsing.
- **Probable cause:** The CLI emits plugin initialization logs to stdout alongside command JSON output instead of isolating logs on stderr.
- **Prevention:** When scripting against `openclaw memory-pro --json`, filter leading plugin log lines first (for example `grep -v '^\[plugins\]'`) or use a parser that extracts the JSON tail instead of assuming pure JSON stdout.

## ERR-20260320-001 acpx codex exec rejected --cwd
- **Date:** 2026-03-20
- **Symptom:** direct Codex ACP smoke-test command failed with `error: unknown option '--cwd'`.
- **Context:** While debugging a transient Codex ACP stall, I used `acpx codex exec --cwd /Users/lwj04/.openclaw/workspace-coding "..."` based on a generic command template.
- **Probable cause:** Current plugin-local `acpx` (`0.1.16`) supports `codex exec [prompt...]` but that subcommand does not implement `--cwd`.
- **Prevention:** For one-shot Codex ACP runs, `cd` into the target directory first, then run `acpx codex exec "..."`. Validate subcommand flags with `acpx codex exec --help` before assuming parity with other wrappers.

## ERR-20260420-001 Claude ACP hangs with BigModel despite successful handshake
- **Date:** 2026-04-20
- **Symptom:** Claude ACP sessions initialize successfully, but prompt execution hangs after handshake with no useful output. OpenClaw/acpx shows session creation followed by stalled `initialize/session/new` flow; direct `claude -p` with the same BigModel env also does not yield a usable result in this environment.
- **Context:** Investigated Codex vs Claude Code skills/plugins. Codex ACP passed, but Claude ACP failed while using only a BigModel API key and preferred model `glm-5.1`.
- **Probable cause:** BigModel's Anthropic-compatible endpoint supports basic `/v1/messages` requests but appears incompatible with the fuller Claude Agent SDK / Claude ACP runtime behavior required by `claude-agent-acp`.
- **Prevention:** Treat BigModel + Claude ACP as unsupported on this host unless revalidated. Prefer Codex for ACP tasks. If Claude must be retried later, first test direct `/v1/messages`, then wrapper startup, then Claude ACP handshake, and only then full prompt execution. Keep the Claude wrapper pinned to a local binary and inspect `/Users/lwj04/.openclaw/workspace/logs/claude-acp-wrapper.log` during diagnostics.

## ERR-20260420-002 acpx skill examples drift from installed acpx behavior
- **Date:** 2026-04-20
- **Symptom:** Skill-guided command templates using `acpx codex ... --format quiet` failed with `error: unknown option '--format'` under installed `acpx 0.5.3`.
- **Context:** While doing live ACP connectivity tests, the documented command shape in the skill did not match the actual local CLI behavior.
- **Probable cause:** Skill documentation drifted ahead of or away from the pinned plugin-local `acpx` version.
- **Prevention:** Before using acpx flags from skill docs, verify with `acpx <agent> --help` or the relevant subcommand help on the current host. Update local notes when command examples are known to differ from the installed version.

## ERR-20260323-001 Feishu file send "open_id cross app" error
- **Date:** 2026-03-23
- **Symptom:** `openclaw message send --channel feishu --target "user:ou_xxx"` returns `code: 99992361, msg: 'open_id cross app'`
- **Context:** Trying to send file to Feishu DM without specifying account
- **Probable cause:** Default Feishu account's app_id doesn't match the target user's open_id tenant. The user `ou_b4105949f5b379242915c66f296f801f` is in `coding` account's allowFrom but NOT in `default` account's allowFrom.
- **Prevention:** 
  - Option 1: Use `--account coding` when sending to users in that account's allowFrom list
  - Option 2: Add the user to `default` account's allowFrom list via `openclaw config set channels.feishu.accounts.default.allowFrom`
  - Note: `--account coding` sends via coding bot (appId: cli_a93186a335f8dcee), user must have DM session with coding bot to receive messages

---

# 历史错误记录（从 `.learnings/.learnings/ERRORS.md` 迁移）

# 错误记录

> 记录错误和教训，避免重复犯错

---

## ERR-20260303-001: 飞书文件发送路径错误

**日期**: 2026-03-03 17:00-17:05
**严重程度**: P1（重要）
**影响**: 用户无法打开发送的文件

### 问题描述

发送 MD 文件到飞书时，用户收到无法打开的链接，或看到 `LocalMediaAccessError`。

### 根本原因

**两个关键问题**：

1. **路径不在允许目录下**：
   - ❌ 错误：`/tmp/test.md`、`/var/data/file.md`
   - ✅ 正确：`/Users/lwj04/.openclaw/workspace/...`

2. **错误信息**：
   ```
   LocalMediaAccessError: Local media path is not under an allowed directory: /tmp/test.md
   ```

### 技术细节

**错误调用**:
```python
# ❌ 错误：文件不在允许目录下
message(
    action="send",
    channel="feishu",
    target="user:xxx",
    media="/tmp/test.md",  # ❌ 不在允许目录
    filename="测试.md"
)
```

**错误信息**:
```
LocalMediaAccessError: Local media path is not under an allowed directory: /tmp/test.md
```

**正确调用**:
```python
# ✅ 正确：文件在 workspace 目录下
message(
    action="send",
    channel="feishu",
    target="user:xxx",
    media="/Users/lwj04/.openclaw/workspace/reports/test.md",  # ✅ 在允许目录
    filename="测试.md"
)
```

**返回结果**:
```json
{
  "mediaUrl": "/Users/lwj04/.openclaw/workspace/reports/test.md",  // ✅ 有值
  "result": { "messageId": "om_x100b555..." }
}
```

### 修复措施

1. ✅ 识别问题：检查错误日志，发现 `LocalMediaAccessError`
2. ✅ 验证修复：将文件移动到 workspace 目录，测试成功
3. ✅ 更新文档：
   - `clawd/skills/feishu-md-sender/SKILL.md` (v1.1 → v1.2)
   - `TOOLS.md` 第 50-120 行
   - `MEMORY.md` Recent Achievements
4. ✅ 更新记忆：`memory/2026-03-03.md`
5. ✅ 重新发送文件：验证修复有效

### 预防措施

1. **路径检查**：发送前确认文件在 workspace 目录下
2. **使用绝对路径**：始终使用 `/Users/lwj04/.openclaw/workspace/...`
3. **文档优先**：参考 TOOLS.md 中的成功案例
4. **测试先行**：新功能先用小文件测试

### 允许的目录

**✅ 允许**：
- `/Users/lwj04/.openclaw/workspace/` 及其所有子目录

**❌ 禁止**：
- `/tmp`
- `/var`
- `/Users/lwj04/Downloads`
- 其他任何非 workspace 目录

### 影响范围

- ✅ 已修复：主技能文档
- ✅ 已同步：workspace-extractor 技能文档
- ✅ 已通知：ontofuel-extractor 智能体

### 关键教训

1. **文件路径有限制**：不是所有目录都允许访问
2. **错误信息很重要**：`LocalMediaAccessError` 明确指出了问题
3. **验证返回值**：mediaUrl 应该有值，null 表示失败
4. **及时更新文档**：发现错误立即更新，避免再次踩坑

### 参考文档

- 技能文档：`clawd/skills/feishu-md-sender/SKILL.md`
- 配置文档：`TOOLS.md` 第 50-120 行
- 成功案例：2026-03-03 17:05 发送 PlugMem 演示总结
- 验证记录：`memory/2026-03-03.md`

---

## ERR-20260225-001: OntoFuel 任务连续失败（已修复）

**日期**: 2026-02-25
**严重程度**: P0（严重）
**影响**: OntoFuel 提取任务延迟 >12 小时

### 问题描述

OntoFuel 本体提取任务连续失败，导致整体进度严重延迟。

### 根本原因

1. **并发过高**：4 并发触发 API 限流
2. **负数 Runtime 误判**：启动失败被误认为 timeout
3. **缺少自动恢复**：暂停后未主动检查和干预
4. **LLM 限流**：未切换到本地模型

### 修复措施

1. ✅ 并发数：4 → 2
2. ✅ 批次间隔：0 → 5 分钟
3. ✅ 智能切换：限流时用 ollama 模型
4. ✅ 健康检查：每 30 分钟
5. ✅ 自动恢复：Gateway 重启 + 失败重试

### 关键教训

1. **不要假设自动恢复** - 暂停后必须主动检查
2. **负数 Runtime ≠ timeout** - 是启动失败，需检查资源
3. **并发不是越高越好** - 需要根据 API 限制调整
4. **LLM 限流时切换本地模型** - 不要浪费等待时间

---

*最后更新: 2026-03-03 17:05*
*维护者: Lily (PM)*

---

## [REF-20260311-TEST] 测试错误记录（流程验证）

**类型**: technical
**来源**: 系统配置
**严重程度**: P2（建议）

### Miss（发生了什么）
这是测试记录，用于验证统一错误记录流程。

### Root（为什么发生）
5-Why分析：
1. 为什么？→ 需要验证记忆系统整合
2. 为什么？→ 确保单向数据流正常工作
3. 为什么？→ 避免重复记录和信息不一致
4. 为什么？→ 提升错误记录效率
5. 为什么？→ **系统需要协调多个记忆层**

### Fix（如何修复）
预防规则（可执行）：
- [x] 统一模板创建
- [x] AGENTS.md 规则添加
- [ ] 完整流程测试

### Pattern（模式识别）
- 频率: 首次（测试）
- 状态: testing

### Metadata
- 记录时间: 2026-03-11 07:38
- 关联文件: scripts/test_error_flow.sh
- 标签: 测试, 流程验证
- See Also: memory_integration_plan_20260310.md

---

## [ERR-20260312-002] Codex CLI 连接失败（已解决）

**日期**: 2026-03-12 22:40
**严重程度**: P1（重要）
**影响**: 无法使用 Codex CLI 执行任务

### 问题描述

Codex CLI 尝试连接 `https://chatgpt.com/backend-api/codex/responses` 时失败：
- ERROR: stream disconnected before completion
- 错误重复多次（会话中观察到）

### 根本原因

**OpenAI Codex CLI 需要特殊访问权限**：
1. Codex CLI 是 OpenAI 官方的实验性 CLI
2. 不是所有 OpenAI API key 都能访问
3. 需要专属的 Codex 内部访问权限
4. 当前配置使用 OpenRouter 代理，但 Codex CLI 始终尝试连接 OpenAI 内部端点

### 修复措施

✅ **方案 3: 使用其他 provider**
- 用户已切换到其他 provider（如 Claude Code、本地模型）
- 问题已解决

### 预防措施

1. **检查访问权限**：使用 Codex CLI 前确认有 Codex 内部访问权限
2. **备选方案**：准备 acpx + Claude Code 或本地模型作为备选
3. **配置验证**：使用 `codex --version` 和测试命令验证连接

### 关键教训

1. **实验性工具有限制**：Codex CLI 需要特殊权限，不是标准 API key 就能用
2. **备选方案很重要**：多 provider 配置可快速切换
3. **错误模式识别**：重复的连接失败应立即记录

### 参考文档

- 会话记录: `memory/2026-03-12-1441.md`, `memory/2026-03-13-memory-docx-rules.md`
- 解决时间: 2026-03-12 22:49（用户选择方案 3）

---

*最后更新: 2026-03-15 09:40*
*维护者: Lily (PM)*

---

## [REF-20260315-TEST] 测试错误记录（流程验证）

**类型**: technical
**来源**: 系统配置
**严重程度**: P2（建议）

### Miss（发生了什么）
这是测试记录，用于验证统一错误记录流程。

### Root（为什么发生）
5-Why分析：
1. 为什么？→ 需要验证记忆系统整合
2. 为什么？→ 确保单向数据流正常工作
3. 为什么？→ 避免重复记录和信息不一致
4. 为什么？→ 提升错误记录效率
5. 为什么？→ **系统需要协调多个记忆层**

### Fix（如何修复）
预防规则（可执行）：
- [x] 统一模板创建
- [x] AGENTS.md 规则添加
- [ ] 完整流程测试

### Pattern（模式识别）
- 频率: 首次（测试）
- 状态: testing

### Metadata
- 记录时间: 2026-03-15 09:36
- 关联文件: scripts/test_error_flow.sh
- 标签: 测试, 流程验证
- See Also: memory_integration_plan_20260310.md

## [ERR-20260502-step-3-api-integration] StepResult 失败: 飞书 API 返回 99992361: open_id cross app

**类型**: technical
**来源**: 规划-执行分离管道
**严重程度**: P1（重要）

### Miss（发生了什么）
步骤 `step-3-api-integration` 执行失败。
- 错误信息: 飞书 API 返回 99992361: open_id cross app
- 已尝试方法: 使用默认 account 发送, 检查 target 格式, 尝试直接 API 调用
- 失败假设: 默认 account 的 app_id 与目标用户的 open_id 不在同一租户

### Root（为什么发生）
5-Why分析：
1. 为什么？→ 飞书 API 返回 99992361: open_id cross app
2. 为什么？→ 默认 account 的 app_id 与目标用户的 open_id 不在同一租户
3. 为什么？→ [待填写]
4. 为什么？→ [待填写]
5. 为什么？→ [待填写 — 根本原因]

### Fix（如何修复）
预防规则（可执行）：
- [ ] 分析错误信息: 飞书 API 返回 99992361: open_id cross app
- [ ] 检查相关工具/环境配置
- [ ] 验证前置条件是否满足

### Pattern（模式识别）
- 频率: 首次
- 状态: emerging

### Metadata
- 记录时间: 2026-05-02 16:16
- 关联步骤: step-3-api-integration
- 标签: [自动化, writeback-pipeline]
