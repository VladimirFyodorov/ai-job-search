#!/usr/bin/env bash
# start.sh — PTY wrapper for Claude Code telegram plugin
# Runs inside Docker container as ENTRYPOINT

set -euo pipefail

PLUGIN_DIR="${HOME}/.claude/plugins/cache/claude-plugins-official/telegram/0.0.6"

# Telegram plugin state directory (auth token, access.json)
export TELEGRAM_STATE_DIR="${TELEGRAM_STATE_DIR:-/home/hunter/.claude/channels/telegram-hunter-v2}"
export TELEGRAM_IS_ORCHESTRATOR="1"

# Ensure state dir exists (volume must be mounted before this runs)
mkdir -p "${TELEGRAM_STATE_DIR}"

# Write bot token to plugin env file if TELEGRAM_BOT_TOKEN is set
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" > "${TELEGRAM_STATE_DIR}/.env"
fi

# Write access.json with admin chat_id if it doesn't exist yet
if [ ! -f "${TELEGRAM_STATE_DIR}/access.json" ]; then
  ADMIN_ID="${TELEGRAM_ADMIN_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
  if [ -n "${ADMIN_ID}" ]; then
    echo "{\"dmPolicy\":\"allowlist\",\"allowFrom\":[\"${ADMIN_ID}\"],\"groups\":{},\"pending\":{}}" > "${TELEGRAM_STATE_DIR}/access.json"
  fi
fi

echo "[hunter] Starting Claude Code with telegram plugin..."
echo "[hunter] TELEGRAM_STATE_DIR=${TELEGRAM_STATE_DIR}"

# Kill any orphaned bun server.ts process from a previous container session.
# Docker restart reuses the container namespace — old bun orphans survive and
# steal the Telegram poller slot, causing new bun to go outbound-only.
if [ -f "${TELEGRAM_STATE_DIR}/bot.pid" ]; then
  OLD_BUN_PID=$(cat "${TELEGRAM_STATE_DIR}/bot.pid" 2>/dev/null || true)
  if [ -n "${OLD_BUN_PID}" ] && kill -0 "${OLD_BUN_PID}" 2>/dev/null; then
    echo "[hunter] Killing orphan bun PID ${OLD_BUN_PID}"
    kill "${OLD_BUN_PID}" 2>/dev/null || true
    sleep 1
  fi
fi
# Clear stale heartbeat so the new bun instance claims the Telegram poller slot
rm -f "${TELEGRAM_STATE_DIR}/bot.heartbeat" "${TELEGRAM_STATE_DIR}/bot.pid"

# Pre-install bun dependencies so Claude Code's auto-spawn is fast
cd "${PLUGIN_DIR}" && bun install --no-summary --silent 2>/dev/null || true
cd /app  # restore CWD so claude reads /app/AGENTS.md as its system prompt

# Send startup notification via Bot API before Claude Code takes over.
# Uses curl so it fires even before the bun poller is ready.
NOTIFY_CHAT="${TELEGRAM_SOFIA_CHAT_ID:-${TELEGRAM_ADMIN_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}}"
if [ -n "${NOTIFY_CHAT}" ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${NOTIFY_CHAT}" \
    -d "text=🤖 Hunter запустился и готов к работе!" > /dev/null 2>&1 || true
fi

# Register bot commands after bun's onStart fires (which resets them to English defaults).
# Delay 60s to ensure bun has already called setMyCommands before we override.
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  (sleep 60 && curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setMyCommands" \
    -H "Content-Type: application/json" \
    -d '{
      "commands": [
        {"command": "start",   "description": "Начать — приветствие и статус профиля"},
        {"command": "scrape",  "description": "Найти новые вакансии"},
        {"command": "apply",   "description": "CV + письмо для вакансии (URL)"},
        {"command": "rank",    "description": "Оценить вакансии из Notion"},
        {"command": "status",  "description": "Сводка поиска за сегодня"},
        {"command": "settings","description": "Показать настройки Notion"},
        {"command": "help",    "description": "Список всех команд"},
        {"command": "restart", "description": "Перезапустить Hunter (~30 сек)"}
      ],
      "scope": {"type": "default"}
    }') > /dev/null 2>&1 &
fi

# Claude Code auto-spawns the telegram plugin server on startup.
# Do NOT pre-start server.ts manually — two pollers cause message loss (race condition).
exec claude --channels plugin:telegram@claude-plugins-official \
  --model claude-sonnet-4-6 \
  --dangerously-skip-permissions
