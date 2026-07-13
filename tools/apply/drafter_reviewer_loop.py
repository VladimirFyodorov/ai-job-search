"""tools/apply/drafter_reviewer_loop.py — Drafter → Reviewer iteration loop.

Runs up to 2 rounds of drafting and review, stopping early when the
Reviewer scores the cover letter at 80 or above.
"""

from __future__ import annotations

from typing import Callable, Optional

from tools.apply.drafter import draft_cover_letter
from tools.apply.reviewer import review_cover_letter

MAX_ROUNDS = 2
PASS_SCORE = 80


def run_loop(
    job_url: str,
    jd_text: str,
    cv_text: str,
    notify: Optional[Callable[[str], None]] = None,
) -> tuple[str, int]:
    """Run the Drafter → Reviewer loop.

    Args:
        job_url: URL of the job posting.
        jd_text: Full job description text.
        cv_text: Sofia's CV / profile text.
        notify:  Optional callable for progress messages (e.g. ``reply``).

    Returns:
        ``(final_cover_letter, final_score)`` after at most ``MAX_ROUNDS``
        rounds, or as soon as the score reaches ``PASS_SCORE``.
    """
    cover_letter = ""
    score = 0
    feedback = ""

    for round_num in range(1, MAX_ROUNDS + 1):
        _notify(notify, f"🖊 Раунд {round_num}/{MAX_ROUNDS}: составляю письмо…")
        cover_letter = draft_cover_letter(
            job_url=job_url,
            jd_text=jd_text,
            cv_text=cv_text,
            feedback=feedback,
        )

        _notify(notify, f"🔍 Раунд {round_num}/{MAX_ROUNDS}: проверяю качество…")
        score, feedback = review_cover_letter(cover_letter, jd_text)

        _notify(notify, f"📊 Раунд {round_num}/{MAX_ROUNDS}: оценка {score}/100")

        if score >= PASS_SCORE:
            break

    return cover_letter, score


def _notify(notify: Optional[Callable[[str], None]], message: str) -> None:
    if notify is not None:
        notify(message)
