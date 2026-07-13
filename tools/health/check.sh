#!/usr/bin/env bash
# check.sh — Docker healthcheck for Hunter bot.
#
# Replaces the simple `test -f bot.heartbeat` check with a multi-condition check:
#   1. bot.heartbeat exists AND age < 120s
#   2. If last-mcp-notify-attempt.txt age < 300s: last-reply-sent.txt must exist AND age < 360s
#   3. If context-stats.json exists: context_pct must be < 90
#
# Exit 0 = healthy, exit 1 = unhealthy

set -euo pipefail

HEARTBEAT_FILE="/home/hunter/.claude/channels/telegram-hunter/bot.heartbeat"
NOTIFY_FILE="/home/hunter/.claude/channels/telegram-hunter/last-mcp-notify-attempt.txt"
REPLY_FILE="/app/logs/last-reply-sent.txt"
CONTEXT_STATS_FILE="/app/logs/context-stats.json"

NOW=$(date +%s)

# --- Check 1: heartbeat exists and is fresh (<120s) ---
if [ ! -f "${HEARTBEAT_FILE}" ]; then
    echo "[health] FAIL: bot.heartbeat missing"
    exit 1
fi

HEARTBEAT_MTIME=$(stat -c %Y "${HEARTBEAT_FILE}" 2>/dev/null || stat -f %m "${HEARTBEAT_FILE}" 2>/dev/null)
HEARTBEAT_AGE=$(( NOW - HEARTBEAT_MTIME ))
if [ "${HEARTBEAT_AGE}" -ge 120 ]; then
    echo "[health] FAIL: bot.heartbeat age=${HEARTBEAT_AGE}s (>= 120s)"
    exit 1
fi

# --- Check 2: if recent notify attempt, check reply was sent ---
if [ -f "${NOTIFY_FILE}" ]; then
    NOTIFY_MTIME=$(stat -c %Y "${NOTIFY_FILE}" 2>/dev/null || stat -f %m "${NOTIFY_FILE}" 2>/dev/null)
    NOTIFY_AGE=$(( NOW - NOTIFY_MTIME ))

    if [ "${NOTIFY_AGE}" -lt 300 ]; then
        # There was a recent notify — check that a reply was recorded AFTER the notify
        if [ ! -f "${REPLY_FILE}" ]; then
            echo "[health] FAIL: pending notify (age=${NOTIFY_AGE}s) but last-reply-sent.txt missing"
            exit 1
        fi
        REPLY_MTIME=$(stat -c %Y "${REPLY_FILE}" 2>/dev/null || stat -f %m "${REPLY_FILE}" 2>/dev/null)
        REPLY_AGE=$(( NOW - REPLY_MTIME ))
        # Reply must be newer than the notify AND within 360s of now
        if [ "${REPLY_MTIME}" -lt "${NOTIFY_MTIME}" ]; then
            echo "[health] FAIL: last reply (ts=${REPLY_MTIME}) predates last notify (ts=${NOTIFY_MTIME}) — silent failure"
            exit 1
        fi
        if [ "${REPLY_AGE}" -ge 360 ]; then
            echo "[health] FAIL: pending notify (age=${NOTIFY_AGE}s) but last reply was ${REPLY_AGE}s ago (>= 360s)"
            exit 1
        fi
    fi
fi

# --- Check 3: context usage < 90% ---
if [ -f "${CONTEXT_STATS_FILE}" ]; then
    CONTEXT_PCT=$(python3 -c "
import json, sys
try:
    with open('${CONTEXT_STATS_FILE}') as f:
        d = json.load(f)
    print(d.get('context_pct', 0))
except:
    print(0)
" 2>/dev/null || echo "0")

    OVER_LIMIT=$(python3 -c "print(1 if float('${CONTEXT_PCT}') >= 90 else 0)" 2>/dev/null || echo "0")
    if [ "${OVER_LIMIT}" = "1" ]; then
        echo "[health] FAIL: context_pct=${CONTEXT_PCT} (>= 90%)"
        exit 1
    fi
fi

echo "[health] OK: heartbeat=${HEARTBEAT_AGE}s old"
exit 0
