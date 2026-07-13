"""tools/apply/notion_logger.py — Log job application to Notion Applications DB.

Creates a new page in the Applications database with the cover letter text,
PDF path, job URL, and an initial Status of "Draft".
"""

from __future__ import annotations

import os
from typing import Any

from tools.notion.client import create_page

NOTION_APPLICATIONS_DB_ID = os.environ.get("NOTION_APPLICATIONS_DB_ID", "")


def log_application(
    job_id: str,
    job_url: str,
    cover_letter_text: str,
    pdf_path: str,
) -> dict[str, Any]:
    """Create an Applications DB entry for this job application.

    Args:
        job_id:             Notion page ID of the related Job entry.
        job_url:            URL of the job posting.
        cover_letter_text:  Plain-text cover letter (stored as rich_text).
        pdf_path:           Local filesystem path to the generated PDF.

    Returns:
        The Notion page dict returned by ``create_page``.
    """
    db_id = os.environ.get("NOTION_APPLICATIONS_DB_ID", NOTION_APPLICATIONS_DB_ID)

    properties: dict[str, Any] = {
        "cover_letter_text": {
            "rich_text": [{"type": "text", "text": {"content": cover_letter_text[:2000]}}]
        },
        "pdf_path": {
            "rich_text": [{"type": "text", "text": {"content": pdf_path}}]
        },
        "job_url": {
            "rich_text": [{"type": "text", "text": {"content": job_url}}]
        },
        "Status": {
            "select": {"name": "Draft"}
        },
    }

    if job_id:
        properties["Job"] = {
            "relation": [{"id": job_id}]
        }

    return create_page(
        parent={"database_id": db_id},
        properties=properties,
    )
