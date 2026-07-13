"""Infostud portal adapter — scrapes infostud.com job listings."""

import requests
from bs4 import BeautifulSoup

from .base import BasePortal

_BASE_URL = "https://www.infostud.com/oglasi-za-posao/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "sr,en;q=0.9",
}


class InfostudPortal(BasePortal):
    """Portal plugin for Infostud (infostud.com) job listings."""

    name = "Infostud"

    def search(self, query: str) -> list[dict]:
        """Search Infostud job listings. Returns [] on any exception."""
        try:
            params = {"q": query}
            resp = requests.get(_BASE_URL, params=params, headers=_HEADERS, timeout=15)

            if resp.status_code != 200:
                print(f"[InfostudPortal] HTTP {resp.status_code} — returning []")
                return []

            return self._parse(resp.text)

        except Exception as exc:
            print(f"[InfostudPortal] error: {exc}")
            return []

    def _parse(self, html: str) -> list[dict]:
        """Parse job listings from Infostud HTML page."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Try multiple known selector patterns for Infostud job cards
        cards = (
            soup.select("div.job-listing")
            or soup.select("article.job-listing")
            or soup.select("li.job-listing")
            or soup.select("[class*='job-listing']")
            or soup.select("[class*='job-card']")
            or soup.select("[class*='oglas']")
        )

        for card in cards:
            title_el = (
                card.select_one("h2.job-title")
                or card.select_one("h3.job-title")
                or card.select_one(".job-title")
                or card.select_one("[class*='job-title']")
                or card.select_one("h2")
                or card.select_one("h3")
            )
            company_el = (
                card.select_one(".company-name")
                or card.select_one("[class*='company']")
                or card.select_one("[class*='employer']")
            )
            location_el = (
                card.select_one(".job-location")
                or card.select_one("[class*='location']")
                or card.select_one("[class*='grad']")
            )
            link_el = (
                card.select_one("a.job-link")
                or card.select_one("a[class*='job']")
                or card.select_one("a[href*='posao']")
                or card.select_one("a[href*='oglas']")
                or card.select_one("a")
            )

            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else self.location

            url = ""
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("http"):
                    url = href
                elif href:
                    url = f"https://www.infostud.com{href}"

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": location,
                    "source": "Infostud",
                }
            )

        return jobs
