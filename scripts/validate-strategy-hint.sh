#!/usr/bin/env bash
# validate-strategy-hint.sh — 校验 StepPlan JSON 中每个 step.strategy_hint
#
# 用法:
#   ./validate-strategy-hint.sh <step-plan.json>
#   ./validate-strategy-hint.sh --fix <step-plan.json>   # 自动修复
#
# 校验规则:
#   1. 长度 ≤ 200 字（中文字符算 1，ASCII 算 1）
#   2. 不包含文件路径（/home/, /tmp/, /var/, /etc/, /usr/, C:\, D:\）
#   3. 不包含具体 CLI 命令（npm, git, curl, bash, python, pip, docker, make, gcc, cargo, go run, yarn, pnpm, npx, mv, cp, rm, chmod, chown, sed, awk, grep, find, ssh, scp, rsync, wget, apt, yum, brew）
#   4. 不包含错误代码（ERR-前缀, HTTP 状态码如 404, 500, 403 等）
#   5. 不包含 API key / token / secret 关键词
#
# 输出: 校验报告 (pass/fail + 违规详情)

set -euo pipefail

# ── 配置 ──────────────────────────────────────────────
MAX_LENGTH=200
FIX_MODE=false
INPUT_FILE=""

# ── 参数解析 ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix)   FIX_MODE=true; shift ;;
    -h|--help)
      echo "用法: $0 [--fix] <step-plan.json>"
      echo "  --fix  自动截断过长的 hint 并移除违规内容"
      exit 0
      ;;
    *)       INPUT_FILE="$1"; shift ;;
  esac
done

if [[ -z "$INPUT_FILE" ]]; then
  echo "错误: 请提供 StepPlan JSON 文件路径" >&2
  echo "用法: $0 [--fix] <step-plan.json>" >&2
  exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "错误: 文件不存在: $INPUT_FILE" >&2
  exit 1
fi

# ── 依赖检查 ──────────────────────────────────────────
if ! command -v jq &>/dev/null; then
  echo "错误: 需要 jq" >&2
  exit 1
fi

# ── 校验规则 ──────────────────────────────────────────
# 文件路径模式
PATH_PATTERNS=(
  '/home/' '/tmp/' '/var/' '/etc/' '/usr/' '/opt/'
  'C:\\\\' 'D:\\\\' 'C:/' 'D:/'
  '~/' './' '../'
)

# CLI 命令模式（作为独立单词匹配）
CLI_COMMANDS=(
  'npm' 'npx' 'yarn' 'pnpm' 'bun'
  'git' 'curl' 'wget' 'bash' 'sh' 'zsh'
  'python' 'python3' 'pip' 'pip3' 'conda'
  'docker' 'kubectl' 'helm'
  'make' 'cmake' 'gcc' 'g\+\+' 'cargo' 'go run'
  'mv' 'cp' 'rm' 'chmod' 'chown' 'mkdir' 'rmdir'
  'sed' 'awk' 'grep' 'find' 'xargs' 'sort' 'uniq'
  'ssh' 'scp' 'rsync' 'ftp'
  'apt' 'yum' 'brew' 'dnf' 'pacman'
  'systemctl' 'service'
  'tar' 'zip' 'unzip' 'gzip'
)

# 构造 CLI 匹配正则（单词边界）
CLI_REGEX=''
for cmd in "${CLI_COMMANDS[@]}"; do
  if [[ -n "$CLI_REGEX" ]]; then
    CLI_REGEX+="|"
  fi
  CLI_REGEX+="\\b${cmd}\\b"
done

# HTTP 状态码模式
HTTP_STATUS_REGEX='\b[45]\d{2}\b'

# ERR- 前缀模式
ERR_CODE_REGEX='ERR-[A-Za-z0-9-]+'

# Secret / API key 模式
SECRET_PATTERNS=(
  'api_key' 'apikey' 'api-key'
  'secret' 'token' 'bearer'
  'password' 'passwd' 'pwd'
  'private.key' 'access.key' 'auth.token'
)

# ── 辅助函数 ──────────────────────────────────────────

# 计算字符串长度（中文字符算 1）
str_len() {
  local s="$1"
  # 使用 perl 统计字符数（而非字节数）
  printf '%s' "$s" | perl -CS -ne 'print length($_)'
}

# 检查是否包含某个模式（大小写不敏感）
contains_pattern() {
  local text="$1"
  local pattern="$2"
  echo "$text" | grep -qi "$pattern"
}

# ── 主逻辑 ────────────────────────────────────────────

# 读取 JSON
PLAN_JSON=$(cat "$INPUT_FILE")

# 提取 steps 数组
STEPS_COUNT=$(echo "$PLAN_JSON" | jq '.steps | length')

if [[ "$STEPS_COUNT" -eq 0 ]]; then
  echo "⚠️  StepPlan 中没有步骤"
  exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Strategy Hint 校验报告"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "文件: $INPUT_FILE"
echo "步骤数: $STEPS_COUNT"
echo ""

TOTAL_VIOLATIONS=0
TOTAL_HINTS=0
PASSED=0
FAILED=0

# 用于 --fix 模式的临时文件
if [[ "$FIX_MODE" == true ]]; then
  FIXED_JSON="$PLAN_JSON"
fi

for (( i=0; i<STEPS_COUNT; i++ )); do
  STEP_ID=$(echo "$PLAN_JSON" | jq -r ".steps[$i].id // \"step-$i\"")
  HINT=$(echo "$PLAN_JSON" | jq -r ".steps[$i].strategy_hint // \"\"")
  
  TOTAL_HINTS=$((TOTAL_HINTS + 1))
  
  VIOLATIONS=()
  
  # 规则 1: 长度检查
  HINT_LEN=$(str_len "$HINT")
  if [[ "$HINT_LEN" -gt $MAX_LENGTH ]]; then
    VIOLATIONS+=("长度超限: ${HINT_LEN} > ${MAX_LENGTH}")
  fi
  
  # 规则 2: 文件路径检查
  for pat in "${PATH_PATTERNS[@]}"; do
    if contains_pattern "$HINT" "$pat"; then
      VIOLATIONS+=("包含文件路径: '${pat}'")
      break
    fi
  done
  
  # 规则 3: CLI 命令检查
  if echo "$HINT" | grep -qE "($CLI_REGEX)"; then
    MATCHED=$(echo "$HINT" | grep -oE "($CLI_REGEX)" | head -3 | tr '\n' ',' | sed 's/,$//')
    VIOLATIONS+=("包含 CLI 命令: ${MATCHED}")
  fi
  
  # 规则 4a: 错误代码检查 (ERR-)
  if echo "$HINT" | grep -qE "$ERR_CODE_REGEX"; then
    MATCHED=$(echo "$HINT" | grep -oE "$ERR_CODE_REGEX" | head -3 | tr '\n' ',' | sed 's/,$//')
    VIOLATIONS+=("包含错误代码: ${MATCHED}")
  fi
  
  # 规则 4b: HTTP 状态码（上下文检查，避免误报版本号）
  if echo "$HINT" | grep -qE "(status|error|code|response|返回).*${HTTP_STATUS_REGEX}|${HTTP_STATUS_REGEX}.*(error|status|code)"; then
    MATCHED=$(echo "$HINT" | grep -oE "${HTTP_STATUS_REGEX}" | head -3 | tr '\n' ',' | sed 's/,$//')
    VIOLATIONS+=("包含 HTTP 状态码: ${MATCHED}")
  fi
  
  # 规则 5: Secret / API key 检查
  for pat in "${SECRET_PATTERNS[@]}"; do
    if contains_pattern "$HINT" "$pat"; then
      VIOLATIONS+=("包含敏感关键词: '${pat}'")
      break
    fi
  done
  
  VIOLATION_COUNT=${#VIOLATIONS[@]}
  TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + VIOLATION_COUNT))
  
  if [[ $VIOLATION_COUNT -eq 0 ]]; then
    echo "  ✅ [$STEP_ID] 通过 (${HINT_LEN}/${MAX_LENGTH})"
    PASSED=$((PASSED + 1))
  else
    echo "  ❌ [$STEP_ID] 失败 (${VIOLATION_COUNT} 项违规):"
    for v in "${VIOLATIONS[@]}"; do
      echo "     • $v"
    done
    FAILED=$((FAILED + 1))
    
    # --fix 模式: 自动修复
    if [[ "$FIX_MODE" == true ]]; then
      FIXED_HINT=$(printf '%s' "$HINT" | perl -CS -e '
        use utf8;
        local $/;
        my $s = <STDIN>;

        # 移除文件路径
        $s =~ s{(?:/home/|/tmp/|/var/|/etc/|/usr/|/opt/|[CcDd]:[\\/]|~?/|\.\.?/)[\w./\\-]+}{[path]}gi;

        # 移除 CLI 命令
        my @cmds = qw(npm npx yarn pnpm bun git curl wget bash sh zsh python python3 pip pip3 conda docker kubectl helm make cmake gcc cargo go mv cp rm chmod chown mkdir rmdir sed awk grep find xargs sort uniq ssh scp rsync ftp apt yum brew dnf pacman systemctl service tar zip unzip gzip);
        for my $c (@cmds) {
          $s =~ s/\b$c\b/[cmd]/gi;
        }

        # 移除 ERR- 错误代码
        $s =~ s/ERR-[A-Za-z0-9-]+/[err-code]/gi;

        # 移除 HTTP 状态码 (上下文感知)
        $s =~ s/\b(status|error|code|response|返回)\s*(\d{3})\b/$1 [http-$2]/gi;
        $s =~ s/\b(\d{3})\s*(error|status|code)\b/[http-$1] $2/gi;

        # 移除敏感词
        $s =~ s/api[_-]?key/[secret]/gi;
        $s =~ s/apikey/[secret]/gi;
        $s =~ s/secret/[secret]/gi;
        $s =~ s/token/[secret]/gi;
        $s =~ s/bearer/[secret]/gi;
        $s =~ s/passw(?:ord|d)/[secret]/gi;
        $s =~ s/private[_-]?key/[secret]/gi;
        $s =~ s/access[_-]?key/[secret]/gi;
        $s =~ s/auth[_-]?token/[secret]/gi;

        # 截断到 200 字符
        if (length($s) > 200) {
          $s = substr($s, 0, 200) . "...";
        }

        print $s;
      ')
      
      # 更新 JSON
      FIXED_JSON=$(echo "$FIXED_JSON" | jq --arg hint "$FIXED_HINT" ".steps[$i].strategy_hint = \$hint")
      echo "     🔧 已自动修复"
    fi
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  总步骤:    $TOTAL_HINTS"
echo "  通过:      $PASSED"
echo "  失败:      $FAILED"
echo "  总违规数:  $TOTAL_VIOLATIONS"

if [[ "$FIX_MODE" == true && "$FAILED" -gt 0 ]]; then
  OUTPUT_FILE="${INPUT_FILE%.json}.fixed.json"
  echo "$FIXED_JSON" | jq '.' > "$OUTPUT_FILE"
  echo ""
  echo "  🔧 修复后的文件已保存到: $OUTPUT_FILE"
fi

echo ""

if [[ "$FAILED" -gt 0 ]]; then
  echo "❌ 校验未通过"
  exit 1
else
  echo "✅ 全部通过"
  exit 0
fi
