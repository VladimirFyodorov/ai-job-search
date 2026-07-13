"""LLM-based job scorer using claude-haiku via Anthropic SDK.

Exports:
    score_jobs(jobs, criteria) -> list[dict]  — adds score/fit_bullets/fail_reasons
    Agent(prompt)              -> str          — LLM call wrapper (mockable in tests)
"""

from __future__ import annotations

import json
import os
from typing import Any

# ---------------------------------------------------------------------------
# Default scoring criteria (fallback when Notion Config DB is unavailable)
# ---------------------------------------------------------------------------

DEFAULT_CRITERIA = (
    "Score each job opportunity for a candidate with these requirements:\n"
    "- Location: Remote or hybrid in Belgrade (max 2 days/week in office)\n"
    "- Target roles: Product Analytics, Product Manager, Associate PM, Growth PM\n"
    "- Minimum salary: $1500/month\n"
    "Rate fit 0-100 where 100 = perfect match."
)

BATCH_SIZE = 5
MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Agent() — LLM wrapper (patched in tests as jobs.scorer.Agent)
# ---------------------------------------------------------------------------

def Agent(prompt: str) -> str:
    """Call the LLM and return the raw text response.

    Uses the Anthropic SDK when available; falls back to a stub that returns
    an empty JSON array (so callers still get a parseable response in
    environments without the SDK installed).
    """
    try:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except ImportError:
        # SDK not installed — return empty batch so callers handle gracefully
        return "[]"


# ---------------------------------------------------------------------------
# Notion Config reader (runtime criteria, optional)
# ---------------------------------------------------------------------------

def _read_criteria_from_notion() -> str | None:
    """Try to read scoring criteria from Notion Config DB.

    Returns the criteria string or None if unavailable.
    """
    try:
        from notion_client import Client as NotionClient  # type: ignore

        token = os.environ.get("NOTION_TOKEN", "")
        db_id = os.environ.get("NOTION_CONFIG_DB_ID", "")
        if not token or not db_id:
            return None

        client = NotionClient(auth=token)
        results = client.databases.query(database_id=db_id).get("results", [])
        for page in results:
            props = page.get("properties", {})
            key_prop = props.get("Key", {})
            val_prop = props.get("Value", {})

            key_text = (
                key_prop.get("title", [{}])[0].get("plain_text", "")
                if key_prop.get("title")
                else ""
            )
            val_text = (
                val_prop.get("rich_text", [{}])[0].get("plain_text", "")
                if val_prop.get("rich_text")
                else ""
            )

            if key_text.lower() == "scoring_criteria" and val_text:
                return val_text

        return None
    except Exception:
        return None


def _get_criteria(criteria: str | None) -> str:
    """Return scoring criteria string, preferring caller-supplied value."""
    if criteria:
        return criteria
    from_notion = _read_criteria_from_notion()
    return from_notion if from_notion else DEFAULT_CRITERIA


# ---------------------------------------------------------------------------
# Core public function
# ---------------------------------------------------------------------------

def score_jobs(
    jobs: list[dict[str, Any]],
    criteria: str | None = None,
) -> list[dict[str, Any]]:
    """Score a list of job dicts using the LLM, batching 5 per call.

    Each job in the returned list gains three keys:
        score        (int, 0-100)
        fit_bullets  (list[str])
        fail_reasons (list[str])

    Args:
        jobs:     List of job dicts (title, company, url, location, source, …).
        criteria: Optional scoring criteria text. Falls back to Notion Config DB
                  then DEFAULT_CRITERIA.

    Returns:
        The same list with score/fit_bullets/fail_reasons merged into each dict.
    """
    effective_criteria = _get_criteria(criteria)
    results: list[dict[str, Any]] = []

    for batch_start in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[batch_start : batch_start + BATCH_SIZE]
        prompt = _build_prompt(batch, effective_criteria)

        raw_response = Agent(prompt)
        parsed = _parse_response(raw_response, expected_count=len(batch))

        for job, scored in zip(batch, parsed):
            merged = dict(job)
            merged["score"] = max(0, min(100, int(scored.get("score", 0))))
            merged["fit_bullets"] = scored.get("fit_bullets", [])
            merged["fail_reasons"] = scored.get("fail_reasons", [])
            results.append(merged)

    return results


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(batch: list[dict[str, Any]], criteria: str) -> str:
    jobs_text = json.dumps(
        [
            {
                "index": i,
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "url": j.get("url", ""),
                "snippet": j.get("snippet", ""),
                "salary": j.get("salary", ""),
            }
            for i, j in enumerate(batch)
        ],
        ensure_ascii=False,
        indent=2,
    )

    return (
        f"{criteria}\n\n"
        "Score each job below and respond with a JSON array of objects — one per job, "
        "in the same order. Each object must have:\n"
        '  "score": integer 0-100\n'
        '  "fit_bullets": array of 1-3 short strings explaining the fit\n'
        '  "fail_reasons": array of strings listing deal-breakers (empty if none)\n\n'
        "Jobs:\n"
        f"{jobs_text}\n\n"
        "Respond ONLY with the JSON array, no markdown fences."
    )


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_response(raw: str, expected_count: int) -> list[dict[str, Any]]:
    """Parse LLM JSON response; return safe defaults on any error."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # drop first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)
        if isinstance(data, list) and len(data) == expected_count:
            return data

        # Wrong length — fill what we have, pad the rest
        padded: list[dict[str, Any]] = []
        for i in range(expected_count):
            if i < len(data) and isinstance(data[i], dict):
                padded.append(data[i])
            else:
                padded.append(
                    {"score": 0, "fit_bullets": [], "fail_reasons": ["parse error"]}
                )
        return padded

    except Exception:
        return [
            {"score": 0, "fit_bullets": [], "fail_reasons": ["parse error"]}
            for _ in range(expected_count)
        ]
