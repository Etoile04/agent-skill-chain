# SESSION-STATE 任务状态扩展模板

> 用于规划-执行分离架构中的任务进度跟踪。
> 添加到 SESSION-STATE.md 的 `## 任务状态` 部分。

---

## 空模板

```markdown
## 任务状态 (规划-执行分离)

### 当前任务
- task: ""                    # 任务描述
- task_id: ""                 # 任务唯一标识（用于日志关联）
- mode: idle                  # idle | planning | executing | completed | failed
- current_step: ""            # 当前步骤 ID
- overall_approach: ""        # 策略偏好（来自 Planning Agent）

### 步骤进度
<!-- 格式: - [status] step-id: 描述 — 备注 -->
<!-- status: [x] 完成, [>] 执行中, [ ] 待执行, [-] 跳过, [!] 失败 -->
- [ ] step-1: (待规划)

### 回退历史
<!-- 格式: - [时间] step-id → 原因 → 调整策略 -->
（无）

### 经验检索结果
<!-- 规划阶段的经验摘要，仅 planning 模式可见 -->
- related_errors: []          # 来自 .learnings/ERRORS.md 的相关条目
- related_cards: []           # 来自 skill-cards/ 的匹配卡片
- active_warnings: []         # 当前活跃的风险提示
```

---

## 填充示例

### 示例 1: 正在执行中的复杂任务

```markdown
## 任务状态 (规划-执行分离)

### 当前任务
- task: "重构 memory 系统的存储层，从 LanceDB 迁移到 SQLite + 向量扩展"
- task_id: "memory-migration-20260502"
- mode: executing
- current_step: "step-3"
- overall_approach: "这类数据库迁移任务通常先建立新 schema，再逐模块迁移读写逻辑，每步后运行回归测试确认无数据丢失"

### 步骤进度
- [x] step-1: 设计新 SQLite schema — 产出 schemas/memory-v2.sql
- [x] step-2: 实现数据迁移脚本 — 产出 scripts/migrate-lancedb-to-sqlite.sh
- [>] step-3: 迁移 memory_store 模块的读写接口
- [ ] step-4: 迁移 memory_recall 模块
- [ ] step-5: 集成测试 + 回归验证
- [ ] step-6: 清理旧代码 + 更新文档

### 回退历史
- [2026-05-02 14:30] step-2 → 迁移脚本在大数据量下 OOM → 调整策略：改为分批迁移（每批 1000 条）
- [2026-05-02 15:15] step-3 → 发现 LanceDB 的向量搜索结果格式与预期不同 → 调整策略：先写适配层再迁移调用方

### 经验检索结果
- related_errors:
  - ERR-20260319-001: read ENOENT（文件不存在处理）
  - ERR-20260225-001: 并发过高触发 API 限流（迁移需控制批次大小）
- related_cards:
  - sc-20260426-001: A2A Gateway 调试工作流（多模块集成的验证策略）
- active_warnings:
  - "LanceDB 的 Python API 在大数据量下有内存泄漏风险"
  - "SQLite 的 WAL 模式需要手动检查点"
```

### 示例 2: 规划阶段

```markdown
## 任务状态 (规划-执行分离)

### 当前任务
- task: "为飞书多维表格实现批量导入功能"
- task_id: "bitable-import-20260502"
- mode: planning
- current_step: ""
- overall_approach: ""        # 待 Planning Agent 输出

### 步骤进度
<!-- 待规划完成后填写 -->
- [ ] (待规划)

### 回退历史
（无）

### 经验检索结果
- related_errors:
  - ERR-20260323-001: 飞书 open_id cross app（需确认 API 账号匹配）
- related_cards:
  - (未找到直接匹配的卡片)
- active_warnings:
  - "飞书 API 限流: 每秒 50 次（批量操作需要分批）"
  - "飞书多维表格单次写入上限 500 条"
```

### 示例 3: 已完成任务

```markdown
## 任务状态 (规划-执行分离)

### 当前任务
- task: "修复 OntoFuel 提取任务的并发限流问题"
- task_id: "ontofuel-fix-20260225"
- mode: completed
- current_step: ""
- overall_approach: "降低并发、增加间隔、添加健康检查和自动恢复"

### 步骤进度
- [x] step-1: 诊断限流原因 — 确认 4 并发触发 API 限流
- [x] step-2: 调整并发参数 — 并发 4→2，间隔 0→5min
- [x] step-3: 添加健康检查 — 每 30 分钟自动检查
- [x] step-4: 实现自动恢复 — Gateway 重启 + 失败重试
- [x] step-5: 验证修复 — 5 批次全部成功

### 回退历史
- [2026-02-25 03:20] step-2 → 初次调整到 3 并发仍然限流 → 进一步降至 2 并发

### 经验检索结果
（任务已完成，检索结果已通过 Learning Writeback 写入 .learnings/）
```

---

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `task` | string | 用户的原始任务描述 |
| `task_id` | string | 唯一标识，格式 `{任务简称}-{日期}` |
| `mode` | enum | `idle`（空闲）、`planning`（规划中）、`executing`（执行中）、`completed`（完成）、`failed`（失败） |
| `current_step` | string | 当前执行的步骤 ID，规划阶段为空 |
| `overall_approach` | string | Planning Agent 输出的策略偏好（不是具体命令） |
| 步骤进度 | list | 每步的状态、ID、描述和备注 |
| 回退历史 | list | 每次回退的时间、步骤、原因和策略调整 |
| 经验检索结果 | struct | 规划阶段检索到的相关错误、技能卡和风险提示 |

## 状态流转

```
idle → planning → executing → completed
                ↘ failed
                ↘ executing ⟲ (回退 → 重新 planning)
```

### 触发条件

| 转换 | 触发 |
|------|------|
| idle → planning | 复杂度评估判定为复杂任务 |
| planning → executing | StepPlan 生成完成 |
| executing → executing | 步骤完成，进入下一步 |
| executing → planning | 触发 fallback_trigger |
| executing → completed | 所有步骤完成 |
| executing → failed | 不可恢复的失败 |
| any → idle | 任务结束清理 |

## 与 SESSION-STATE.md 的集成

将此模板的 `## 任务状态` 部分追加到 SESSION-STATE.md 末尾。

SESSION-STATE.md 完整结构：

```markdown
# SESSION-STATE

## 当前上下文
（现有内容，由 WAL 协议维护）

## 任务状态 (规划-执行分离)
（本模板的内容）
```

注意事项：
- `## 任务状态` 部分由 `writeback-pipeline.sh` 自动更新
- `## 当前上下文` 部分仍由 AGENTS.md 的 WAL 协议维护
- 两个部分独立运行，互不干扰
