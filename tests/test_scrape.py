"""TDD unit tests for the /scrape skill — H3-scrape.test.md (T1–T6).

These tests are the red phase: they will fail with ImportError until
tools/jobs/ is created in Iteration 2. Collection must succeed at this stage.

All tests use unittest.mock — NO real network calls, NO real Notion API,
NO real LLM calls.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
import json

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT))

# --- Guarded imports (tools/jobs/ does not exist yet in Iteration 1) ---

try:
    from notify import notify_start
    _NOTIFY_AVAILABLE = True
except ImportError as _notify_err:
    _NOTIFY_AVAILABLE = False
    _NOTIFY_IMPORT_ERROR = _notify_err

try:
    from jobs.linkedin import LinkedInScraper
    _LINKEDIN_AVAILABLE = True
except ImportError as _linkedin_err:
    _LINKEDIN_AVAILABLE = False
    _LINKEDIN_IMPORT_ERROR = _linkedin_err

try:
    from jobs.jooble import JoobleScraper
    _JOOBLE_AVAILABLE = True
except ImportError as _jooble_err:
    _JOOBLE_AVAILABLE = False
    _JOOBLE_IMPORT_ERROR = _jooble_err

try:
    from jobs.scorer import score_jobs
    _SCORER_AVAILABLE = True
except ImportError as _scorer_err:
    _SCORER_AVAILABLE = False
    _SCORER_IMPORT_ERROR = _scorer_err

try:
    from jobs.notion_writer import NotionWriter
    _NOTION_WRITER_AVAILABLE = True
except ImportError as _notion_writer_err:
    _NOTION_WRITER_AVAILABLE = False
    _NOTION_WRITER_IMPORT_ERROR = _notion_writer_err

try:
    from jobs.digest import build_digest
    _DIGEST_AVAILABLE = True
except ImportError as _digest_err:
    _DIGEST_AVAILABLE = False
    _DIGEST_IMPORT_ERROR = _digest_err


def _require(flag, err_var_name):
    """Raise ImportError inside a test body so the test fails (not errors at collect)."""
    if not flag:
        raise ImportError(globals().get(err_var_name, "module not available"))


# ---------------------------------------------------------------------------
# T1: notify_start called before any scraping begins
# ---------------------------------------------------------------------------

class TestNotifyStart(unittest.TestCase):
    """T1 — notify_start is called BEFORE any scraping tool is invoked."""

    def setUp(self):
        _require(_NOTIFY_AVAILABLE, "_NOTIFY_IMPORT_ERROR")

    def test_notify_start_sends_scrape_message(self):
        """notify_start sends a message containing '⚡' and '/scrape'."""
        mock_sender = MagicMock()
        notify_start("scrape", sender=mock_sender)
        mock_sender.assert_called_once()
        msg = mock_sender.call_args[0][0]
        self.assertIn("⚡", msg)
        self.assertIn("/scrape", msg)

    def test_notify_start_message_format(self):
        """Message is exactly '⚡ Начинаю /scrape...'."""
        mock_sender = MagicMock()
        notify_start("scrape", sender=mock_sender)
        msg = mock_sender.call_args[0][0]
        self.assertEqual(msg, "⚡ Начинаю /scrape...")

    def test_notify_start_called_with_none_sender_does_not_raise(self):
        """notify_start with sender=None must not raise."""
        notify_start("scrape", sender=None)


# ---------------------------------------------------------------------------
# T2: LinkedIn scraper returns list of dicts with required fields
# ---------------------------------------------------------------------------

class TestLinkedInScraper(unittest.TestCase):
    """T2 — LinkedInScraper.fetch() returns dicts with required fields."""

    def setUp(self):
        _require(_LINKEDIN_AVAILABLE, "_LINKEDIN_IMPORT_ERROR")

    def _mock_html(self):
        """Minimal LinkedIn-style HTML job listing."""
        return """
        <html><body>
        <div class="base-card">
          <h3 class="base-search-card__title">Product Manager</h3>
          <h4 class="base-search-card__subtitle">Acme Corp</h4>
          <span class="job-search-card__location">Belgrade, Serbia</span>
          <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/123"></a>
        </div>
        </body></html>
        """

    @patch("requests.get")
    def test_fetch_returns_list_of_dicts(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.fetch("Product Manager Belgrade")

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    @patch("requests.get")
    def test_each_result_has_required_fields(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.fetch("Product Manager Belgrade")

        required_keys = {"title", "company", "url", "location", "source"}
        for job in results:
            self.assertTrue(required_keys.issubset(job.keys()),
                            f"Missing keys in {job}: need {required_keys - job.keys()}")

    @patch("requests.get")
    def test_source_field_is_linkedin(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.fetch("Product Manager Belgrade")

        for job in results:
            self.assertEqual(job["source"], "LinkedIn",
                             f"Expected source='LinkedIn', got {job['source']!r}")


# ---------------------------------------------------------------------------
# T3: Jooble scraper returns list of dicts with required fields
# ---------------------------------------------------------------------------

class TestJoobleScraper(unittest.TestCase):
    """T3 — JoobleScraper.fetch() returns dicts with required fields."""

    def setUp(self):
        _require(_JOOBLE_AVAILABLE, "_JOOBLE_IMPORT_ERROR")

    def _mock_json_response(self):
        return {
            "jobs": [
                {
                    "title": "Product Analyst",
                    "company": "TechCo",
                    "link": "https://jooble.org/desc/456",
                    "location": "Belgrade, Serbia",
                    "snippet": "Join our team...",
                    "salary": "$2000",
                    "updated": "2026-07-13",
                }
            ]
        }

    @patch("requests.post")
    def test_fetch_returns_list_of_dicts(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        scraper = JoobleScraper(api_key="test-key")
        results = scraper.fetch("Product Analyst Belgrade")

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    @patch("requests.post")
    def test_each_result_has_required_fields(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        scraper = JoobleScraper(api_key="test-key")
        results = scraper.fetch("Product Analyst Belgrade")

        required_keys = {"title", "company", "url", "location", "source"}
        for job in results:
            self.assertTrue(required_keys.issubset(job.keys()),
                            f"Missing keys in {job}: need {required_keys - job.keys()}")

    @patch("requests.post")
    def test_source_field_is_jooble(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        scraper = JoobleScraper(api_key="test-key")
        results = scraper.fetch("Product Analyst Belgrade")

        for job in results:
            self.assertEqual(job["source"], "Jooble",
                             f"Expected source='Jooble', got {job['source']!r}")


# ---------------------------------------------------------------------------
# T4: Scorer returns score 0-100 + fit_bullets; batches of 5 per Agent() call
# ---------------------------------------------------------------------------

class TestScorer(unittest.TestCase):
    """T4 — score_jobs() adds score and fit_bullets; uses Agent() in batches of 5."""

    def setUp(self):
        _require(_SCORER_AVAILABLE, "_SCORER_IMPORT_ERROR")

    def _make_jobs(self, n):
        return [
            {
                "title": f"PM Role {i}",
                "company": f"Company {i}",
                "url": f"https://example.com/job/{i}",
                "location": "Belgrade",
                "source": "LinkedIn",
            }
            for i in range(n)
        ]

    @patch("jobs.scorer.Agent")
    def test_score_jobs_returns_same_length(self, mock_agent):
        mock_agent.return_value = json.dumps([
            {"score": 75, "fit_bullets": ["Good fit", "Remote OK"]}
            for _ in range(5)
        ])
        jobs = self._make_jobs(5)
        results = score_jobs(jobs, criteria="Product Manager in Belgrade")
        self.assertEqual(len(results), 5)

    @patch("jobs.scorer.Agent")
    def test_score_field_in_range(self, mock_agent):
        mock_agent.return_value = json.dumps([
            {"score": 80, "fit_bullets": ["Senior role", "Belgrade location"]}
            for _ in range(5)
        ])
        jobs = self._make_jobs(5)
        results = score_jobs(jobs, criteria="Product Manager in Belgrade")
        for job in results:
            self.assertIn("score", job)
            self.assertGreaterEqual(job["score"], 0)
            self.assertLessEqual(job["score"], 100)

    @patch("jobs.scorer.Agent")
    def test_fit_bullets_is_list_of_strings(self, mock_agent):
        mock_agent.return_value = json.dumps([
            {"score": 65, "fit_bullets": ["Remote friendly", "Target role"]}
            for _ in range(5)
        ])
        jobs = self._make_jobs(5)
        results = score_jobs(jobs, criteria="Product Manager in Belgrade")
        for job in results:
            self.assertIn("fit_bullets", job)
            self.assertIsInstance(job["fit_bullets"], list)
            self.assertGreater(len(job["fit_bullets"]), 0)
            for bullet in job["fit_bullets"]:
                self.assertIsInstance(bullet, str)

    @patch("jobs.scorer.Agent")
    def test_batches_of_5_per_agent_call(self, mock_agent):
        """10 jobs must produce exactly 2 Agent() calls (batch size = 5)."""
        mock_agent.return_value = json.dumps([
            {"score": 70, "fit_bullets": ["Good match"]}
            for _ in range(5)
        ])
        jobs = self._make_jobs(10)
        score_jobs(jobs, criteria="Product Manager in Belgrade")
        self.assertEqual(mock_agent.call_count, 2,
                         f"Expected 2 Agent() calls for 10 jobs, got {mock_agent.call_count}")


# ---------------------------------------------------------------------------
# T5: notion_writer dedup — skips seen URLs, updates seen_jobs.json
# ---------------------------------------------------------------------------

class TestNotionWriterDedup(unittest.TestCase):
    """T5 — NotionWriter skips URLs in seen_jobs.json; updates it after saving."""

    def setUp(self):
        _require(_NOTION_WRITER_AVAILABLE, "_NOTION_WRITER_IMPORT_ERROR")

    def _make_jobs(self):
        return [
            {
                "title": "Old Job",
                "company": "OldCo",
                "url": "https://example.com/job/99",
                "location": "Belgrade",
                "source": "LinkedIn",
                "score": 80,
                "fit_bullets": ["Seen before"],
            },
            {
                "title": "New Job",
                "company": "NewCo",
                "url": "https://example.com/job/100",
                "location": "Belgrade",
                "source": "Jooble",
                "score": 75,
                "fit_bullets": ["Fresh listing"],
            },
        ]

    @patch("builtins.open", new_callable=mock_open,
           read_data='["https://example.com/job/99"]')
    @patch("jobs.notion_writer.NotionClient")
    def test_skips_seen_url(self, mock_notion_cls, mock_file):
        mock_notion = MagicMock()
        mock_notion_cls.return_value = mock_notion

        writer = NotionWriter(seen_jobs_path="/fake/seen_jobs.json")
        writer.save_jobs(self._make_jobs())

        # Notion create should be called once (only job/100, not job/99)
        self.assertEqual(mock_notion.create_page.call_count, 1,
                         "Expected 1 Notion create_page call (job/99 must be skipped)")

    @patch("builtins.open", new_callable=mock_open,
           read_data='["https://example.com/job/99"]')
    @patch("jobs.notion_writer.NotionClient")
    def test_new_url_triggers_notion_create(self, mock_notion_cls, mock_file):
        mock_notion = MagicMock()
        mock_notion_cls.return_value = mock_notion

        writer = NotionWriter(seen_jobs_path="/fake/seen_jobs.json")
        writer.save_jobs(self._make_jobs())

        # The one call must be for the new URL
        call_args = mock_notion.create_page.call_args
        self.assertIn("https://example.com/job/100",
                      str(call_args),
                      "Notion create_page must be called with the new URL")

    @patch("builtins.open", new_callable=mock_open,
           read_data='["https://example.com/job/99"]')
    @patch("jobs.notion_writer.NotionClient")
    def test_seen_jobs_json_updated(self, mock_notion_cls, mock_file):
        mock_notion = MagicMock()
        mock_notion_cls.return_value = mock_notion

        writer = NotionWriter(seen_jobs_path="/fake/seen_jobs.json")
        writer.save_jobs(self._make_jobs())

        # File must be opened for writing to persist the updated seen list
        written_calls = [c for c in mock_file.call_args_list if "w" in str(c)]
        self.assertGreater(len(written_calls), 0,
                           "seen_jobs.json must be written after saving new jobs")


# ---------------------------------------------------------------------------
# T6: TG digest card matches template; only jobs with score >= min_score appear
# ---------------------------------------------------------------------------

class TestDigest(unittest.TestCase):
    """T6 — build_digest renders cards correctly and filters by min_score."""

    def setUp(self):
        _require(_DIGEST_AVAILABLE, "_DIGEST_IMPORT_ERROR")

    def _jobs(self):
        return [
            {
                "title": "Product Manager",
                "company": "Acme Corp",
                "url": "https://linkedin.com/jobs/view/1",
                "location": "Belgrade, Serbia",
                "work_format": "Remote",
                "salary_range": "$2000–$3000",
                "score": 75,
                "fit_bullets": ["Remote role", "PM position"],
                "fit_reason": "Remote role, PM position",
            },
            {
                "title": "Office Intern",
                "company": "Boring LLC",
                "url": "https://jooble.org/desc/2",
                "location": "New York, USA",
                "work_format": "On-site",
                "salary_range": "$500",
                "score": 45,
                "fit_bullets": ["Not a fit"],
                "fit_reason": "Not a fit",
            },
        ]

    def test_only_high_score_job_appears(self):
        """Jobs with score < min_score must not appear in digest."""
        digest = build_digest(jobs=self._jobs(), min_score=60)
        self.assertIn("Product Manager", digest)
        self.assertNotIn("Office Intern", digest,
                         "Job with score=45 must be filtered out (min_score=60)")

    def test_digest_card_contains_required_emojis(self):
        """Card must contain all 5 emoji prefixes from the template."""
        digest = build_digest(jobs=self._jobs(), min_score=60)
        for emoji in ["🏢", "📍", "💰", "⭐", "🔗"]:
            self.assertIn(emoji, digest,
                          f"Emoji {emoji} missing from digest card")

    def test_digest_card_contains_job_fields(self):
        """Card must include title, company, location, score, url."""
        digest = build_digest(jobs=self._jobs(), min_score=60)
        self.assertIn("Product Manager", digest)
        self.assertIn("Acme Corp", digest)
        self.assertIn("Belgrade", digest)
        self.assertIn("75", digest)
        self.assertIn("https://linkedin.com/jobs/view/1", digest)

    def test_score_annotation_format(self):
        """Score line must match '⭐ {score}/100 — {fit_reason}'."""
        digest = build_digest(jobs=self._jobs(), min_score=60)
        self.assertIn("75/100", digest)
        self.assertIn("—", digest)

    def test_empty_when_all_below_min_score(self):
        """Digest must be empty (or a no-results message) when all scores < min_score."""
        low_jobs = [
            {
                "title": "Low Score Job",
                "company": "NoCo",
                "url": "https://example.com/job/0",
                "location": "Nowhere",
                "work_format": "On-site",
                "salary_range": "$0",
                "score": 10,
                "fit_bullets": [],
                "fit_reason": "Not a fit",
            }
        ]
        digest = build_digest(jobs=low_jobs, min_score=60)
        self.assertNotIn("Low Score Job", digest)


if __name__ == "__main__":
    unittest.main()
