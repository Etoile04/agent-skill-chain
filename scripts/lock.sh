#!/usr/bin/env bash
# lock.sh — File-based atomic lock with TTL and stale cleanup
#
# Usage:
#   lock.sh acquire <lockfile> [ttl_seconds]  — Acquire lock (fails if held)
#   lock.sh release <lockfile>                — Release lock
#
# Atomicity: Uses ln (hard link) which is atomic on POSIX.
# Staleness: A lock older than its TTL is considered stale and auto-cleaned.
set -euo pipefail

ACTION="${1:-}"
LOCKFILE="${2:-}"
TTL="${3:-60}"

acquire() {
    local lockfile="$1" ttl="$2"

    # Check for existing lock
    if [ -f "$lockfile" ]; then
        # Read lock metadata
        local acquired_at lock_ttl
        acquired_at=$(python3 -c "
import json, sys
try:
    d = json.load(open('$lockfile'))
    print(d.get('acquired_at_epoch', 0))
except: print(0)
" 2>/dev/null || echo 0)
        lock_ttl=$(python3 -c "
import json
try:
    d = json.load(open('$lockfile'))
    print(d.get('ttl_seconds', 60))
except: print(60)
" 2>/dev/null || echo 60)

        # Check if lock is stale (older than TTL)
        local now
        now=$(python3 -c "import time; print(int(time.time()))")
        local age=$(( now - acquired_at ))
        if [ "$age" -gt "$lock_ttl" ]; then
            # Stale lock — clean up
            rm -f "$lockfile"
        else
            echo "ERROR: Lock is held (age=${age}s, ttl=${lock_ttl}s)" >&2
            return 1
        fi
    fi

    # Create lock atomically using ln (hard link fails if target exists)
    local tmpf
    tmpf=$(mktemp)
    local now_epoch
    now_epoch=$(python3 -c "import time; print(int(time.time()))")
    printf '{"PID": %d, "acquired_at": "%s", "acquired_at_epoch": %d, "ttl_seconds": %d}\n' \
        $$ "$(date -Iseconds)" "$now_epoch" "$ttl" > "$tmpf"

    # Try atomic link — fails if lockfile already exists (race condition protection)
    if ln "$tmpf" "$lockfile" 2>/dev/null; then
        rm -f "$tmpf"
        echo "Lock acquired: $lockfile"
        return 0
    else
        rm -f "$tmpf"
        echo "ERROR: Failed to acquire lock (race)" >&2
        return 1
    fi
}

release() {
    local lockfile="$1"
    if [ -f "$lockfile" ]; then
        rm -f "$lockfile"
        echo "Lock released: $lockfile"
    fi
}

case "$ACTION" in
    acquire) acquire "$LOCKFILE" "$TTL" ;;
    release) release "$LOCKFILE" ;;
    *) echo "Usage: lock.sh {acquire|release} <lockfile> [ttl_seconds]" >&2; exit 1 ;;
esac
