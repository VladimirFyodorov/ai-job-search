---
test_id: H3-scrape
skill: scrape
description: /scrape skill — scrapers, scorer, dedup, digest
---

# H3 Scrape — Expected Behavior

## T1: notify_start called before any scraping begins
**Trigger:** User triggers `/scrape [query]`
**Expected:**
- `notify_start("scrape", sender=<send_fn>)` is called BEFORE any portal tool call, WebSearch, or Agent() invocation
- sender is called with a message containing "⚡" and "/scrape"
- Example: "⚡ Начинаю /scrape..."
- No scraper result or tool output is awaited first

## T2: LinkedIn scraper returns list of dicts with required fields
**Preconditions:** HTTP GET to LinkedIn search URL returns HTML with job listings
**Steps:**
- Call `LinkedInScraper.fetch(query="Product Manager Belgrade")`
**Expected:**
- Returns a non-empty list of dicts
- Each dict contains keys: `title`, `company`, `url`, `location`, `source`
- `source` value is exactly `"LinkedIn"` for every item
- All required fields are non-empty strings

## T3: Jooble scraper returns list of dicts with required fields
**Preconditions:** HTTP POST to Jooble API returns JSON with job listings
**Steps:**
- Call `JoobleScraper.fetch(query="Product Manager Belgrade")`
**Expected:**
- Returns a non-empty list of dicts
- Each dict contains keys: `title`, `company`, `url`, `location`, `source`
- `source` value is exactly `"Jooble"` for every item
- All required fields are non-empty strings

## T4: Scorer returns score 0–100 plus fit_bullets per job; batches of 5 per Agent() call
**Preconditions:** A list of job dicts is available; Notion Config scoring criteria are loaded
**Steps:**
- Call `score_jobs(jobs)` with a list of 10 job dicts
**Expected:**
- Returns a list of the same length with `score` (int, 0–100) and `fit_bullets` (list[str]) added to each dict
- Agent() is called in batches of exactly 5 jobs per call (2 calls for 10 jobs)
- `score` is always in range 0–100 inclusive
- `fit_bullets` is a non-empty list of strings per job

## T5: notion_writer creates page for new URL; skips if URL already in seen_jobs.json; updates seen_jobs.json
**Preconditions:**
- `seen_jobs.json` exists and contains one URL: `"https://example.com/job/99"`
- Notion Jobs DB is available (mocked)
**Steps:**
- Call `notion_writer.save_jobs(jobs)` with two jobs:
  - job A: url `"https://example.com/job/99"` (already seen)
  - job B: url `"https://example.com/job/100"` (new)
**Expected:**
- Notion create-page is called exactly once (for job B only)
- `seen_jobs.json` is updated to include both URLs
- Job A is silently skipped (no Notion call, no error)

## T6: TG digest card matches template exactly; only jobs with score >= min_score appear
**Preconditions:**
- `min_score` config is 60
- Two scored jobs: job X (score=75), job Y (score=45)
**Steps:**
- Call `build_digest(jobs=[job_x, job_y], min_score=60)`
**Expected:**
- Returns a string containing exactly one digest card (for job X only)
- Card format matches the template:
  ```
  🏢 {title} @ {company}
  📍 {location} · {work_format}
  💰 {salary_range}
  ⭐ {score}/100 — {fit_reason}
  🔗 {url}
  ```
- job Y (score=45 < 60) does NOT appear in the output
- All emoji prefixes (🏢, 📍, 💰, ⭐, 🔗) are present in card for job X
