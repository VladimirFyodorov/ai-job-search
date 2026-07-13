#!/usr/bin/env python3
"""watchdog.py — Anti-stall watchdog for Hunter bot.

Checks if Hunter received a message but hasn't replied within 5 minutes.
If stalled: restarts the Docker container and sends a TG admin alert.

Run via launchd every 2 minutes (see launchd/com.hunter.watchdog.plist).
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

HUNTER_DIR = Path.home() / "work" / "hunter"
TELEGRAM_STATE_DIR = Path.home() / ".claude" / "channels" / "telegram-hunter"
LAST_NOTIFY_FILE = TELEGRAM_STATE_DIR / "last-mcp-notify-attempt.txt"
DOCKER_COMPOSE_FILE = HUNTER_DIR / "docker-compose.yml"
STALL_THRESHOLD = 300  # seconds: 5 minutes without reply after notify


def load_env(env_path: Path) -> dict:
    env = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


def send_tg_alert(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"[watchdog] TG alert failed: {e}", file=sys.stderr)


def read_timestamp_file(path: Path) -> int:
    """Read a file containing a Unix timestamp. Returns 0 if missing or invalid."""
    try:
        content = path.read_text().strip()
        return int(content)
    except Exception:
        return 0


def get_last_reply_ts() -> int:
    """Read last-reply-sent.txt from inside the Docker container."""
    try:
        result = subprocess.run(
            ["docker", "exec", "hunter-hunter-1", "cat", "/app/logs/last-reply-sent.txt"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


def main() -> None:
    env = load_env(HUNTER_DIR / ".env")
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    admin_chat = env.get("TELEGRAM_ADMIN_CHAT_ID", "")

    if not bot_token or not admin_chat:
        print("[watchdog] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID", file=sys.stderr)
        sys.exit(1)

    now = int(time.time())

    # Read last notify attempt timestamp
    last_notify_ts = read_timestamp_file(LAST_NOTIFY_FILE)
    if last_notify_ts == 0:
        # No pending notify — nothing to check
        sys.exit(0)

    # Check if enough time has passed since last notify
    elapsed = now - last_notify_ts
    if elapsed <= STALL_THRESHOLD:
        sys.exit(0)

    # Read last reply timestamp from inside Docker
    last_reply_ts = get_last_reply_ts()

    # If bot has replied since the last notify, all is well
    if last_reply_ts >= last_notify_ts:
        sys.exit(0)

    # Stall detected — restart the container
    print(f"[watchdog] Stall detected: notify={last_notify_ts}, reply={last_reply_ts}, elapsed={elapsed}s — restarting", file=sys.stderr)

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "restart", "hunter"],
            timeout=60,
            check=True,
        )
        print("[watchdog] Container restarted successfully", file=sys.stderr)
    except Exception as e:
        print(f"[watchdog] Restart failed: {e}", file=sys.stderr)

    send_tg_alert(bot_token, admin_chat, "⚠️ Hunter не ответил за 5мин после сообщения — перезапустил")


if __name__ == "__main__":
    main()
