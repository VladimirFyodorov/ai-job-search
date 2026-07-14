# Hunter v2 — Deployment Guide

Docker Compose деплой на Mac с Telegram UI.

---

## Быстрый старт

```bash
cd /Users/vf/work/hunter-v2
docker compose up -d
```

Hunter пришлёт `🤖 Hunter запустился и готов к работе!` через ~30 сек.

---

## Первый запуск (авторизация Claude Code)

**Обязательный шаг** — без него Hunter молчит ("Not logged in").

```bash
docker exec -it hunter-v2-1 claude login
```

В терминале появится URL. Если буфер в Docker не работает (нет копирования), URL нужно скопировать из TG (оркестратор умеет его прислать). После авторизации в браузере вставить код в терминал.

Авторизация сохраняется в `~/.claude/credentials` (volume mount). При следующих запусках контейнера логин не нужен.

### Срок действия токена

OAuth токен истекает. Если Hunter перестал отвечать — первым делом проверить:

```bash
python3 -c "
import json, time
d = json.load(open('/Users/vf/.claude/credentials'))
t = d['claudeAiOauth']
exp = t['expiresAt'] / 1000
print('expired:', time.time() > exp)
print('has_refresh:', bool(t.get('refreshToken')))
"
```

Если `expired: True` и Hunter молчит → повторить `docker exec -it hunter-v2-1 claude login`.

---

## Переменные окружения (.env)

| Переменная | Описание |
|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_SOFIA_CHAT_ID` | Chat ID пользователя (для уведомлений и команд-меню) |
| `TELEGRAM_ADMIN_CHAT_ID` | Chat ID администратора (для ошибок) |
| `NOTION_TOKEN` | Integration token из Notion |
| `NOTION_CONFIG_DB_ID` | ID Config DB в Notion |
| `OPENAI_API_KEY` | Для Whisper (голосовые сообщения) |
| `JOOBLE_API_KEY` | API ключ Jooble (поиск вакансий) |

⚠️ `CLAUDE_CODE_OAUTH_TOKEN` в `.env` **не нужен** — Claude Code использует `~/.claude/credentials` через volume mount. Если прописан устаревший токен — удали строку.

---

## Обновление кода

```bash
cd /Users/vf/work/hunter-v2
git pull origin master
docker compose up -d
```

Изменения в Python/AGENTS.md подхватываются без rebuild (volume mount). 

Изменения в `tools/channels/start.sh` требуют rebuild:

```bash
docker compose build && docker compose up -d
```

---

## Команды меню бота

Команды регистрируются через `scope: chat` (только для `TELEGRAM_SOFIA_CHAT_ID`) при старте контейнера (через `start.sh` после 30-секундной задержки). Bun's onStart сбрасывает `default` scope при каждом reconnect — поэтому используется `chat` scope.

Если команды пропали (например после `docker compose build`):

```bash
BOT_TOKEN=<token>
CHAT_ID=<sofia_chat_id>
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"commands":[
    {"command":"start","description":"Начать — приветствие и статус профиля"},
    {"command":"scrape","description":"Найти новые вакансии"},
    {"command":"apply","description":"CV + письмо для вакансии (URL)"},
    {"command":"rank","description":"Оценить вакансии из Notion"},
    {"command":"status","description":"Сводка поиска за сегодня"},
    {"command":"settings","description":"Показать настройки Notion"},
    {"command":"help","description":"Список всех команд"},
    {"command":"restart","description":"Перезапустить Hunter (~30 сек)"}
  ],"scope":{"type":"chat","chat_id":<CHAT_ID>}}'
```

---

## Диагностика

### Hunter молчит

1. Проверить контейнер: `docker ps` — должен быть `hunter-v2-1 Up`
2. Проверить процессы: `docker exec hunter-v2-1 pgrep -a claude` — должен быть PID
3. Проверить JSONL: `ls -lt ~/.claude/projects/-app/*.jsonl | head -3` — последний файл должен быть недавним
4. Проверить auth: `docker exec hunter-v2-1 cat /home/hunter/.claude/credentials | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claudeAiOauth'].get('accessToken','')[:30])"`
5. Если "Not logged in" в логах → `docker exec -it hunter-v2-1 claude login`

### hunter-v2-1 (unhealthy)

Статус `unhealthy` в `docker ps` означает что healthcheck не проходит — это нормально, бот работает. Healthcheck настроен на что-то что не работает изнутри Docker (например `docker ps`). Не влияет на работу бота.

### Bun орфан

Если Hunter запускался нестандартно (kill -9 контейнера), старый bun может занять TG poller slot. `start.sh` автоматически убивает орфана по `bot.pid`. Если не помогло:

```bash
docker exec hunter-v2-1 pkill -f "bun server.ts"
docker compose restart
```
