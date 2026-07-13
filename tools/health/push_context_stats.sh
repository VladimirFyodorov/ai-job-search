#!/usr/bin/env bash
# push_context_stats.sh — Write context usage stats from Claude Code hooks.
#
# Called by Claude Code hooks (Stop, PostToolUse) via .claude/settings.json.
# Reads token usage from JSONL session file and writes context-stats.json.
#
# Always exits 0 — never blocks Claude.

set -euo pipefail
trap 'exit 0' ERR

STATS_PATH="/app/logs/context-stats.json"
CONTEXT_WINDOW=200000

# Find the most recent JSONL session file for this Claude session
SESSION_ID="${CLAUDE_CODE_SESSION_ID:-}"
if [ -z "${SESSION_ID}" ]; then
    exit 0
fi

JSONL_FILE="$(find "${HOME}/.claude/projects/" -name "${SESSION_ID}.jsonl" -type f 2>/dev/null | head -1 || true)"
if [ -z "${JSONL_FILE}" ] || [ ! -f "${JSONL_FILE}" ]; then
    exit 0
fi

# Extract token counts from last assistant message
LAST_USAGE="$(grep '"type":"assistant"' "${JSONL_FILE}" 2>/dev/null | tail -1 || true)"
if [ -z "${LAST_USAGE}" ]; then
    exit 0
fi

context_pct=$(python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    u = d.get('message', {}).get('usage', {})
    input_t = u.get('input_tokens', 0) or 0
    cache_r = u.get('cache_read_input_tokens', u.get('cache_read_tokens', 0)) or 0
    total = input_t + cache_r
    pct = round(total / ${CONTEXT_WINDOW} * 100, 2)
    print(pct)
except Exception as e:
    print('null')
" <<< "${LAST_USAGE}" 2>/dev/null || echo "null")

if [ "${context_pct}" = "null" ] || [ -z "${context_pct}" ]; then
    exit 0
fi

TS=$(date +%s)
mkdir -p "$(dirname "${STATS_PATH}")"
python3 -c "
import json
data = {'ts': ${TS}, 'context_pct': ${context_pct}}
with open('${STATS_PATH}', 'w') as f:
    json.dump(data, f)
" 2>/dev/null || true

exit 0
