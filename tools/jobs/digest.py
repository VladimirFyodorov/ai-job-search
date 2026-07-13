"""
tools/jobs/digest.py — Format scored job listings as Telegram HTML digest cards.

build_digest(jobs, min_score=60) -> str
  Filters by score >= min_score, sorts descending by score, returns a
  newline-joined string of HTML cards ready for Telegram sendMessage.
"""

from typing import Any


def format_digest_card(job: dict[str, Any]) -> str:
    """
    Render a single job as a Telegram HTML card.

    Template:
        🏢 {title} @ {company}
        📍 {location} · {work_format}
        💰 {salary_range}
        ⭐ {score}/100 — {fit_reason}
        <a href="{url}">🔗 Открыть</a>
    """
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    work_format = job.get("work_format", "")
    salary_range = job.get("salary_range", "")
    score = job.get("score", 0)
    url = job.get("url", "")

    fit_reason = job.get("fit_reason", "")
    if not fit_reason:
        fit_bullets = job.get("fit_bullets", [])
        fit_reason = fit_bullets[0] if fit_bullets else ""

    lines = [
        f"🏢 {title} @ {company}",
        f"📍 {location} · {work_format}",
        f"💰 {salary_range}",
        f"⭐ {score}/100 — {fit_reason}",
        f'<a href="{url}">🔗 Открыть</a>',
    ]
    return "\n".join(lines)


def build_digest(jobs: list[dict[str, Any]], min_score: int = 60) -> str:
    """
    Build a full TG digest from a list of scored jobs.

    Filters out jobs below min_score, sorts by score descending,
    and returns all cards joined by a blank line.
    Returns an empty string when no jobs pass the filter.
    """
    filtered = [j for j in jobs if j.get("score", 0) >= min_score]
    filtered.sort(key=lambda j: j.get("score", 0), reverse=True)
    cards = [format_digest_card(j) for j in filtered]
    return "\n\n".join(cards)
