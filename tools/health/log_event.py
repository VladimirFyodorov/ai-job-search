#!/usr/bin/env python3
"""log_event.py — Append structured event to /app/logs/events.jsonl

Usage:
    python3 tools/health/log_event.py <event_type> [user=...] [snippet=...] [tools=N]

event_type: inbound | outbound

Writes JSON line: {"ts": <unix>, "type": "<event_type>", "user": "...", "snippet": "...", "tools": N}
"""

import json
import os
import sys
import time

LOG_PATH = "/app/logs/events.jsonl"
LAST_REPLY_PATH = "/app/logs/last-reply-sent.txt"


def log_event(event_type: str, user: str = "", snippet: str = "", tools: int = 0) -> None:
    record = {
        "ts": int(time.time()),
        "type": event_type,
        "user": user,
        "snippet": snippet[:80],
        "tools": tools,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    if event_type == "outbound":
        with open(LAST_REPLY_PATH, "w") as f:
            f.write(str(int(time.time())))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: log_event.py <event_type> [key=value ...]", file=sys.stderr)
        sys.exit(1)

    event_type = sys.argv[1]
    kwargs: dict = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k] = v

    tools_val = int(kwargs.get("tools", 0))
    log_event(
        event_type=event_type,
        user=kwargs.get("user", ""),
        snippet=kwargs.get("snippet", ""),
        tools=tools_val,
    )


if __name__ == "__main__":
    main()
