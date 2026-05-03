#!/bin/bash
# run_tests.sh — Run all unit + integration tests and summarize results.
#
# Exit codes: 0 = all passed, 1 = some failed
#
# Usage:
#   cd /tmp/agent-skill-chain/experiments/phase1.2/task2
#   bash run_tests.sh

set -euo pipefail

WORKDIR="/tmp/agent-skill-chain/experiments/phase1.2/task2"
cd "$WORKDIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TOTAL=0
PASSED=0
FAILED=0

run_test() {
    local label="$1"
    local test_file="$2"
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Running: ${label}${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"

    # Capture output and exit code
    set +e
    output=$(python3 "$test_file" -v 2>&1)
    exit_code=$?
    set -e

    echo "$output"

    # Parse results from unittest output (macOS-compatible, no grep -P)
    ran_line=$(echo "$output" | sed -n 's/Ran \([0-9]*\) test.*/\1/p' | tail -1)
    ran_line=${ran_line:-0}

    if [ "$exit_code" -eq 0 ]; then
        echo -e "${GREEN}  ✓ ${label}: ${ran_line} tests passed${NC}"
        PASSED=$((PASSED + ran_line))
        TOTAL=$((TOTAL + ran_line))
    else
        # Count failures from the FAILED line
        fail_count=$(echo "$output" | sed -n 's/.*failures=\([0-9]*\).*/\1/p' | tail -1)
        fail_count=${fail_count:-$ran_line}
        pass_in_run=$((ran_line - fail_count))
        echo -e "${RED}  ✗ ${label}: ${fail_count} failed, ${pass_in_run} passed${NC}"
        PASSED=$((PASSED + pass_in_run))
        FAILED=$((FAILED + fail_count))
        TOTAL=$((TOTAL + ran_line))
    fi
}

echo -e "${YELLOW}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║     Feishu API Toolchain — Full Test Suite        ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════╝${NC}"

# ---- Phase 1: Individual module tests ----

echo ""
echo -e "${YELLOW}>>> Phase 1: Module Unit Tests${NC}"

run_test "auth.py unit tests"        "test_auth.py"
run_test "endpoints.py unit tests"   "test_endpoints.py"
run_test "ratelimit.py unit tests"   "test_ratelimit.py"
run_test "reporter.py unit tests"    "test_reporter.py"
run_test "mock_transport.py tests"   "test_mock_transport.py"

# ---- Phase 2: Integration tests ----

echo ""
echo -e "${YELLOW}>>> Phase 2: End-to-End Integration Tests${NC}"

run_test "Integration tests"         "integration_test.py"

# ---- Summary ----

echo ""
echo -e "${YELLOW}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                  SUMMARY                          ║${NC}"
echo -e "${YELLOW}╠════════════════════════════════════════════════════╣${NC}"
printf "${YELLOW}║${NC}  Total tests:  %s\n" "$TOTAL"
printf "${YELLOW}║${NC}  ${GREEN}Passed:       %s${NC}\n" "$PASSED"
printf "${YELLOW}║${NC}  ${RED}Failed:       %s${NC}\n" "$FAILED"
echo -e "${YELLOW}╚════════════════════════════════════════════════════╝${NC}"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo -e "${RED}✗ Some tests failed.${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
fi
