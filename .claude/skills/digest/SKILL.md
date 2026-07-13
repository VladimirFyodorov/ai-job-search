---
name: digest
description: Manual trigger for daily job search digest — injects DAILY_DIGEST trigger into hunter container
---

# SKILL: /digest

Manually triggers the daily job search digest. Sends the same PTY-injection trigger that the 09:00 Belgrade cron fires automatically.

## Usage

/digest

## What it does

1. Sends "⚡ Начинаю /digest..." notification
2. Calls inject_trigger() to send DAILY_DIGEST message to Claude's PTY stdin
3. Claude processes the DAILY_DIGEST trigger: reads Notion Config → scrapes jobs → scores → filters (score≥60, not seen) → sends TG digest to Sofia
4. Sends "✅ /digest запущен" notification

## Implementation

```python
from tools.crons.daily_digest import inject_trigger
import os

container = os.environ.get('HUNTER_CONTAINER_NAME', 'hunter-v2-1')
notify_start('digest')
result = inject_trigger(container)
if result:
    notify_done('digest', 'дайджест запущен в Hunter контейнере')
else:
    notify_error('digest', 'Не удалось запустить дайджест', 'inject_trigger failed')
```

## Environment variables

- `HUNTER_CONTAINER_NAME` — container to inject into (default: `hunter-v2-1`)
