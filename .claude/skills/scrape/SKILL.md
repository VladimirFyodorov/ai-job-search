---
name: scrape
description: >
  Scrapes LinkedIn and Jooble for new job postings, deduplicates against seen_jobs.json,
  scores results with an LLM agent, writes new jobs to Notion, and sends digest cards.
  Triggers on: /scrape, найди работу, есть что-то новое, search jobs, find jobs, new jobs
allowed-tools: Read, Write, Edit, Bash, Agent
---

# /scrape

Finds new job postings from LinkedIn and Jooble, deduplicates, scores, and delivers a digest.

---

## Triggers

Invoke this skill when the user says any of:

- `/scrape` or `/scrape <query>`
- "найди работу", "есть что-то новое?", "покажи новые вакансии"
- "find jobs", "search jobs", "any new positions?"

An optional `<query>` argument overrides the default search terms from the user profile.

---

## Invoke Sequence

### Step 1 — Notify start

```python
from tools.notify import notify_start
notify_start("scrape", sender=reply)
```

### Step 2 — Load seen jobs

```python
from tools.jobs.dedup import load_seen
seen = load_seen("config/seen_jobs.json")
```

`load_seen` returns a dict `{url: {...}}`. Creates the file if absent.

### Step 3 — Scrape portals in parallel

```python
from tools.jobs.linkedin import LinkedInScraper
from tools.jobs.jooble import JoobleScraper

linkedin_jobs = LinkedInScraper().fetch(query)
jooble_jobs   = JoobleScraper().fetch(query)
all_jobs = linkedin_jobs + jooble_jobs
```

`scrape_linkedin` and `scrape_jooble` are also available as module-level aliases
from `tools.jobs` (i.e. `from tools.jobs import scrape_linkedin, scrape_jooble`).

Each item in the returned list is a dict with at minimum:
`title`, `company`, `url`, `location`, `source`.

### Step 4 — Deduplicate

```python
from tools.jobs.dedup import is_duplicate, mark_seen, save_seen

new_jobs = []
for job in all_jobs:
    if not is_duplicate(job["url"], seen):
        new_jobs.append(job)
        mark_seen(job, seen)
```

### Step 5 — Score

```python
from tools.jobs.scorer import score_jobs

# criteria: dict loaded from config/criteria.json or a default string
scored_jobs = score_jobs(new_jobs, criteria)
```

`score_jobs` calls an LLM Agent in batches of 5 and returns the same list with
`score` (int 0–100) and `fit_bullets` (list[str]) added to each item.

### Step 6 — Write to Notion

```python
from tools.jobs.notion_writer import NotionWriter

writer = NotionWriter()
writer.write_jobs(scored_jobs, seen)
```

`write_jobs` creates a new Notion page for each job not already present in the
database, then calls `save_seen` internally to persist the updated seen dict.

**First-run note**: if `NOTION_JOBS_DB_ID` is not set in the environment, check
`config/notion_db_ids.json`. If the database does not exist yet, run:

```bash
python tools/notion/setup.py
```

### Step 7 — Build and send digest

```python
from tools.jobs.digest import build_digest

cards = build_digest(scored_jobs, min_score=60)
for card in cards:
    reply(card)
```

`build_digest` returns a list of formatted markdown strings (one per job),
sorted by score descending, filtered by `min_score`.

### Step 8 — Notify done or empty

**Jobs found:**
```python
from tools.notify import notify_done
notify_done("scrape", f"{len(cards)} подходящих из {len(all_jobs)} найденных", sender=reply)
```

**Zero results:**
```python
reply("Сегодня новых подходящих вакансий нет 🤷‍♀️")
```

### Step 9 — Error handling

```python
from tools.notify import notify_error
notify_error("scrape", "Не удалось получить вакансии", admin_msg_en=str(e), sender=reply)
```

Wrap the entire sequence in try/except and call `notify_error` on any unhandled
exception. Always attempt to save `seen` before raising.

---

## Module Reference

| Symbol | Location | Purpose |
|--------|----------|---------|
| `scrape_linkedin` / `LinkedInScraper` | `tools.jobs.linkedin` | LinkedIn portal scraper |
| `scrape_jooble` / `JoobleScraper` | `tools.jobs.jooble` | Jooble portal scraper |
| `score_jobs` | `tools.jobs.scorer` | LLM batch scoring |
| `load_seen`, `is_duplicate`, `mark_seen`, `save_seen` | `tools.jobs.dedup` | Deduplication helpers |
| `NotionWriter` | `tools.jobs.notion_writer` | Notion database writer |
| `build_digest`, `format_digest_card` | `tools.jobs.digest` | Digest card formatter |
| `notify_start`, `notify_done`, `notify_error` | `tools.notify` | Telegram notifications |

---

## Rules

1. Never fabricate job postings. Only present real results from scrapers.
2. Always deduplicate before scoring — never score jobs the user has already seen.
3. If `score < min_score` (default 60), omit the job from digest but still write it to Notion.
4. Run LinkedIn and Jooble fetches in parallel where possible.
5. Persist `seen_jobs.json` even on partial failure so the next run does not re-process items.
