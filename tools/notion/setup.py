#!/usr/bin/env python3
"""
tools/notion/setup.py — One-time Notion database setup for Hunter.

Creates 5 databases under NOTION_PARENT_PAGE_ID:
  1. Jobs        — job listings scraped and scored
  2. Applications — cover letters and application tracking
  3. Config      — key-value settings (min_score, keywords, etc.)
  4. Templates   — cover letter and email templates
  5. CV/Profile  — Sofia's structured resume (created as a page, not DB)

Writes config/notion_db_ids.json with the created DB IDs.

Usage:
  python tools/notion/setup.py            # creates databases (requires NOTION_TOKEN)
  python tools/notion/setup.py --dry-run  # prints "Would create: <name>" without API calls
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.notion.client import create_database, create_page

# ── Database schemas ──────────────────────────────────────────────────────────

JOBS_DB_SCHEMA = {
    "Name": {"title": {}},
    "Company": {"rich_text": {}},
    "URL": {"url": {}},
    "Source": {
        "select": {
            "options": [
                {"name": "Jooble", "color": "blue"},
                {"name": "SerpAPI", "color": "green"},
                {"name": "Remotive", "color": "purple"},
                {"name": "Infostud", "color": "orange"},
                {"name": "HelloWorld", "color": "red"},
                {"name": "Manual", "color": "gray"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "New", "color": "blue"},
                {"name": "Saved", "color": "yellow"},
                {"name": "Applied", "color": "orange"},
                {"name": "Interview", "color": "purple"},
                {"name": "Offer", "color": "green"},
                {"name": "Rejected", "color": "red"},
            ]
        }
    },
    "Score": {"number": {"format": "number"}},
    "Salary Min": {"number": {"format": "number"}},
    "Salary Max": {"number": {"format": "number"}},
    "Currency": {"rich_text": {}},
    "Work Format": {
        "select": {
            "options": [
                {"name": "Remote", "color": "green"},
                {"name": "Hybrid", "color": "yellow"},
                {"name": "Onsite", "color": "orange"},
            ]
        }
    },
    "Location": {"rich_text": {}},
    "Job ID": {"rich_text": {}},
    "Date Added": {"date": {}},
    "Applied Date": {"date": {}},
    "Description": {"rich_text": {}},
    "Score Rationale": {"rich_text": {}},
    "Fit Bullets": {"rich_text": {}},
    "Keyword Gaps": {"rich_text": {}},
}

APPLICATIONS_DB_SCHEMA = {
    "Name": {"title": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "Draft", "color": "gray"},
                {"name": "Sent", "color": "blue"},
                {"name": "Acknowledged", "color": "green"},
                {"name": "No Response", "color": "yellow"},
                {"name": "Rejected", "color": "red"},
            ]
        }
    },
    "Cover Letter Snippet": {"rich_text": {}},
    "Interview Notes": {"rich_text": {}},
    "Follow Up Date": {"date": {}},
    "Date Created": {"date": {}},
}

CONFIG_DB_SCHEMA = {
    "Key": {"title": {}},
    "Value": {"rich_text": {}},
    "Description": {"rich_text": {}},
}

TEMPLATES_DB_SCHEMA = {
    "Name": {"title": {}},
    "Type": {
        "select": {
            "options": [
                {"name": "Cover Letter", "color": "blue"},
                {"name": "Cold Email", "color": "green"},
                {"name": "Follow Up", "color": "orange"},
            ]
        }
    },
    "Job Type": {
        "multi_select": {
            "options": [
                {"name": "Product Manager", "color": "blue"},
                {"name": "Senior PM", "color": "purple"},
                {"name": "Lead PM", "color": "red"},
                {"name": "General", "color": "gray"},
            ]
        }
    },
    "Language": {
        "select": {
            "options": [
                {"name": "English", "color": "blue"},
                {"name": "Russian", "color": "red"},
                {"name": "Serbian", "color": "green"},
            ]
        }
    },
}

# Default config entries to seed into Config DB
DEFAULT_CONFIG = [
    ("min_score", "55", "Minimum score (0-100) to include job in digest"),
    ("digest_hour", "9", "Hour for daily digest (Belgrade time, 24h)"),
    ("search_keywords", "product manager,PM,CPO", "Comma-separated search keywords"),
    ("salary_min_eur", "2000", "Minimum monthly salary in EUR"),
    ("max_jobs_per_digest", "10", "Max job cards sent per daily digest"),
    ("cover_letter_min_score", "72", "Min score to auto-generate cover letter"),
    ("sources_enabled", "jooble,remotive,infostud", "Enabled scraper sources (comma-sep)"),
    ("search_location", "Serbia,Remote", "Comma-separated location filters"),
]

# ── Setup runner ─────────────────────────────────────────────────────────────

DATABASES_TO_CREATE = [
    ("Jobs", JOBS_DB_SCHEMA),
    ("Applications", APPLICATIONS_DB_SCHEMA),
    ("Config", CONFIG_DB_SCHEMA),
    ("Templates", TEMPLATES_DB_SCHEMA),
]


def run_setup(dry_run: bool = False) -> dict[str, str]:
    """
    Create all 5 Notion structures (4 databases + 1 profile page).
    Returns dict mapping name → id.
    """
    parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID", "")
    if not dry_run and not parent_page_id:
        print("[ERROR] NOTION_PARENT_PAGE_ID is not set", file=sys.stderr)
        sys.exit(1)

    ids: dict[str, str] = {}

    # Create 4 databases
    for name, schema in DATABASES_TO_CREATE:
        if dry_run:
            print(f"Would create: {name} (database)")
            ids[name.lower().replace("/", "_").replace(" ", "_")] = f"dry-run-{name.lower()}"
        else:
            print(f"Creating database: {name}...")
            db = create_database(parent_page_id, name, schema)
            db_id = db["id"]
            ids[name.lower().replace("/", "_").replace(" ", "_")] = db_id
            print(f"  → {name}: {db_id}")

    # Create CV/Profile page
    if dry_run:
        print("Would create: CV/Profile (page)")
        ids["cv_profile"] = "dry-run-cv-profile"
    else:
        print("Creating page: CV/Profile...")
        cv_page = create_page(
            parent={"page_id": parent_page_id},
            properties={
                "title": {
                    "title": [{"type": "text", "text": {"content": "CV / Profile — Sofia"}}]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": "CV / Profile"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Fill in Sofia's structured resume here. Sections: Summary, Target Roles, Target Locations, Experience, Skills, Languages, Education, Salary Expectations, What I'm NOT looking for."
                                },
                            }
                        ]
                    },
                },
            ],
        )
        cv_id = cv_page["id"]
        ids["cv_profile"] = cv_id
        print(f"  → CV/Profile: {cv_id}")

    # Seed Config DB with defaults (skip in dry-run)
    if not dry_run and "config" in ids:
        print("Seeding Config DB with defaults...")
        from tools.notion.client import create_page as cp

        for key, value, description in DEFAULT_CONFIG:
            cp(
                parent={"database_id": ids["config"]},
                properties={
                    "Key": {"title": [{"type": "text", "text": {"content": key}}]},
                    "Value": {"rich_text": [{"type": "text", "text": {"content": value}}]},
                    "Description": {
                        "rich_text": [{"type": "text", "text": {"content": description}}]
                    },
                },
            )
            print(f"  → config: {key}={value}")

    return ids


def write_config(ids: dict[str, str]) -> None:
    """Write config/notion_db_ids.json."""
    config_dir = Path(__file__).parent.parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    out = config_dir / "notion_db_ids.json"
    out.write_text(json.dumps(ids, indent=2) + "\n")
    print(f"\nWritten: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hunter — Notion DB setup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without calling Notion API",
    )
    args = parser.parse_args()

    ids = run_setup(dry_run=args.dry_run)

    if not args.dry_run:
        write_config(ids)
        print("\nSetup complete. Next steps:")
        print("  1. Fill in Sofia's CV/Profile page in Notion")
        print("  2. Add NOTION_CONFIG_DB_ID to .env (from config/notion_db_ids.json)")
        print("  3. docker compose up -d")
    else:
        print("\nDry run complete — no API calls made.")


if __name__ == "__main__":
    main()
