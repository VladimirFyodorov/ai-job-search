"""LinkedIn public job-listing scraper.

Uses requests + BeautifulSoup to parse public HTML.  No authentication required.
Returns [] on any network or parse error so callers can handle failure gracefully.
"""

import time
import requests
from bs4 import BeautifulSoup

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_BASE_URL = "https://www.linkedin.com/jobs/search"


class LinkedInScraper:
    """Scrape job listings from LinkedIn public search pages."""

    name = "LinkedIn"

    def __init__(self, max_results: int = 20, location: str = "Belgrade"):
        self.max_results = max_results
        self.location = location
        self._ua_index = 0

    def _next_ua(self) -> str:
        ua = _USER_AGENTS[self._ua_index % len(_USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _headers(self) -> dict:
        return {
            "User-Agent": self._next_ua(),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _parse_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.select("div.base-card"):
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            url = link_el.get("href", "") if link_el else ""

            if not title:
                continue

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": location,
                    "source": "LinkedIn",
                    "description": "",
                }
            )
        return jobs

    def fetch(self, query: str, location: str = None, max_results: int = None) -> list[dict]:
        """Fetch job listings matching *query*.

        Args:
            query: Search keywords (e.g. ``"Product Manager Belgrade"``).
            location: Override the default location.
            max_results: Override the default max_results.

        Returns:
            List of job dicts with keys: title, company, url, location, source, description.
            Returns ``[]`` on any error.
        """
        loc = location or self.location
        limit = max_results or self.max_results
        results: list[dict] = []
        start = 0

        try:
            while len(results) < limit:
                params = {
                    "keywords": query,
                    "location": loc,
                    "start": start,
                }
                resp = requests.get(_BASE_URL, params=params, headers=self._headers(), timeout=15)

                if resp.status_code == 429:
                    print(f"[LinkedInScraper] 429 rate-limited — aborting")
                    return results

                if resp.status_code != 200:
                    print(f"[LinkedInScraper] HTTP {resp.status_code} — aborting")
                    return results

                page_jobs = self._parse_page(resp.text)
                if not page_jobs:
                    break

                results.extend(page_jobs)
                start += 25

                if len(page_jobs) < 25:
                    break  # last page

                if len(results) < limit:
                    time.sleep(2)

        except Exception as exc:
            print(f"[LinkedInScraper] error: {exc}")
            return results

        return results[:limit]

    def search(self, query: str, location: str = None) -> list[dict]:
        """Portal plugin interface — delegates to fetch()."""
        return self.fetch(query, location=location)
