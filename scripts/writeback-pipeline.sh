#!/usr/bin/env bash
# writeback-pipeline.sh — Learning Writeback 自动化管道
#
# 从 StepResult JSON 中提取经验，自动更新错误记录、技能卡和日志。
#
# 处理流程:
#   1. 解析 StepResult（status, artifacts, evidence, error）
#   2. 如果 status=failed：提取错误模式 → .learnings/ERRORS.md
#   3. 如果 status=success 且有策略价值 → skill-cards/pending/（draft）
#   4. 追加到 memory/YYYY-MM-DD.md（当日日志）
#   5. 如果错误模式与已有技能卡匹配 → 建议更新 planning_hints
#
# 用法:
#   ./scripts/writeback-pipeline.sh result.json
#   ./scripts/writeback-pipeline.sh --dry-run result.json
#   cat result.json | ./scripts/writeback-pipeline.sh -
#   ./scripts/writeback-pipeline.sh --dry-run --stdin < result.json
#
# 依赖: python3, jq（可选，fallback 到 python）

set -euo pipefail

# ─── 常量 ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
LEARNINGS_DIR="$WORKSPACE/.learnings"
MEMORY_DIR="$WORKSPACE/memory"
SKILL_CARDS_DIR="$WORKSPACE/skill-cards"
PENDING_DIR="$SKILL_CARDS_DIR/pending"
TEMPLATE_FILE="$LEARNINGS_DIR/TEMPLATE.md"
ERRORS_FILE="$LEARNINGS_DIR/ERRORS.md"

# ─── 默认值 ───
DRY_RUN=false
INPUT_FILE=""
TASK_NAME=""        # 可选：任务名称覆盖
STEP_ID=""          # 可选：步骤 ID

# ─── 参数解析 ───
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN=true; shift ;;
    --task-name)  TASK_NAME="$2"; shift 2 ;;
    --step-id)    STEP_ID="$2"; shift 2 ;;
    --help|-h)
      echo "用法: $0 [--dry-run] [--task-name NAME] [--step-id ID] INPUT"
      echo ""
      echo "INPUT: StepResult JSON 文件路径 或 '-'（stdin）"
      echo ""
      echo "选项:"
      echo "  --dry-run       只输出建议，不写入文件"
      echo "  --task-name     覆盖任务名称（用于日志）"
      echo "  --step-id       覆盖步骤 ID"
      echo "  --help          显示帮助"
      exit 0
      ;;
    -*)  echo "未知选项: $1" >&2; exit 1 ;;
    *)   INPUT_FILE="$1"; shift ;;
  esac
done

if [[ -z "$INPUT_FILE" ]]; then
  echo "❌ 缺少输入。用法: $0 [--dry-run] <result.json|->" >&2
  exit 1
fi

# ─── 确保目录存在 ───
mkdir -p "$PENDING_DIR"

# ─── 读取输入 ───
if [[ "$INPUT_FILE" == "-" ]]; then
  INPUT_JSON="$(cat)"
else
  if [[ ! -f "$INPUT_FILE" ]]; then
    echo "❌ 文件不存在: $INPUT_FILE" >&2
    exit 1
  fi
  INPUT_JSON="$(cat "$INPUT_FILE")"
fi

# ─── 日期 ───
TODAY="$(date +%Y-%m-%d)"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"

# ─── 核心处理（Python） ───
export _INPUT_JSON="$INPUT_JSON"
export _WORKSPACE="$WORKSPACE"
export _LEARNINGS_DIR="$LEARNINGS_DIR"
export _MEMORY_DIR="$MEMORY_DIR"
export _SKILL_CARDS_DIR="$SKILL_CARDS_DIR"
export _PENDING_DIR="$PENDING_DIR"
export _ERRORS_FILE="$ERRORS_FILE"
export _TODAY="$TODAY"
export _TIMESTAMP="$TIMESTAMP"
export _DRY_RUN="$DRY_RUN"
export _TASK_NAME="$TASK_NAME"
export _STEP_ID="$STEP_ID"

python3 << 'PYTHON_SCRIPT'
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

# ===== 参数 =====
input_json = os.environ.get("_INPUT_JSON", "")
workspace = os.environ.get("_WORKSPACE", "")
learnings_dir = os.environ.get("_LEARNINGS_DIR", "")
memory_dir = os.environ.get("_MEMORY_DIR", "")
skill_cards_dir = os.environ.get("_SKILL_CARDS_DIR", "")
pending_dir = os.environ.get("_PENDING_DIR", "")
errors_file = os.environ.get("_ERRORS_FILE", "")
today = os.environ.get("_TODAY", "")
timestamp = os.environ.get("_TIMESTAMP", "")
dry_run = os.environ.get("_DRY_RUN", "false") == "true"
task_name_override = os.environ.get("_TASK_NAME", "")
step_id_override = os.environ.get("_STEP_ID", "")

# ===== 解析 StepResult =====
try:
    result = json.loads(input_json)
except json.JSONDecodeError as e:
    print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
    sys.exit(1)

status = result.get("status", "unknown")
step_id = step_id_override or result.get("stepId", "unknown-step")
artifacts = result.get("artifacts", [])
evidence = result.get("evidence", "")
error = result.get("error", {})
planning_suggestion = result.get("planningSuggestion", "")

# 从 error 提取详细信息
error_message = ""
error_attempts = []
error_hypothesis = ""
if isinstance(error, dict):
    error_message = error.get("message", "")
    error_attempts = error.get("attempts", [])
    error_hypothesis = error.get("hypothesis", "")
elif isinstance(error, str):
    error_message = error

# 任务描述（用于日志）
task_desc = task_name_override or result.get("task", {}).get("description", step_id)

# ===== 报告收集 =====
report_lines = []
report_lines.append("=" * 60)
report_lines.append(f"📋 Learning Writeback 报告 — {timestamp}")
report_lines.append("=" * 60)
report_lines.append(f"步骤: {step_id}")
report_lines.append(f"状态: {status}")
if dry_run:
    report_lines.append("模式: DRY-RUN（仅建议，不写入）")
report_lines.append("")

actions_taken = []   # 已执行的操作
suggestions = []     # 建议

# ===== 1. 失败处理 =====
if status == "failed":
    report_lines.append("## ❌ 失败处理")
    report_lines.append("")
    
    # 生成错误 ID
    err_id = f"ERR-{today.replace('-', '')}-{step_id.replace('/', '-')}"
    
    # 构建错误记录（按 TEMPLATE 格式）
    error_entry = f"""
## [{err_id}] StepResult 失败: {error_message[:80]}

**类型**: technical
**来源**: 规划-执行分离管道
**严重程度**: P1（重要）

### Miss（发生了什么）
步骤 `{step_id}` 执行失败。
- 错误信息: {error_message}
- 已尝试方法: {', '.join(error_attempts) if error_attempts else '无'}
- 失败假设: {error_hypothesis or '未提供'}

### Root（为什么发生）
5-Why分析：
1. 为什么？→ {error_message}
2. 为什么？→ {error_hypothesis or '需进一步分析'}
3. 为什么？→ [待填写]
4. 为什么？→ [待填写]
5. 为什么？→ [待填写 — 根本原因]

### Fix（如何修复）
预防规则（可执行）：
- [ ] 分析错误信息: {error_message}
- [ ] 检查相关工具/环境配置
- [ ] 验证前置条件是否满足

### Pattern（模式识别）
- 频率: 首次
- 状态: emerging

### Metadata
- 记录时间: {timestamp}
- 关联步骤: {step_id}
- 标签: [自动化, writeback-pipeline]
"""
    
    report_lines.append(f"  错误 ID: {err_id}")
    report_lines.append(f"  错误信息: {error_message}")
    report_lines.append("")
    
    if dry_run:
        report_lines.append("  📝 [建议] 追加错误记录到 .learnings/ERRORS.md:")
        report_lines.append("  " + "-" * 40)
        for line in error_entry.strip().split('\n'):
            report_lines.append(f"  {line}")
        report_lines.append("")
        suggestions.append(f"追加错误记录 {err_id} 到 .learnings/ERRORS.md")
    else:
        # 追加到 ERRORS.md
        errors_path = Path(errors_file)
        if errors_path.exists():
            with open(errors_path, 'a', encoding='utf-8') as f:
                f.write(error_entry)
            actions_taken.append(f"追加错误记录 {err_id} 到 .learnings/ERRORS.md")
            report_lines.append(f"  ✅ 已追加错误记录到 .learnings/ERRORS.md")
        else:
            report_lines.append(f"  ⚠️  .learnings/ERRORS.md 不存在，跳过错误记录")
        report_lines.append("")
    
    # 检查是否有匹配的技能卡 → 建议更新 planning_hints
    report_lines.append("  🔍 检查匹配的技能卡...")
    matched_cards = []
    
    cards_path = Path(skill_cards_dir)
    if cards_path.exists():
        # 从错误信息中提取关键词
        error_keywords = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', error_message.lower()))
        
        for card_file in cards_path.rglob("*.md"):
            if card_file.name == "README.md" or card_file.parent.name == "pending":
                continue
            try:
                content = card_file.read_text(encoding='utf-8')
                # 简单关键词匹配
                card_keywords = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', content.lower()))
                overlap = error_keywords & card_keywords
                if len(overlap) >= 2:  # 至少 2 个关键词重叠
                    matched_cards.append({
                        'file': str(card_file.relative_to(workspace)),
                        'overlap': list(overlap)[:5],
                        'name': card_file.stem
                    })
            except:
                pass
    
    if matched_cards:
        report_lines.append(f"  找到 {len(matched_cards)} 个相关技能卡:")
        for mc in matched_cards:
            report_lines.append(f"    - {mc['file']} (重叠词: {', '.join(mc['overlap'])})")
            hint_suggestion = f"""
  建议更新 {mc['file']} 的 planning_hints.common_failures:
  ```yaml
  - pattern: "{error_message[:60]}"
    hint: "{error_hypothesis or '需人工补充策略提示'}"
  ```"""
            report_lines.append(hint_suggestion)
            suggestions.append(f"更新 {mc['file']} 的 planning_hints (错误: {error_message[:40]})")
    else:
        report_lines.append("  未找到匹配的技能卡")
    report_lines.append("")

# ===== 2. 成功处理 =====
elif status == "success":
    report_lines.append("## ✅ 成功处理")
    report_lines.append("")
    
    if artifacts:
        report_lines.append(f"  产出物: {', '.join(str(a) for a in artifacts)}")
    if evidence:
        report_lines.append(f"  证据: {evidence[:200]}")
    
    # 判断是否有策略价值（启发式）
    has_strategy_value = False
    strategy_reason = ""
    
    # 条件1: 有多个产出物
    if len(artifacts) >= 2:
        has_strategy_value = True
        strategy_reason = "多产出物（可能包含可复用的工作流）"
    
    # 条件2: evidence 中包含工具/方法名
    if evidence and any(kw in evidence.lower() for kw in ['使用', '调用', '配置', '安装', '运行', 'exec', 'script', 'command']):
        has_strategy_value = True
        strategy_reason = "证据中包含可复用的方法描述"
    
    # 条件3: 有 planning suggestion
    if planning_suggestion:
        has_strategy_value = True
        strategy_reason = "包含规划层建议"
    
    if has_strategy_value:
        report_lines.append(f"  策略价值: ✅ ({strategy_reason})")
        report_lines.append("")
        
        # 生成 draft 技能卡
        card_id = f"sc-{today.replace('-', '')}-wb-{step_id.replace('/', '-')}"
        draft_card = f"""---
id: {card_id}
type: pattern
category: patterns
task_types:
  - 自动生成
avg_reward: 0.5
usage_count: 0
created: {today}
updated: {today}
status: draft
sources:
  - writeback-pipeline
---

# [自动提取] {task_desc[:60]}

> 由 writeback-pipeline 自动生成，需人工审核后移至正式目录。

## ✅ 成功经验 (e_success)

### 有效的策略
- {evidence[:200] if evidence else '待补充'}

### 关键决策
- 待人工补充

### 验证过的工具/方法
- 待人工补充

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- 待人工补充

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. 待人工补充

### 触发条件
- {task_desc[:80]}

### 预期结果
- {evidence[:100] if evidence else '待补充'}
"""
        
        if dry_run:
            report_lines.append("  📝 [建议] 生成 draft 技能卡到 skill-cards/pending/:")
            report_lines.append(f"  文件: pending/{card_id}.md")
            report_lines.append("  " + "-" * 40)
            for line in draft_card.strip().split('\n'):
                report_lines.append(f"  {line}")
            report_lines.append("")
            suggestions.append(f"生成 draft 技能卡 pending/{card_id}.md")
        else:
            output_path = Path(pending_dir) / f"{card_id}.md"
            output_path.write_text(draft_card, encoding='utf-8')
            actions_taken.append(f"生成 draft 技能卡 {output_path.relative_to(workspace)}")
            report_lines.append(f"  ✅ 已生成 draft 技能卡: {output_path}")
        report_lines.append("")
    else:
        report_lines.append("  策略价值: 无（常规成功步骤）")
        report_lines.append("")

# ===== 3. blocked 处理 =====
elif status == "blocked":
    report_lines.append("## 🚫 阻塞处理")
    report_lines.append(f"  原因: {error_message or '未提供'}")
    if planning_suggestion:
        report_lines.append(f"  规划建议: {planning_suggestion}")
    report_lines.append("")

# ===== 4. 追加到 memory/YYYY-MM-DD.md =====
report_lines.append("## 📝 日志记录")

log_entry = f"""
### [{timestamp}] Writeback: {step_id} ({status})
- 步骤: {step_id}
- 状态: {status}
"""
if status == "failed":
    log_entry += f"- 错误: {error_message}\n"
    log_entry += f"- 尝试: {', '.join(str(a) for a in error_attempts[:3])}\n"
elif status == "success":
    if artifacts:
        log_entry += f"- 产出: {', '.join(str(a) for a in artifacts)}\n"
    if evidence:
        log_entry += f"- 证据: {evidence[:200]}\n"

if dry_run:
    report_lines.append("  📝 [建议] 追加日志到 memory/{}.md:".format(today))
    report_lines.append("  " + "-" * 40)
    for line in log_entry.strip().split('\n'):
        report_lines.append(f"  {line}")
    report_lines.append("")
    suggestions.append(f"追加日志到 memory/{today}.md")
else:
    memory_file = Path(memory_dir) / f"{today}.md"
    if memory_file.exists():
        with open(memory_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    else:
        # 创建新日志文件
        header = f"# {today} 工作日志\n\n"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        memory_file.write_text(header + log_entry, encoding='utf-8')
    actions_taken.append(f"追加日志到 memory/{today}.md")
    report_lines.append(f"  ✅ 已追加日志到 memory/{today}.md")
report_lines.append("")

# ===== 5. 汇总 =====
report_lines.append("=" * 60)
report_lines.append("## 📊 汇总")
report_lines.append("")
if actions_taken:
    report_lines.append("已执行操作:")
    for action in actions_taken:
        report_lines.append(f"  ✅ {action}")
if suggestions:
    report_lines.append("")
    report_lines.append("建议:")
    for suggestion in suggestions:
        report_lines.append(f"  💡 {suggestion}")
if not actions_taken and not suggestions:
    report_lines.append("无操作（常规步骤，无需 writeback）")

report_lines.append("")
report_lines.append("=" * 60)

# 输出报告
print('\n'.join(report_lines))

PYTHON_SCRIPT
