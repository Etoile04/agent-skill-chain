#!/usr/bin/env bash
# test_ucb_transfer_mode.sh — TDD tests for UCB transfer_mode support
set -euo pipefail
cd "$(dirname "$0")/.."
PASS=0; FAIL=0

echo "=== Test 1: output JSON should include transfer_mode field ==="
OUTPUT=$(bash scripts/ucb-retrieve.sh --query "test" --top-k 10 2>&1)
if echo "$OUTPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); assert all('transfer_mode' in r for r in d['results']), 'missing transfer_mode'" 2>/dev/null; then
  echo "PASS"; ((PASS++))
else
  echo "FAIL: transfer_mode missing from output"; ((FAIL++))
fi

echo "=== Test 2: no forbidden cards in results ==="
FORBIDDEN=$(echo "$OUTPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for r in d['results']:
    if r.get('transfer_mode') == 'forbidden':
        print(r['id'])
" 2>/dev/null)
if [[ -z "$FORBIDDEN" ]]; then
  echo "PASS: no forbidden cards"; ((PASS++))
else
  echo "FAIL: forbidden card $FORBIDDEN in results"; ((FAIL++))
fi

echo "=== Test 3: direct cards should have bonus in score_breakdown ==="
HAS_BONUS=$(echo "$OUTPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for r in d['results']:
    if r.get('transfer_mode') == 'direct' and 'transfer_bonus' in r.get('score_breakdown',{}):
        print('yes')
        break
else:
    print('no')
" 2>/dev/null)
if [[ "$HAS_BONUS" == "yes" ]]; then
  echo "PASS: direct cards have transfer_bonus"; ((PASS++))
else
  echo "FAIL: no transfer_bonus found for direct cards"; ((FAIL++))
fi

echo "--- Results: $PASS passed, $FAIL failed ---"
[[ $FAIL -eq 0 ]]
