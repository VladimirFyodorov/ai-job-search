---
test_id: H2-notifications
skill: notify
description: Notification utility behavior
---

# H2 Notifications — Expected Behavior

## T1: /scrape sends start notification immediately
**Trigger:** User triggers `/scrape`
**Expected:**
- `notify_start("scrape", sender=<send_fn>)` is called BEFORE any tool call (scrape, search, etc.)
- sender is called with a message containing "⚡" and "/scrape"
- Example: "⚡ Начинаю /scrape..."
- No result or tool output is awaited first

## T2: progress notification sent only for long operations
**Trigger:** A long-running operation (>3 sec) is in progress
**Expected:**
- `notify_progress("🔍 Ищу...", sender=<send_fn>)` is called during the operation
- sender receives the progress message string verbatim
- Short operations (<= 3 sec) do NOT trigger a progress notification

## T3: done notification includes result summary string
**Trigger:** `/scrape` completes successfully
**Expected:**
- `notify_done("scrape", "5 вакансий", sender=<send_fn>)` is called after work is done
- sender is called with a message containing "✅", "/scrape", and the summary
- Example: "✅ /scrape готово: 5 вакансий"

## T4: error notification — Sofia gets Russian, admin gets English
**Trigger:** An error occurs during a skill
**Expected:**
- `notify_error("scrape", "ошибка", sender=sofia_sender, admin_sender=admin_sender, admin_msg_en="scrape failed: timeout")` is called
- sofia_sender receives a Russian message containing "❌" and "/scrape"
- admin_sender receives the English message (`admin_msg_en`)
- If `admin_msg_en` is None (or not provided), admin_sender is NOT called
- `admin_msg_en` defaults to `None`

## T5: voice message command triggers same notification chain as text command
**Trigger:** Sofia sends a voice message that transcribes to "/scrape senior python"
**Expected:**
- After transcription, the same `notify_start` → (optional) `notify_progress` → `notify_done` chain fires
- Notifications are identical to what a text "/scrape senior python" would produce
- Voice input path does not skip or duplicate notifications
