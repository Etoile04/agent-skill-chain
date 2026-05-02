---
id: sc-20260502-002
type: pattern
category: patterns
task_types:
  - 飞书文件发送
  - 消息发送
  - 文件路径问题
  - API 错误排查
avg_reward: 0.5
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
transfer_mode: indirect
sources:
  - .learnings/ERRORS.md
related_learnings:
  - ERR-20260303-001
  - ERR-20260323-001
  - LRN-20260310-003
planning_hints:
  common_failures:
    - pattern: "LocalMediaAccessError: path not under allowed directory"
      hint: "飞书文件发送只允许 workspace 目录下的文件，/tmp、/var、Downloads 等全部被拦截。先 cp 到 workspace 再发送"
    - pattern: "open_id cross app 错误"
      hint: "目标用户的 open_id 与发送账号的 app_id 不匹配。检查是否用了正确的 --account 参数"
    - pattern: "文件发送后用户打不开"
      hint: "用了 path 参数而非 media 参数，或文件不在允许目录下。确认用 media 参数 + workspace 路径"
  typical_approach: "发送前先检查：1) 文件路径在 workspace 下 2) 使用 media 参数 3) --account 与目标用户匹配"
  caveats:
    - "允许目录：/Users/lwj04/.openclaw/workspace/ 及其子目录"
    - "禁止目录：/tmp、/var、/Users/lwj04/Downloads 等非 workspace 目录"
    - "不同 Feishu 账号有不同的 allowFrom 列表，需确认账号匹配"
---

# 飞书文件发送路径限制模式

## ✅ 成功经验 (e_success)

### 经验传递分级
```yaml
experiences:
  direct:
    - "飞书文件发送只允许 workspace 目录下的文件，/tmp、/var 等全部被拦截"
    - "open_id 与 app_id 必须匹配，cross app 错误说明账号不匹配"
  indirect:
    - "发送前先检查三件事：1) 路径在 workspace 下 2) 用 media 参数 3) account 匹配"
  - "统一文件流转路径：源文件 → cp 到 workspace → media 参数发送"
  forbidden:
    - "具体路径和命令见 e_workflow"
```

### 有效的策略
- **Workspace 内操作**：所有待发送文件先复制到 workspace 目录下
- **media 参数发送**：使用 `media` 参数（不是 `path`）发送文件
- **Account 匹配检查**：发送前确认 `--account` 与目标用户的 allowFrom 匹配

### 关键决策
- **统一文件流转路径**：源文件 → cp 到 workspace → media 参数发送
- **错误快速定位**：看到 LocalMediaAccessError 立即知道是路径问题

### 验证过的工具/方法
- `message(action="send", channel="feishu", target="user:xxx", media="/Users/lwj04/.openclaw/workspace/file.md")`
- `--account coding` 用于 coding bot 的 allowFrom 用户

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **直接用 /tmp 路径发送**：被 LocalMediaAccessError 拦截
- **用 path 参数代替 media**：用户只看到绝对路径，看不到文件内容
- **用错了 Feishu 账号**：默认账号的 app_id 与目标 open_id 不匹配

### 错误模式
- **路径限制**：症状（LocalMediaAccessError）→ 根因（文件不在 workspace 目录）→ 修复（cp 到 workspace）
- **Account 不匹配**：症状（open_id cross app）→ 根因（用了错误的 Feishu account）→ 修复（--account coding）

### 需要避免的做法
- 不要直接用 /tmp、/var 等非 workspace 目录的文件发送
- 不要用 path 参数代替 media 参数发送文件
- 不要假设默认 Feishu 账号能发给所有用户

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **确认源文件路径** — 检查文件是否在 workspace 目录下
2. **必要时复制** — `cp /source/file.md /Users/lwj04/.openclaw/workspace/file.md`
3. **确认目标账号** — 检查目标用户的 open_id 属于哪个 account 的 allowFrom
4. **发送文件** — 使用 `media` 参数 + 正确的 `--account`
5. **验证结果** — 确认返回的 mediaUrl 有值（非 null）

### 触发条件
- 需要通过飞书发送文件给用户
- 收到 LocalMediaAccessError
- 收到 open_id cross app 错误

### 前置条件
- 文件存在且可读
- 知道目标用户的 open_id
- 知道目标用户属于哪个 Feishu account

### 预期结果
- 文件成功发送
- 用户能正常打开文件
- mediaUrl 返回有效值

### 回退方案
- 路径错误 → cp 到 workspace 重试
- Account 不匹配 → 切换 --account 或将用户添加到目标 account 的 allowFrom
- 用户无 DM 会话 → 先发送文本消息建立 DM，再发文件
