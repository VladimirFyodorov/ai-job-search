"""Jooble portal adapter — wraps JoobleScraper as a BasePortal plugin."""

import os

import requests

from .base import BasePortal

_API_URL = "https://rs.jooble.org/api/"


class JooblePortal(BasePortal):
    """Portal plugin for Jooble job search API."""

    name = "Jooble"

    def __init__(self, api_key: str = None, location: str = "Belgrade"):
        super().__init__(location=location)
        self.api_key = api_key if api_key is not None else os.environ.get("JOOBLE_API_KEY", "")

    def search(self, query: str) -> list[dict]:
        """Search for jobs via Jooble API. Returns [] if api_key missing or on any error."""
        if not self.api_key:
            print("[JooblePortal] JOOBLE_API_KEY not set — skipping")
            return []

        url = f"{_API_URL}?key={self.api_key}"
        payload = {
            "keywords": query,
            "location": self.location,
            "count": 20,
        }

        try:
            resp = requests.post(url, json=payload, timeout=15)

            if resp.status_code != 200:
                print(f"[JooblePortal] HTTP {resp.status_code} — aborting")
                return []

            data = resp.json()
            raw_jobs = data.get("jobs", [])

        except Exception as exc:
            print(f"[JooblePortal] error: {exc}")
            return []

        results = []
        for item in raw_jobs:
            results.append(
                {
                    "title": item.get("title", ""),
                    "company": item.get("company", item.get("employer", "")),
                    "url": item.get("link", ""),
                    "location": item.get("location", ""),
                    "salary": item.get("salary", ""),
                    "source": "Jooble",
                }
            )

        return results
