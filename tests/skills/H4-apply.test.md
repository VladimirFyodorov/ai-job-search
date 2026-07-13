---
test_id: H4-apply
skill: apply
description: /apply skill — Drafter-Reviewer loop, LaTeX PDF, Notion Applications logger
---

# H4 /apply Skill — Expected Behavior

## T1: notify_start called before any Agent() invocation
**Trigger:** Sofia sends `/apply https://example.com/job/123`
**Expected:**
- `notify_start("apply", sender=reply)` is called as the very first action
- The start message "⚡ Начинаю /apply..." is delivered to Sofia before any Agent() subagent is invoked
- No Agent() call precedes the start notification

## T2: drafter returns cover letter string for given JD + CV
**Trigger:** `draft_cover_letter(job_url, jd_text, cv_text)` called with valid inputs
**Expected:**
- Returns a non-empty string (the cover letter text)
- Uses Agent() internally with claude-sonnet-4-6
- When `feedback` arg is empty string, prompt does NOT include revision instructions
- When `feedback` is non-empty, prompt includes the reviewer critique for revision

## T3: reviewer returns score (int 0–100) and feedback string
**Trigger:** `review_cover_letter(cover_letter, jd_text)` called with valid inputs
**Expected:**
- Returns a tuple `(score, feedback)` where `score` is int in range 0–100
- `feedback` is a non-empty string with critique
- Uses Agent() internally
- If Agent() returns unparseable output, score falls back to 0

## T4: loop stops after round 1 if score ≥ 80
**Trigger:** `run_loop(job_url, jd_text, cv_text)` where reviewer returns score ≥ 80 on first round
**Expected:**
- Drafter called exactly once
- Reviewer called exactly once
- Returns tuple `(cover_letter_text, score)` with score ≥ 80
- notify_progress called with round completion message

## T5: loop runs exactly 2 rounds if score stays < 80
**Trigger:** `run_loop(job_url, jd_text, cv_text)` where reviewer always returns score < 80
**Expected:**
- Drafter called exactly twice (initial draft + revision)
- Reviewer called exactly twice (after each draft)
- Returns tuple `(cover_letter_text, final_score)` after 2 rounds regardless of score
- Does NOT run a 3rd round

## T6: latex_pdf.py writes a PDF file to cover_letters/ directory
**Trigger:** `render_pdf(cover_letter_text, job_url)` called
**Expected:**
- Creates `cover_letters/` directory if it does not exist
- Writes a `.tex` file and runs lualatex (or `LATEX_ENGINE` env) via subprocess twice
- Returns path to the `.pdf` file
- Raises `RuntimeError` if subprocess returns non-zero exit code

## T7: notion_logger creates Applications DB page with all required fields
**Trigger:** `log_application(job_id, job_url, cover_letter_text, pdf_path)` called
**Expected:**
- Calls `tools.notion.client.create_page` with correct arguments
- Properties include: Job (relation to job_id), cover_letter_text (rich_text), pdf_path (rich_text), job_url (rich_text), Status=Draft (select)
- Parent is `{"database_id": NOTION_APPLICATIONS_DB_ID}` from env
- Returns the page dict from create_page

## T8: full /apply flow — notify_start first, PDF delivered via reply(files=[...])
**Trigger:** Complete `/apply <URL>` flow end-to-end with all modules mocked
**Expected:**
- notify_start is called first (before any Agent/WebFetch/subprocess)
- run_loop produces a cover letter
- render_pdf produces a PDF path
- log_application logs to Notion
- reply(files=[pdf_path]) is called to deliver PDF to Sofia
- Sofia is asked a follow-up: "Хочешь что-то изменить?"
- notify_done called at the end
