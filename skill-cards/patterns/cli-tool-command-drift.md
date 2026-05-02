---
id: sc-20260502-001
type: pattern
category: patterns
task_types:
  - CLI 工具使用
  - ACP 调试
  - 命令行排错
  - 插件集成
avg_reward: 0.5
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
transfer_mode: indirect
sources:
  - .learnings/ERRORS.md
related_learnings:
  - ERR-20260320-001
  - ERR-20260420-002
planning_hints:
  common_failures:
    - pattern: "CLI 命令报 unknown option"
      hint: "先验证当前安装版本的子命令支持哪些参数，不要直接复制文档模板。用 <tool> <subcmd> --help 确认"
    - pattern: "skill 文档中的命令模板与实际行为不符"
      hint: "skill 文档可能滞后于实际版本，以本地 --help 输出为准，并更新 TOOLS.md 记录差异"
    - pattern: "全局选项和子命令选项混淆"
      hint: "像 acpx 的 --format、--cwd 是全局选项，不是子命令选项。放在子命令前面"
  typical_approach: "使用新 CLI 工具前，先用 --version 和 --help 验证可用参数，再执行实际命令"
  caveats:
    - "acpx 的 --cwd 和 --format 是全局选项，不能放在 codex exec 后面"
    - "acpx codex exec 不支持 --cwd，需要先 cd 再执行"
    - "Claude ACP + BigModel 目前不可用，优先用 Codex ACP"
---

# CLI 工具命令漂移与参数验证模式

## ✅ 成功经验 (e_success)

### 经验传递分级
```yaml
experiences:
  direct:
    - "acpx 0.5.3 的 --format 和 --cwd 是全局选项，不是子命令选项"
    - "acpx codex exec 不支持 --cwd，必须 cd 再执行"
    - "Claude ACP + BigModel 不兼容，Agent SDK 握手成功但执行挂死"
  indirect:
    - "使用新 CLI 工具前先 --version + --help 验证可用参数"
    - "外部工具命令行参数位置需查文档确认，不假设跨版本兼容"
    - "分层测试：版本确认 → 参数验证 → 最小连通 → 完整命令"
  forbidden:
    - "具体命令见 e_workflow（如 acpx --format quiet codex exec 'Reply OK'）"
```

### 有效的策略
- **先验证后使用**：运行 `--version` 和 `--help` 确认可用参数，再执行实际命令
- **分层测试**：`codex --version` → `acpx --version` → 最小连通测试 → 完整命令
- **本地记录差异**：在 TOOLS.md 中维护实际命令格式与文档的差异

### 关键决策
- **遇到 unknown option 立即停止**：不猜测参数格式，先查 help
- **用 `cd` 替代 `--cwd`**：acpx codex exec 不支持 --cwd，改用 shell cd

### 验证过的工具/方法
- acpx 0.5.3：`--format quiet` 是全局选项
- Codex ACP：`acpx --format quiet codex exec "prompt"` 格式正确
- Claude ACP：BigModel 环境下不可用，直接排除

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **acpx codex exec --cwd 报错**：--cwd 不是 exec 子命令的选项
- **acpx codex exec --format quiet 报错**：--format 是全局选项，不能放在子命令后
- **Claude ACP + BigModel 挂起**：握手成功但执行挂死，BigModel 不兼容 Claude Agent SDK
- **Skill 文档模板过时**：acp-router skill 的命令模板与 acpx 0.5.3 不匹配

### 错误模式
- **全局/子命令选项混淆**：症状（unknown option）→ 根因（全局选项放到子命令后）→ 修复（移到子命令前或用 cd）
- **Provider 兼容性**：症状（ACP 握手成功但挂起）→ 根因（BigModel 不兼容 Claude Agent SDK）→ 修复（排除该组合）

### 需要避免的做法
- 不要直接复制 skill 文档中的命令模板
- 不要假设 CLI 工具参数在不同版本间不变
- 不要在 Claude ACP + BigModel 组合上浪费时间

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **版本确认** — `<tool> --version` 确认安装版本
2. **参数验证** — `<tool> <subcmd> --help` 查看支持的参数
3. **最小测试** — 用最简命令验证连通性（如 `acpx --format quiet codex exec "Reply OK"`）
4. **逐步扩展** — 在最小测试基础上添加参数
5. **记录差异** — 发现与文档不符时，更新 TOOLS.md

### 触发条件
- 使用新 CLI 工具或升级后首次使用
- 命令执行报 unknown option
- Skill 文档中的命令模板执行失败

### 前置条件
- 目标工具已安装
- 能访问 --help 输出

### 预期结果
- 确认可用的命令格式
- 文档与实际的差异已记录
- 最小连通测试通过

### 回退方案
- 参数不支持 → 查 help 找替代方案或用 cd 替代 --cwd
- Provider 不兼容 → 切换到已知可用的组合
- 工具版本过旧 → 升级或适配命令格式
