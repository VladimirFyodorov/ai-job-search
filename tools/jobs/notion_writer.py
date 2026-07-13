"""
tools/jobs/notion_writer.py — Write scored jobs to Notion, with URL-based dedup.

NotionClient wraps tools/notion/client.py create_page().
NotionWriter loads seen_jobs.json (a JSON list of URLs), skips already-seen
URLs, writes new pages to Notion, and persists the updated list.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow running from repo root or tools/
_TOOLS_DIR = Path(__file__).parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from notion import client as _notion_api


class NotionClient:
    """Thin OO wrapper around tools/notion/client.py for testability."""

    def __init__(self, db_id: str = ""):
        self.db_id = db_id

    def create_page(self, properties: dict[str, Any], children: list | None = None) -> dict[str, Any]:
        parent = {"database_id": self.db_id}
        return _notion_api.create_page(parent=parent, properties=properties, children=children)


def _get_jobs_db_id() -> str:
    """Read NOTION_JOBS_DB_ID from env or config/notion_db_ids.json."""
    db_id = os.environ.get("NOTION_JOBS_DB_ID", "")
    if db_id:
        return db_id
    config_path = Path(__file__).parent.parent.parent / "config" / "notion_db_ids.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return data.get("jobs", "")
    return ""


def _job_to_properties(job: dict[str, Any]) -> dict[str, Any]:
    """Convert a job dict to Notion page properties schema."""
    fit_bullets = job.get("fit_bullets", [])
    fit_text = " | ".join(fit_bullets) if fit_bullets else ""
    return {
        "Name": {"title": [{"text": {"content": job.get("title", "")}}]},
        "Company": {"rich_text": [{"text": {"content": job.get("company", "")}}]},
        "URL": {"url": job.get("url", "")},
        "Location": {"rich_text": [{"text": {"content": job.get("location", "")}}]},
        "Source": {"select": {"name": job.get("source", "")}},
        "Score": {"number": job.get("score", 0)},
        "FitBullets": {"rich_text": [{"text": {"content": fit_text}}]},
        "WorkFormat": {"rich_text": [{"text": {"content": job.get("work_format", "")}}]},
        "SalaryRange": {"rich_text": [{"text": {"content": job.get("salary_range", "")}}]},
    }


class NotionWriter:
    """
    Writes scored jobs to a Notion database, deduplicating by URL.

    seen_jobs_path: path to a JSON file containing a list of already-saved URLs.
    """

    def __init__(self, seen_jobs_path: str = "logs/seen_jobs.json", db_id: str = ""):
        self.seen_jobs_path = seen_jobs_path
        self.db_id = db_id or _get_jobs_db_id()
        self.notion = NotionClient(db_id=self.db_id)
        self._seen: list[str] = self._load_seen()

    def _load_seen(self) -> list[str]:
        try:
            with open(self.seen_jobs_path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return []

    def _save_seen(self) -> None:
        path = Path(self.seen_jobs_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # directory may already exist or path is virtual (tests)
        with open(self.seen_jobs_path, "w") as f:
            json.dump(self._seen, f, indent=2)

    def save_jobs(self, jobs: list[dict[str, Any]]) -> tuple[int, int]:
        """
        Write new jobs to Notion, skip duplicates.

        Returns (written, skipped) counts.
        """
        written = 0
        skipped = 0
        for job in jobs:
            url = job.get("url", "")
            if url in self._seen:
                skipped += 1
                continue
            props = _job_to_properties(job)
            self.notion.create_page(properties=props)
            self._seen.append(url)
            written += 1
        if written:
            self._save_seen()
        return written, skipped
