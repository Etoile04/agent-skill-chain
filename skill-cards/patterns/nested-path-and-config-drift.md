---
id: sc-20260502-005
type: pattern
category: patterns
task_types:
  - 文件路径问题
  - 配置管理
  - 系统初始化
  - 记忆系统维护
avg_reward: 0.5
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
transfer_mode: indirect
sources:
  - .learnings/ERRORS.md
related_learnings:
  - ERR-20260319-001
  - ERR-20260319-002
  - ERR-20260319-003
planning_hints:
  common_failures:
    - pattern: "read ENOENT：期望的文件不存在"
      hint: "先验证文件系统实际状态，再报告。创建缺失的基线文件（memory/、daily notes、heartbeat state）"
    - pattern: "嵌套 .learnings 目录导致记录分裂"
      hint: "写入前验证目标路径。.learnings/ 是唯一的规范路径，不允许 .learnings/.learnings/"
    - pattern: "CLI JSON 输出被插件日志污染"
      hint: "用 grep -v 过滤非 JSON 行，或写解析器提取 JSON 尾部，不假设纯 JSON stdout"
  typical_approach: "操作前验证文件/目录是否存在和正确；系统初始化时创建所有基线文件"
  caveats:
    - "AGENTS.md 规则引用的文件可能尚未创建，需要先创建再使用"
    - "openclaw CLI 的 --json 输出可能混合插件日志"
---

# 嵌套路径与配置漂移模式

## ✅ 成功经验 (e_success)

### 经验传递分级
```yaml
experiences:
  direct:
    - ".learnings/ 是唯一的规范路径，不允许嵌套的 .learnings/.learnings/"
  indirect:
    - "操作前验证文件/目录是否存在和正确"
    - "系统初始化时创建所有基线文件"
  forbidden:
    - "具体文件路径和命令见 e_workflow"
```

### 有效的策略
- **操作前验证**：读/写文件前先验证路径存在和正确
- **基线文件初始化**：系统初始化时创建所有需要的目录和文件
- **路径验证规则**：在 AGENTS.md 中明确规范路径

### 关键决策
- **.learnings/ 为唯一规范路径**：不允许嵌套的 .learnings/.learnings/
- **过滤非 JSON 输出**：`grep -v '^\[plugins\]'` 清理 CLI 输出

### 验证过的工具/方法
- `ls -la` 验证目录结构
- `grep -v` 过滤 CLI 输出
- `mkdir -p` 确保目录存在

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- **memory/config 文件缺失**：workspace 规则引用了未创建的文件
- **嵌套 .learnings 目录**：早期操作写入了 .learnings/.learnings/ 而非 .learnings/
- **JSON 解析失败**：CLI 输出混合了插件日志和 JSON

### 错误模式
- **路径漂移**：症状（ENOENT）→ 根因（规则引用未创建的文件）→ 修复（创建基线文件）
- **嵌套目录**：症状（记录分裂/内容不一致）→ 根因（写入错误嵌套路径）→ 修复（迁移到规范路径）

### 需要避免的做法
- 不要假设规则引用的文件都已存在
- 不要写入嵌套的 .learnings/.learnings/ 路径
- 不要假设 CLI --json 输出是纯 JSON

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. **验证文件系统** — 检查期望的目录和文件是否存在
2. **创建基线** — 创建所有缺失的目录和文件
3. **验证路径** — 写入前确认目标是规范路径（不是嵌套路径）
4. **过滤输出** — 处理 CLI 输出时过滤非目标内容
5. **定期审计** — 检查是否有漂移的路径或分裂的记录

### 触发条件
- read 返回 ENOENT
- 发现嵌套的重复目录
- CLI JSON 解析失败

### 前置条件
- 知道规范目录结构
- 有创建目录/文件的权限

### 预期结果
- 所有期望的文件和目录存在
- 记录只写入规范路径
- CLI 输出可正确解析

### 回退方案
- 文件缺失 → 创建基线文件
- 嵌套路径 → 迁移内容到规范路径，删除嵌套目录
- JSON 混合输出 → 用 grep/jq 过滤提取
