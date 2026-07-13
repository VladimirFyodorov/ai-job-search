---
name: apply
description: Draft, review, and deliver a tailored cover letter PDF for a job application; log to Notion Applications DB.
allowed-tools: Read, Write, Edit, Bash, Agent, WebFetch
---

# SKILL: /apply

## Triggers

- `/apply <URL>` — Sofia sends a job posting URL
- "напиши письмо для X" / "подай на X" — natural-language trigger
- "хочу подать на <company/position>"

## Invoke Sequence

```
1. notify_start("apply", sender=reply)          # ⚡ Начинаю /apply... — FIRST action, before anything else
2. WebFetch(url)                                # Fetch job description HTML
3. Extract JD text from HTML (Bash/python strip)
4. Read CV from Notion (NOTION_CV_PAGE_ID)      # read_page(NOTION_CV_PAGE_ID) → cv_text
   └─ Fallback: read cv/ directory files if Notion read fails
5. run_loop(job_url, jd_text, cv_text, notify=reply)   # Drafter→Reviewer ≤2 rounds, returns (letter, score)
6. render_pdf(cover_letter_text, job_url)               # LaTeX → PDF in cover_letters/
7. log_application(job_id, job_url, cover_letter_text, pdf_path)  # Notion Applications DB
8. reply(files=[pdf_path])                              # Deliver PDF to Sofia
9. reply("Хочешь что-то изменить? Могу переписать или скорректировать акценты 🖊")
10. notify_done("apply", f"письмо готово (оценка {score}/100), PDF отправлен", sender=reply)
```

## Module Reference

| Symbol | Module | Description |
|--------|--------|-------------|
| `draft_cover_letter(job_url, jd_text, cv_text, feedback="")` | `tools.apply.drafter` | Calls Agent() to write cover letter |
| `review_cover_letter(cover_letter, jd_text)` | `tools.apply.reviewer` | Calls Agent() → `(score: int, feedback: str)` |
| `run_loop(job_url, jd_text, cv_text, notify=None)` | `tools.apply.drafter_reviewer_loop` | ≤2 rounds, stops at score ≥ 80; returns `(letter, score)` |
| `render_pdf(cover_letter_text, job_url)` | `tools.apply.latex_pdf` | lualatex (or `LATEX_ENGINE`); returns PDF path |
| `log_application(job_id, job_url, cover_letter_text, pdf_path)` | `tools.apply.notion_logger` | Creates Notion Applications DB page |
| `notify_start / notify_progress / notify_done` | `tools.notify` | TG notification helpers |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_CV_PAGE_ID` | Yes | Notion page ID for Sofia's CV / profile |
| `NOTION_APPLICATIONS_DB_ID` | Yes | Notion database ID for Applications |
| `LATEX_ENGINE` | No | LaTeX compiler binary (default: `lualatex`) |

## Error Handling

| Error | Sofia message (Russian) | Admin message (English) |
|-------|------------------------|------------------------|
| LaTeX compilation failure | "Не удалось сгенерировать PDF — что-то пошло не так 🛠 Попробую снова позже." | `[apply] LaTeX failed: {error}` |
| Notion write failure | "Письмо готово, но не удалось сохранить в базу. PDF отправляю напрямую." | `[apply] Notion log_application failed: {error}` |
| JD fetch failure | "Не удалось загрузить вакансию по ссылке. Пришли текст описания напрямую?" | `[apply] WebFetch failed for {url}: {error}` |
| Reviewer score always < 80 | — (silent, deliver best draft) | — |

## Drafter–Reviewer Loop

```
Round 1:
  draft_cover_letter(job_url, jd_text, cv_text)  → letter_v1
  review_cover_letter(letter_v1, jd_text)         → (score, feedback)
  if score >= 80: deliver letter_v1 ✓

Round 2 (only if score < 80):
  draft_cover_letter(job_url, jd_text, cv_text, feedback=feedback) → letter_v2
  review_cover_letter(letter_v2, jd_text)                          → (score, feedback)
  deliver letter_v2 regardless of score
```

## PDF Delivery

```python
# TG PDF send — attach file directly
reply(files=[pdf_path])
```

The PDF is sent as a document attachment. File size limit: Telegram 50 MB (cover letters are ~50 KB).

## Notion Applications DB Schema

| Property | Type | Value |
|----------|------|-------|
| Job | relation | job_id (Notion page ID) |
| cover_letter_text | rich_text | Plain text (truncated to 2000 chars) |
| pdf_path | rich_text | Local filesystem path |
| job_url | rich_text | Job posting URL |
| Status | select | "Draft" |
