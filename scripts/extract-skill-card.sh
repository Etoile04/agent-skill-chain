#!/usr/bin/env bash
# extract-skill-card.sh — 从 memory 文件或对话文本中提炼三维技能卡
#
# 用法:
#   bash scripts/extract-skill-card.sh [--dry-run] [--type TYPE] [--name NAME] INPUT [INPUT...]
#
# INPUT 可以是:
#   - memory/ 目录下的文件路径
#   - 任意文本文件路径
#   - "-" 表示从 stdin 读取
#
# 输出: skill-cards/{category}/{name}.md
#
# 依赖: llm-task (OpenClaw 内置工具) 或 curl (回退)

set -euo pipefail

# ─── 默认值 ───
DRY_RUN=false
CARD_TYPE=""
CARD_NAME=""
INPUTS=()

# ─── 参数解析 ───
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN=true; shift ;;
    --type)       CARD_TYPE="$2"; shift 2 ;;
    --name)       CARD_NAME="$2"; shift 2 ;;
    -*)           echo "未知选项: $1" >&2; exit 1 ;;
    *)           INPUTS+=("$1"); shift ;;
  esac
done

if [[ ${#INPUTS[@]} -eq 0 ]]; then
  echo "用法: $0 [--dry-run] [--type TYPE] [--name NAME] INPUT [INPUT...]" >&2
  echo "  INPUT: 文件路径 或 '-' (stdin)" >&2
  exit 1
fi

# ─── 工作目录 ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_CARDS_DIR="$WORKSPACE/skill-cards"

# 确保目录存在
mkdir -p "$SKILL_CARDS_DIR"/{workflows,patterns,domains}

# ─── 读取输入 ───
CONTENT=""
for input in "${INPUTS[@]}"; do
  if [[ "$input" == "-" ]]; then
    INPUT_TEXT="$(cat)"
  else
    if [[ ! -f "$input" ]]; then
      echo "⚠️  文件不存在: $input" >&2
      continue
    fi
    INPUT_TEXT="$(cat "$input")"
  fi
  CONTENT="${CONTENT}

---

${INPUT_TEXT}"
done

if [[ -z "$CONTENT" ]]; then
  echo "❌ 没有有效输入内容" >&2
  exit 1
fi

# 截断过长内容（保留前 8000 字符，避免 LLM 超时）
MAX_CHARS=8000
if [[ ${#CONTENT} -gt $MAX_CHARS ]]; then
  CONTENT="${CONTENT:0:$MAX_CHARS}

... [内容已截断，共 ${#CONTENT} 字符]"
fi

# ─── 日期 ───
TODAY="$(date +%Y-%m-%d)"

# ─── LLM Prompt ───
read -r -d '' PROMPT << 'PROMPT_EOF' || true
你是一个经验提炼助手。请从以下对话轨迹中提炼一张「三维技能卡」。

## 三维结构
1. **e_success（成功经验）**：什么做法有效？哪些决策是正确的？
2. **e_mistake（失败教训）**：什么做法失败了？踩了什么坑？根因是什么？
3. **e_workflow（推荐工作流）**：如果再次遇到类似任务，推荐的标准流程是什么？

## 输出格式
严格按以下格式输出：

```
---
id: sc-DATE-NNN
type: workflow | pattern | domain
category: workflows | patterns | domains
task_types:
  - 任务类型1
  - 任务类型2
avg_reward: 0.7
usage_count: 0
created: DATE
updated: DATE
status: draft
sources:
  - 来源文件
---

# 技能卡标题

## ✅ 成功经验 (e_success)

### 有效的策略
- ...

### 关键决策
- ...

### 验证过的工具/方法
- ...

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- ...

### 错误模式
- ...

### 需要避免的做法
- ...

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. ...

### 触发条件
- ...

### 前置条件
- ...

### 预期结果
- ...

### 回退方案
- ...
```

## 要求
1. type 选择：
   - 如果内容主要是某个安装/调试/部署流程 → workflow
   - 如果内容主要是某个错误模式或成功模式 → pattern
   - 如果内容主要是某个领域（飞书、A2A、知识库等）的知识 → domain
2. category 必须与 type 映射：workflow→workflows, pattern→patterns, domain→domains
3. avg_reward 根据成功/失败比例估算（0.0-1.0）
4. 提取的信息要具体、可操作，避免空泛描述
5. 只输出 YAML + Markdown 内容，不要额外解释

## 输入内容：
PROMPT_EOF

PROMPT="${PROMPT}

${CONTENT}"

# ─── 注入参数覆盖 ───
if [[ -n "$CARD_TYPE" ]]; then
  # 在 prompt 中追加类型提示
  PROMPT="${PROMPT}

⚠️ 用户指定了类型: ${CARD_TYPE}，请使用这个类型。"
fi

if [[ -n "$CARD_NAME" ]]; then
  PROMPT="${PROMPT}

⚠️ 用户指定了文件名: ${CARD_NAME}，请在标题中体现。"
fi

# ─── 调用 LLM ───
echo "🔄 正在提炼技能卡..."

# 方案 1: 使用 openclaw llm-task（如果可用）
if command -v openclaw &>/dev/null; then
  RESULT="$(openclaw llm-task --prompt "$PROMPT" --schema '{"type":"string"}' 2>/dev/null || echo "")"
fi

# 方案 2: 使用 curl 调用本地 API（如果 llm-task 不可用）
if [[ -z "$RESULT" ]]; then
  # 尝试从环境变量获取 API 信息
  API_BASE="${OPENCLAW_API_BASE:-http://localhost:4152}"
  API_KEY="${OPENCLAW_API_KEY:-}"

  # 构建 JSON payload
  # 使用 python 处理转义
  ESCAPED_PROMPT="$(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$PROMPT")"

  RESULT="$(curl -s -X POST "${API_BASE}/v1/llm-task" \
    -H "Content-Type: application/json" \
    ${API_KEY:+-H "Authorization: Bearer $API_KEY"} \
    -d "{\"prompt\":${ESCAPED_PROMPT},\"schema\":{\"type\":\"string\"}}" 2>/dev/null || echo "")"
fi

# 方案 3: 直接输出 prompt 让用户手动处理
if [[ -z "$RESULT" || "$RESULT" == "" ]]; then
  echo "⚠️  无法自动调用 LLM，将 prompt 输出到 /tmp/skill-card-prompt.txt"
  echo "$PROMPT" > /tmp/skill-card-prompt.txt
  echo "   请手动将 prompt 发送给 LLM，并将结果粘贴回来"
  echo ""
  echo "   或者使用: cat /tmp/skill-card-prompt.txt | openclaw llm-task"
  exit 1
fi

# ─── 解析结果 ───
# 清理结果（可能包含 markdown 代码块标记）
CARD_CONTENT="$(echo "$RESULT" | sed 's/^```$//; s/^```yaml//; s/^```markdown//; s/^```md//' | sed '/^$/N;/^\n$/d')"

# 提取 type/category（用于确定输出路径）
PARSED_TYPE="$(echo "$CARD_CONTENT" | head -20 | grep '^type:' | awk '{print $2}' | tr -d ' ')"
PARSED_CATEGORY="$(echo "$CARD_CONTENT" | head -20 | grep '^category:' | awk '{print $2}' | tr -d ' ')"
PARSED_TITLE="$(echo "$CARD_CONTENT" | grep '^#' | head -1 | sed 's/^# //' | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9\u4e00-\u9fff-]//g')"

# 回退默认值
if [[ -z "$PARSED_CATEGORY" || "$PARSED_CATEGORY" == "domains" ]]; then
  PARSED_CATEGORY="${CARD_TYPE:-domain}s"
fi
if [[ -z "$PARSED_CATEGORY" ]]; then
  PARSED_CATEGORY="workflows"
fi

# 确定输出文件名
if [[ -n "$CARD_NAME" ]]; then
  OUTPUT_FILE="$SKILL_CARDS_DIR/$PARSED_CATEGORY/${CARD_NAME}.md"
elif [[ -n "$PARSED_TITLE" && "$PARSED_TITLE" != "" ]]; then
  OUTPUT_FILE="$SKILL_CARDS_DIR/$PARSED_CATEGORY/${PARSED_TITLE}.md"
else
  OUTPUT_FILE="$SKILL_CARDS_DIR/$PARSED_CATEGORY/sc-${TODAY}-$(date +%s).md"
fi

# ─── 输出 ───
if [[ "$DRY_RUN" == "true" ]]; then
  echo "📝 [DRY-RUN] 技能卡将写入: $OUTPUT_FILE"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$CARD_CONTENT"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
  mkdir -p "$(dirname "$OUTPUT_FILE")"
  echo "$CARD_CONTENT" > "$OUTPUT_FILE"
  echo "✅ 技能卡已写入: $OUTPUT_FILE"
  echo "   类型: ${PARSED_TYPE:-unknown}"
  echo "   分类: $PARSED_CATEGORY"
fi
