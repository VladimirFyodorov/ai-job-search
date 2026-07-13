---
test_id: H1-foundation
skill: orchestrator
description: Foundation behavior — TG commands, ack, notifications
---

# H1 Foundation — Expected Behavior

## T1: /start welcome
**Trigger:** Sofia sends `/start`
**Expected:**
- Reply in Russian with welcome message mentioning Hunter name
- Explains what it does (поиск работы, вакансии, сопроводительные письма)
- Mentions available commands (/scrape, /apply, /help)
- Asks if CV/profile is ready or offers to run first search

## T2: /help commands list
**Trigger:** Sofia sends `/help`
**Expected:**
- Reply in Russian with list of all commands:
  - /scrape [запрос] — поиск вакансий
  - /apply <URL> — сопроводительное письмо + CV
  - /rank — рейтинг вакансий
  - /status — сводка
  - /settings — настройки
- Mentions voice messages are supported

## T3: 👀 ack before work
**Trigger:** Any message longer than a trivial greeting
**Expected:**
- react(👀) is called BEFORE any Bash/WebFetch/Agent tool call
- ack happens within the same turn as the message arrives

## T4: Skill start notification
**Trigger:** User triggers /scrape
**Expected:**
- First reply contains "⚡" and mentions the command name
- Example: "⚡ Начинаю /scrape..."
- Sent BEFORE results arrive

## T5: Skill done notification
**Trigger:** /scrape completes
**Expected:**
- Final reply contains "✅" and summary
- Example: "✅ /scrape готово: 5 вакансий найдено, 2 подходящих"

## T6: Voice message handling
**Trigger:** Sofia sends a voice message
**Expected:**
- download_attachment called
- ffmpeg conversion to wav
- Whisper API transcription
- Response in Russian to content (NOT the transcription echoed)
- Never reveals transcription text verbatim

## T7: Error routing
**Trigger:** Internal error occurs
**Expected:**
- Sofia sees friendly Russian message: "Что-то пошло не так, скоро починим 🛠"
- Admin (TELEGRAM_ADMIN_CHAT_ID) gets English error with details
- No raw stack traces shown to Sofia

## T8: Unknown user
**Trigger:** Message from chat_id not in access.json
**Expected:**
- Reply: "Извини, у меня нет доступа для этого чата. Обратись к администратору."
- No further processing
