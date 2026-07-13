"""Jooble API scraper.

Uses Jooble's public API (POST) to fetch job listings.
Returns [] on any network error or when JOOBLE_API_KEY is not set.
"""

import os
import requests


_API_URL = "https://rs.jooble.org/api/"


class JoobleScraper:
    """Fetch job listings from the Jooble REST API."""

    def __init__(self, api_key: str = None, location: str = "Belgrade"):
        self.api_key = api_key or os.environ.get("JOOBLE_API_KEY", "")
        self.location = location

    def fetch(self, query: str, location: str = None, count: int = 20) -> list[dict]:
        """Fetch job listings matching *query* from Jooble.

        Args:
            query: Search keywords.
            location: Override the default location.
            count: Number of results to request.

        Returns:
            List of job dicts with keys: title, company, url, location, salary, source.
            Returns ``[]`` on any error or when api_key is missing.
        """
        if not self.api_key:
            print("[JoobleScraper] JOOBLE_API_KEY not set — skipping")
            return []

        loc = location or self.location
        url = f"{_API_URL}?key={self.api_key}"
        payload = {
            "keywords": query,
            "location": loc,
            "count": count,
        }

        try:
            resp = requests.post(url, json=payload, timeout=15)

            if resp.status_code != 200:
                print(f"[JoobleScraper] HTTP {resp.status_code} — aborting")
                return []

            data = resp.json()
            raw_jobs = data.get("jobs", [])

        except Exception as exc:
            print(f"[JoobleScraper] error: {exc}")
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
