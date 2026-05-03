#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PASS=0; FAIL=0

# ─── 测试数据 ───

# Test 1: 高价值成功 — 多产出物 + 方法描述
cat > /tmp/test-step-high-value.json << 'TJSON'
{"stepId":"test-hv","status":"success","artifacts":["src/module.ts","tests/module.test.ts","docs/api.md"],"evidence":"Refactored auth module into separate files, added comprehensive tests. Key insight: session tokens should be validated before JWT decoding to avoid unnecessary crypto overhead."}
TJSON

# Test 2: 低价值成功 — 单产出物 + 短证据（<100 字符）
cat > /tmp/test-step-low-value.json << 'TJSON'
{"stepId":"test-lv","status":"success","artifacts":["notes.txt"],"evidence":"completed"}
TJSON

# Test 3: 失败结果
cat > /tmp/test-step-fail.json << 'TJSON'
{"stepId":"test-f","status":"failed","error":{"message":"API rate limit exceeded after 10 retries","attempts":["direct call","with backoff","exponential backoff","batch requests"],"hypothesis":"need sliding window rate limiter instead of retry-based"}}
TJSON

# Test 4: 深度洞察但只有 1 个产出物 — 旧系统会遗漏（无关键词且 artifacts<2）
# evidence 很长 (>100 chars) 且包含实质性洞察，但 artifacts 只有 1 个
cat > /tmp/test-step-deep-insight.json << 'TJSON'
{"stepId":"test-deep","status":"success","artifacts":["report/summary.md"],"evidence":"Discovered that the correlation between temperature and yield follows a non-linear pattern above 400K. The previously assumed linear model significantly underestimates performance at high temperatures. A polynomial fit of degree 3 captures the behavior accurately with R-squared 0.97. This insight changes how we approach thermal optimization in the entire pipeline."}
TJSON

# ─── 测试执行 ───

echo "=== Test 1: high-value success (multi-artifact + method description) → draft skill card ==="
OUTPUT=$(bash scripts/writeback-pipeline.sh --dry-run /tmp/test-step-high-value.json 2>&1)
if echo "$OUTPUT" | grep -qiE "draft|技能卡|策略价值: ✅"; then
  echo "PASS"; ((PASS++))
else
  echo "FAIL"; echo "$OUTPUT" | tail -5; ((FAIL++))
fi

echo "=== Test 2: low-value success (single artifact + minimal evidence) → no draft ==="
OUTPUT=$(bash scripts/writeback-pipeline.sh --dry-run /tmp/test-step-low-value.json 2>&1)
if echo "$OUTPUT" | grep -qiE "策略价值: 无|no.*skill|常规成功"; then
  echo "PASS"; ((PASS++))
else
  echo "FAIL"; echo "$OUTPUT" | tail -5; ((FAIL++))
fi

echo "=== Test 3: failure → error recording ==="
OUTPUT=$(bash scripts/writeback-pipeline.sh --dry-run /tmp/test-step-fail.json 2>&1)
if echo "$OUTPUT" | grep -qiE "ERRORS|失败处理|错误记录"; then
  echo "PASS"; ((PASS++))
else
  echo "FAIL"; echo "$OUTPUT" | tail -5; ((FAIL++))
fi

echo "=== Test 4: deep insight with single artifact but long evidence → draft skill card ==="
# 关键改进：evidence 长度 > 100 字符且包含实质性洞察应被识别为高价值
# 旧的关键词匹配不识别这个（没有"使用/调用/配置"等关键词，且 artifacts < 2）
OUTPUT=$(bash scripts/writeback-pipeline.sh --dry-run /tmp/test-step-deep-insight.json 2>&1)
if echo "$OUTPUT" | grep -qiE "draft|技能卡|策略价值: ✅"; then
  echo "PASS"; ((PASS++))
else
  echo "FAIL: deep insight with single artifact not recognized as high value"; echo "$OUTPUT" | tail -10; ((FAIL++))
fi

echo "--- Results: $PASS passed, $FAIL failed ---"
[[ $FAIL -eq 0 ]]
