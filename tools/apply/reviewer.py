"""tools/apply/reviewer.py — Cover letter scoring and critique via Agent().

Uses claude-sonnet-4-6 to score a cover letter against the job description
and return structured feedback. The model is instructed to respond with
strict JSON so the score can be reliably parsed.

Agent() is imported at module level so unit tests can patch it:
    with patch("tools.apply.reviewer.Agent", mock_fn): ...
"""

from __future__ import annotations

import json

try:
    from claude_code_sdk import Agent  # type: ignore[import]
except ImportError:
    def Agent(prompt: str, **kwargs):  # type: ignore[misc]
        raise RuntimeError(
            "Agent() requires claude_code_sdk or Claude Code runtime. "
            "In tests, patch 'tools.apply.reviewer.Agent'."
        )


def review_cover_letter(
    cover_letter: str,
    jd_text: str,
) -> tuple[int, str]:
    """Score and critique a cover letter.

    Args:
        cover_letter: The cover letter text to review.
        jd_text:      The job description to score against.

    Returns:
        A ``(score, feedback)`` tuple where ``score`` is an int 0–100
        and ``feedback`` is a critique string. On parse failure, score
        falls back to 0.
    """
    prompt = (
        f"You are reviewing a cover letter for a job application.\n\n"
        f"Job description:\n{jd_text}\n\n"
        f"Cover letter:\n{cover_letter}\n\n"
        f"Score the cover letter from 0 to 100 based on how well it matches the job description. "
        f"Respond with ONLY valid JSON in the following format, with no additional text:\n"
        f'{{"score": <integer 0-100>, "feedback": "<concise critique in 1-3 sentences>"}}'
    )

    raw = Agent(prompt, model="claude-sonnet-4-6")
    return _parse_review_output(str(raw))


def _parse_review_output(raw: str) -> tuple[int, str]:
    """Parse Agent output into (score, feedback). Falls back to (0, raw) on error."""
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return 0, text or "No feedback provided."
    try:
        data = json.loads(text[start:end])
        score = int(data.get("score", 0))
        score = max(0, min(100, score))
        feedback = str(data.get("feedback", "")).strip() or "No feedback provided."
        return score, feedback
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0, text or "No feedback provided."
