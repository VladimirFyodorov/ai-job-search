"""
tools/notion/client.py — Notion API CRUD helpers

Rate limit: 3 req/s (Notion). sleep(0.35) between writes is enforced here.
All functions raise on error (caller decides retry logic).
"""

import os
import time
import requests
from typing import Any, Optional

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

WRITE_DELAY = 0.35  # seconds between write operations (Notion rate limit)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _get(path: str, params: Optional[dict] = None) -> dict[str, Any]:
    """HTTP GET to Notion API."""
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """HTTP POST to Notion API with write delay."""
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, headers=_headers(), json=body, timeout=30)
    resp.raise_for_status()
    time.sleep(WRITE_DELAY)
    return resp.json()


def _patch(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """HTTP PATCH to Notion API with write delay."""
    url = f"{BASE_URL}{path}"
    resp = requests.patch(url, headers=_headers(), json=body, timeout=30)
    resp.raise_for_status()
    time.sleep(WRITE_DELAY)
    return resp.json()


# ── Public API ──────────────────────────────────────────────────────────────


def read_page(page_id: str) -> dict[str, Any]:
    """
    Read a Notion page by ID.
    Returns the full page object (including properties).
    To read page body (blocks), use read_page_blocks().
    """
    return _get(f"/pages/{page_id}")


def read_page_blocks(page_id: str) -> list[dict[str, Any]]:
    """Read all block children of a page."""
    results = []
    cursor = None
    while True:
        params: dict[str, Any] = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        data = _get(f"/blocks/{page_id}/children", params=params)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def create_page(
    parent: dict[str, str],
    properties: dict[str, Any],
    children: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Create a new Notion page.

    Args:
        parent: e.g. {"database_id": "abc123"} or {"page_id": "abc123"}
        properties: Notion property schema for the page
        children: optional list of block objects for page body

    Returns:
        Created page object.
    """
    body: dict[str, Any] = {"parent": parent, "properties": properties}
    if children:
        body["children"] = children
    return _post("/pages", body)


def query_db(
    db_id: str,
    filter: Optional[dict[str, Any]] = None,
    sorts: Optional[list[dict[str, Any]]] = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """
    Query a Notion database with optional filter and sort.

    Returns a flat list of page objects (auto-paginates).
    """
    results = []
    cursor = None

    while True:
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        if cursor:
            body["start_cursor"] = cursor

        data = _post(f"/databases/{db_id}/query", body)
        results.extend(data.get("results", []))

        if not data.get("has_more") or len(results) >= page_size:
            break
        cursor = data.get("next_cursor")

    return results[:page_size]


def update_page(page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
    """
    Update properties of an existing Notion page.

    Args:
        page_id: The page to update.
        properties: Dict of property name → Notion property value object.

    Returns:
        Updated page object.
    """
    return _patch(f"/pages/{page_id}", {"properties": properties})


def create_database(
    parent_page_id: str,
    title: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a new Notion database under a parent page.
    Used by setup.py.
    """
    body = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties,
        "is_inline": False,
    }
    return _post("/databases", body)
