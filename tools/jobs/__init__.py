# jobs package — scraper implementations for hunter-v2

from tools.jobs.linkedin import LinkedInScraper as scrape_linkedin
from tools.jobs.jooble import JoobleScraper as scrape_jooble
from tools.jobs import scorer, dedup, notion_writer

__all__ = ["scrape_linkedin", "scrape_jooble", "scorer", "dedup", "notion_writer"]
