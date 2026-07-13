"""tools/apply/drafter.py — Cover letter drafting via Agent().

Uses claude-sonnet-4-6 to write a tailored cover letter given a job
description and Sofia's CV text. When feedback from the Reviewer is
provided, the prompt includes a revision instruction.

Agent() is imported at module level so unit tests can patch it:
    with patch("tools.apply.drafter.Agent", mock_fn): ...
"""

from __future__ import annotations

try:
    from claude_code_sdk import Agent  # type: ignore[import]
except ImportError:
    def Agent(prompt: str, **kwargs):  # type: ignore[misc]
        raise RuntimeError(
            "Agent() requires claude_code_sdk or Claude Code runtime. "
            "In tests, patch 'tools.apply.drafter.Agent'."
        )


def draft_cover_letter(
    job_url: str,
    jd_text: str,
    cv_text: str,
    feedback: str = "",
) -> str:
    """Draft a cover letter tailored to the job description.

    Args:
        job_url:  URL of the job posting (included in prompt for context).
        jd_text:  Full job description text.
        cv_text:  Sofia's CV / profile text.
        feedback: Reviewer critique from a previous round. When non-empty,
                  the model is asked to revise rather than draft from scratch.

    Returns:
        Cover letter as a plain-text string.
    """
    if feedback:
        prompt = (
            f"You are writing a cover letter for a job application.\n\n"
            f"Job URL: {job_url}\n\n"
            f"Job description:\n{jd_text}\n\n"
            f"Applicant CV / profile:\n{cv_text}\n\n"
            f"Previous draft was reviewed and received the following critique:\n"
            f"{feedback}\n\n"
            f"Please revise the cover letter to address the critique. "
            f"Write only the cover letter text — no preamble."
        )
    else:
        prompt = (
            f"You are writing a cover letter for a job application.\n\n"
            f"Job URL: {job_url}\n\n"
            f"Job description:\n{jd_text}\n\n"
            f"Applicant CV / profile:\n{cv_text}\n\n"
            f"Write a concise, tailored cover letter (3–4 paragraphs). "
            f"Highlight skills from the CV that match the JD. "
            f"Write only the cover letter text — no preamble."
        )

    result = Agent(prompt, model="claude-sonnet-4-6")
    return str(result).strip()
