#!/usr/bin/env bash
# checkpoint-resume.sh — Checkpoint/Resume for long-running tasks
set -euo pipefail

ACTION="${1:-}"
STATE_FILE="${2:-}"
TASK_ID="${3:-}"
STEP_ID="${4:-}"
RESUME_HINT="${5:-}"

checkpoint() {
    local state_file="$1" task_id="$2" step_id="$3" resume_hint="$4"
    python3 -c "
import json, os
state = {}
if os.path.exists('$state_file'):
    with open('$state_file') as f:
        state = json.load(f)
if state.get('task_id') != '$task_id':
    state = {'task_id': '$task_id', 'completed_steps': [], 'resume_hints': []}
state['completed_steps'].append('$step_id')
state['resume_hints'].append('$resume_hint')
state['last_checkpoint'] = '$step_id'
with open('$state_file', 'w') as f:
    json.dump(state, f, indent=2)
print(f'Checkpoint saved: $step_id')
"
}

resume() {
    local state_file="$1" task_id="$2"
    if [ ! -f "$state_file" ]; then
        echo "No checkpoint found for $task_id"
        return 1
    fi
    python3 -c "
import json
with open('$state_file') as f:
    state = json.load(f)
print(state.get('resume_hints', [''])[-1] if state.get('resume_hints') else 'No hint')
"
}

case "$ACTION" in
    checkpoint) checkpoint "$STATE_FILE" "$TASK_ID" "$STEP_ID" "$RESUME_HINT" ;;
    resume) resume "$STATE_FILE" "$TASK_ID" ;;
    *) echo "Usage: checkpoint-resume.sh {checkpoint|resume} <state_file> <task_id> [step_id] [resume_hint]" >&2; exit 1 ;;
esac
