# Scoring Criteria — Notion Config DB

This document describes the scoring criteria keys stored in the Notion Config DB.
Sofia can edit these directly in Notion. Hunter reads them before scoring each job.

## Keys in Config DB

| Key | Default Value | Description |
|-----|---------------|-------------|
| `remote_rule` | `remote or hybrid Belgrade max 2 days` | Work format requirement |
| `target_roles` | `Product Analytics, Product Manager, Associate PM, Growth PM, Data PM` | Target job titles |
| `salary_min_usd` | `1500` | Minimum monthly salary in USD |
| `location` | `Belgrade, Serbia or EU remote` | Acceptable locations |
| `min_score` | `60` | Minimum score (0–100) to include in digest |
| `max_jobs_per_digest` | `10` | Max job cards per digest message |
| `search_keywords` | `product manager, product analytics, associate PM` | Search terms for /scrape |
| `sources_enabled` | `linkedin,jooble` | Active scrapers (comma-separated) |
| `digest_hour` | `9` | Hour for daily digest (Belgrade/Europe time) |
| `scoring_criteria` | (see below) | Full scoring rubric for LLM evaluation |

## scoring_criteria format

The `scoring_criteria` key holds a multi-line text with the full rubric:

```
1. Work format: Remote or hybrid Belgrade ≤2 days/week (hard filter, weight: 30)
2. Role fit: Product Analytics, PM, Associate PM, Growth PM (hard filter, weight: 25)
3. Salary: ≥$1500/month or equivalent EUR (hard filter, weight: 20)
4. Location: Belgrade or EU country remote (hard filter, weight: 15)
5. Growth path: Role can lead to senior PM (bonus, weight: 10)
```

Jobs failing ANY hard filter score ≤ 20 regardless of other factors.
Jobs passing all hard filters start at 60 and gain bonus points from factor 5.

## How Hunter uses these

1. Before scoring: read all keys from Notion Config DB via `tools/notion/client.py`
2. Pass `scoring_criteria` text to scoring Agent() subagent along with the job description
3. Agent returns score (0–100) and brief rationale
4. Filter by `min_score`, sort descending, take top `max_jobs_per_digest`

## How Sofia edits them

Open Notion → Hunter v2 → Config → find the key → edit the value.
Changes take effect on the next /scrape run.
