#!/usr/bin/env bash
# planning-quality-eval.sh — 规划质量评估器
#
# 用法:
#   ./planning-quality-eval.sh <step-plan.json> <results-dir-or-file> [--task-desc "任务描述"]
#
# 参数:
#   step-plan.json        StepPlan JSON 文件
#   results-dir-or-file   StepResult JSON 文件目录 或 单个文件（多个结果时用逗号分隔）
#   --task-desc           可选，任务描述文本（用于计算 plan_coverage）
#
# 输出: JSON 格式的评估报告
#
# 评估指标:
#   - step_success_rate:  成功步骤 / 总步骤
#   - fallback_rate:      触发 fallback / replan 的步骤占比
#   - plan_coverage:      StepPlan 覆盖任务关键方面的比例 (0.0 - 1.0)
#   - avg_steps_per_replan: 平均每次重规划的步骤数

set -euo pipefail

# ── 参数解析 ──────────────────────────────────────────
PLAN_FILE=""
RESULTS_INPUT=""
TASK_DESC=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-desc)
      TASK_DESC="$2"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    -h|--help)
      echo "用法: $0 <step-plan.json> <results-dir-or-file> [--task-desc \"任务描述\"]"
      echo ""
      echo "参数:"
      echo "  step-plan.json        StepPlan JSON 文件"
      echo "  results-dir-or-file   StepResult JSON 文件（目录/单文件/逗号分隔多文件）"
      echo "  --task-desc           任务描述（用于 plan_coverage 计算）"
      echo "  --verbose             显示详细计算过程"
      exit 0
      ;;
    *)
      if [[ -z "$PLAN_FILE" ]]; then
        PLAN_FILE="$1"
      elif [[ -z "$RESULTS_INPUT" ]]; then
        RESULTS_INPUT="$1"
      else
        echo "未知参数: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$PLAN_FILE" || -z "$RESULTS_INPUT" ]]; then
  echo "错误: 需要提供 StepPlan 和 StepResult 文件" >&2
  echo "用法: $0 <step-plan.json> <results-dir-or-file>" >&2
  exit 1
fi

# ── 依赖检查 ──────────────────────────────────────────
if ! command -v jq &>/dev/null; then
  echo "错误: 需要 jq" >&2
  exit 1
fi

# ── 读取 StepPlan ─────────────────────────────────────
if [[ ! -f "$PLAN_FILE" ]]; then
  echo "错误: StepPlan 文件不存在: $PLAN_FILE" >&2
  exit 1
fi

PLAN_JSON=$(cat "$PLAN_FILE")
TOTAL_STEPS=$(echo "$PLAN_JSON" | jq '.steps | length')

if [[ "$TOTAL_STEPS" -eq 0 ]]; then
  echo '{"error": "StepPlan 中没有步骤", "step_success_rate": 0, "fallback_rate": 0, "plan_coverage": 0, "avg_steps_per_replan": 0}'
  exit 0
fi

# ── 收集 StepResult 文件 ──────────────────────────────
RESULT_FILES=()

if [[ -d "$RESULTS_INPUT" ]]; then
  # 目录模式: 查找所有 .json 文件
  while IFS= read -r -d '' f; do
    RESULT_FILES+=("$f")
  done < <(find "$RESULTS_INPUT" -name "*.json" -print0 2>/dev/null)
elif [[ "$RESULTS_INPUT" == *","* ]]; then
  # 逗号分隔多文件
  IFS=',' read -ra FILES <<< "$RESULTS_INPUT"
  for f in "${FILES[@]}"; do
    f=$(echo "$f" | xargs)  # trim
    [[ -f "$f" ]] && RESULT_FILES+=("$f")
  done
else
  # 单文件
  [[ -f "$RESULTS_INPUT" ]] && RESULT_FILES+=("$RESULTS_INPUT")
fi

if [[ ${#RESULT_FILES[@]} -eq 0 ]]; then
  echo "错误: 没有找到 StepResult 文件" >&2
  exit 1
fi

# ── 合并所有 StepResult ──────────────────────────────
ALL_RESULTS="[]"
for rf in "${RESULT_FILES[@]}"; do
  ONE=$(cat "$rf")
  # 如果是数组，合并；如果是单个对象，追加
  if echo "$ONE" | jq -e 'type == "array"' &>/dev/null; then
    ALL_RESULTS=$(echo "$ALL_RESULTS" | jq --argjson arr "$ONE" '. + $arr')
  else
    ALL_RESULTS=$(echo "$ALL_RESULTS" | jq --argjson obj "$ONE" '. + [$obj]')
  fi
done

RESULT_COUNT=$(echo "$ALL_RESULTS" | jq 'length')

# ── 计算指标 ──────────────────────────────────────────

# 1. step_success_rate
SUCCESS_COUNT=$(echo "$ALL_RESULTS" | jq '[.[] | select(.status == "success")] | length')
STEP_SUCCESS_RATE=$(echo "scale=4; $SUCCESS_COUNT / $TOTAL_STEPS" | bc 2>/dev/null || echo "0")

# 确保 0-1 范围
if [[ "$(echo "$STEP_SUCCESS_RATE > 1.0" | bc 2>/dev/null || echo 0)" -eq 1 ]]; then
  STEP_SUCCESS_RATE="1.0000"
fi

# 2. fallback_rate
# 统计触发 fallback 的步骤：
#   - status == "failed" 且有 planningSuggestion
#   - status == "blocked"
#   - 明确标记为 replan 的
FALLBACK_COUNT=$(echo "$ALL_RESULTS" | jq '[.[] | select(
  (.status == "failed" and .planningSuggestion != null) or
  (.status == "blocked") or
  (.planningSuggestion // "" | test("replan|重新规划|回退"; "i"))
)] | length')
FALLBACK_RATE=$(echo "scale=4; $FALLBACK_COUNT / $TOTAL_STEPS" | bc 2>/dev/null || echo "0")

# 3. plan_coverage (需要任务描述)
PLAN_COVERAGE="0"
COVERAGE_DETAIL=""

if [[ -n "$TASK_DESC" ]]; then
  # 从任务描述中提取关键词（简单分词）
  # 去除标点，按空格/标点分割
  KEYWORDS=$(echo "$TASK_DESC" | \
    jq -R -s '
      # 转小写
      ascii_downcase |
      # 去除常见停用词（中英文）
      gsub("\\b(the|a|an|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|shall|should|may|might|can|could|of|in|to|for|with|on|at|by|from|as|into|through|during|before|after|above|below|between|out|off|over|under|again|further|then|once|here|there|when|where|why|how|all|both|each|few|more|most|other|some|such|no|nor|not|only|own|same|so|than|too|very|的|了|在|是|我|有|和|就|不|人|都|一|一个|上|也|很|到|说|要|去|你|会|着|没有|看|好|自己|这)\\b"; "g"; "") |
      # 按非字母数字 CJK 字符分割
      [split("[\\s,.;:!?()\\[\\]{}\"''<>|/\\\\\\n\\r\\t]+"; "") | .[] | select(length > 1)] | unique
    ')

  KEYWORD_COUNT=$(echo "$KEYWORDS" | jq 'length')

  if [[ "$KEYWORD_COUNT" -gt 0 ]]; then
    # 将所有 steps 的 goal + strategy_hint 合并为文本
    PLAN_TEXT=$(echo "$PLAN_JSON" | jq -r '[.steps[] | "\(.goal) \(.strategy_hint)"] | join(" ")')

    # 计算有多少关键词在计划文本中出现
    MATCHED=0
    for i in $(seq 0 $((KEYWORD_COUNT - 1))); do
      KW=$(echo "$KEYWORDS" | jq -r ".[$i]")
      if echo "$PLAN_TEXT" | grep -qi "$KW"; then
        MATCHED=$((MATCHED + 1))
      fi
    done

    PLAN_COVERAGE=$(echo "scale=4; $MATCHED / $KEYWORD_COUNT" | bc 2>/dev/null || echo "0")
    COVERAGE_DETAIL="关键词总数: ${KEYWORD_COUNT}, 命中: ${MATCHED}"
  fi
fi

# 4. avg_steps_per_replan
# 通过 fallback_triggers 触发的重规划次数来估算
# 统计 StepResult 中有 planningSuggestion 包含 replan 关键词的
REPLAN_COUNT=$(echo "$ALL_RESULTS" | jq '[.[] | select(.planningSuggestion // "" | test("replan|重新规划|回退|重新评估"; "i"))] | length')

if [[ "$REPLAN_COUNT" -gt 0 ]]; then
  # 如果有多次 replan，估算平均每次的步骤数
  # 简化计算: 总步骤 / (1 + replan次数) — 假设每次 replan 会产生新的步骤集
  AVG_STEPS=$(echo "scale=2; $TOTAL_STEPS / (1 + $REPLAN_COUNT)" | bc 2>/dev/null || echo "$TOTAL_STEPS")
else
  AVG_STEPS="$TOTAL_STEPS"
fi

# ── 附加指标 ──────────────────────────────────────────

# 各步骤状态分布
STATUS_DIST=$(echo "$ALL_RESULTS" | jq 'group_by(.status) | map({key: .[0].status, value: length}) | from_entries')

# 步骤完整性：有多少 plan step 有对应的 result
COVERED_STEP_IDS=$(echo "$ALL_RESULTS" | jq '[.[].stepId]')
PLAN_STEP_IDS=$(echo "$PLAN_JSON" | jq '[.steps[].id]')
MISSING_RESULTS=$(echo "$PLAN_JSON" | jq --argjson covered "$COVERED_STEP_IDS" '[.steps[].id] | map(select(. as $id | $covered | index($id) | not))')

# ── 生成报告 ──────────────────────────────────────────
REPORT=$(jq -n \
  --argjson step_success_rate "$STEP_SUCCESS_RATE" \
  --argjson fallback_rate "$FALLBACK_RATE" \
  --argjson plan_coverage "$PLAN_COVERAGE" \
  --argjson avg_steps_per_replan "$AVG_STEPS" \
  --argjson total_steps "$TOTAL_STEPS" \
  --argjson success_count "$SUCCESS_COUNT" \
  --argjson fallback_count "$FALLBACK_COUNT" \
  --argjson replan_count "$REPLAN_COUNT" \
  --argjson result_count "$RESULT_COUNT" \
  --arg coverage_detail "$COVERAGE_DETAIL" \
  --argjson status_distribution "$STATUS_DIST" \
  --argjson missing_results "$MISSING_RESULTS" \
  '{
    metrics: {
      step_success_rate: $step_success_rate,
      fallback_rate: $fallback_rate,
      plan_coverage: $plan_coverage,
      avg_steps_per_replan: $avg_steps_per_replan
    },
    details: {
      total_steps: $total_steps,
      results_received: $result_count,
      success_count: $success_count,
      fallback_count: $fallback_count,
      replan_count: $replan_count,
      status_distribution: $status_distribution,
      missing_results: $missing_results,
      coverage_detail: $coverage_detail
    },
    assessment: {
      overall: (
        if ($step_success_rate >= 0.8 and $fallback_rate <= 0.2) then "good"
        elif ($step_success_rate >= 0.5) then "needs_improvement"
        else "poor"
        end
      ),
      recommendation: (
        if ($step_success_rate >= 0.8 and $fallback_rate <= 0.2) then
          "规划质量良好，步骤划分合理"
        elif ($step_success_rate < 0.5) then
          "成功率过低，建议重新评估任务复杂度和步骤粒度"
        elif ($fallback_rate > 0.3) then
          "fallback 率过高，可能步骤划分过细或 fallback_triggers 过于敏感"
        else
          "规划基本可用但需改进，关注失败步骤的具体原因"
        end
      )
    }
  }')

# ── 输出 ──────────────────────────────────────────────
if [[ "$VERBOSE" == true ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📊 规划质量评估报告"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "📈 核心指标:"
  echo "  step_success_rate:  $STEP_SUCCESS_RATE"
  echo "  fallback_rate:      $FALLBACK_RATE"
  echo "  plan_coverage:      ${PLAN_COVERAGE:-N/A}"
  echo "  avg_steps_per_replan: $AVG_STEPS"
  echo ""
  echo "📋 详细数据:"
  echo "  总步骤:         $TOTAL_STEPS"
  echo "  结果数:         $RESULT_COUNT"
  echo "  成功步骤:       $SUCCESS_COUNT"
  echo "  Fallback 次数:  $FALLBACK_COUNT"
  echo "  Replan 次数:    $REPLAN_COUNT"
  [[ -n "$COVERAGE_DETAIL" ]] && echo "  Coverage:       $COVERAGE_DETAIL"
  echo ""
fi

echo "$REPORT" | jq '.'
