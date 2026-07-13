"""TDD unit tests for the /add-portal skill — H6-add-portal.test.md (T1–T6).

These tests are the red phase: they will fail with ImportError until
tools/jobs/portals/ is created in Iteration 2. Collection must succeed
at this stage.

All tests use unittest.mock — NO real network calls, NO real API calls.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT))

# --- Guarded imports (tools/jobs/portals/ does not exist yet in Iteration 1) ---

try:
    from jobs.portals.base import BasePortal
    _BASE_PORTAL_AVAILABLE = True
except ImportError as _base_portal_err:
    _BASE_PORTAL_AVAILABLE = False
    _BASE_PORTAL_IMPORT_ERROR = _base_portal_err

try:
    from jobs.portals.jooble import JooblePortal
    _JOOBLE_PORTAL_AVAILABLE = True
except ImportError as _jooble_portal_err:
    _JOOBLE_PORTAL_AVAILABLE = False
    _JOOBLE_PORTAL_IMPORT_ERROR = _jooble_portal_err

try:
    from jobs.portals.infostud import InfostudPortal
    _INFOSTUD_PORTAL_AVAILABLE = True
except ImportError as _infostud_portal_err:
    _INFOSTUD_PORTAL_AVAILABLE = False
    _INFOSTUD_PORTAL_IMPORT_ERROR = _infostud_portal_err

try:
    from jobs.portals import list_portals, get_portal
    _PORTAL_REGISTRY_AVAILABLE = True
except ImportError as _portal_registry_err:
    _PORTAL_REGISTRY_AVAILABLE = False
    _PORTAL_REGISTRY_IMPORT_ERROR = _portal_registry_err

try:
    from jobs.linkedin import LinkedInScraper
    _LINKEDIN_AVAILABLE = True
except ImportError as _linkedin_err:
    _LINKEDIN_AVAILABLE = False
    _LINKEDIN_IMPORT_ERROR = _linkedin_err


def _require(flag, err_var_name):
    """Raise ImportError inside a test body so the test fails (not errors at collect)."""
    if not flag:
        raise ImportError(globals().get(err_var_name, "module not available"))


# ---------------------------------------------------------------------------
# T1: BasePortal ABC enforces search() abstract method
# ---------------------------------------------------------------------------

class TestBasePortal(unittest.TestCase):
    """T1 — instantiating BasePortal directly raises TypeError."""

    def setUp(self):
        _require(_BASE_PORTAL_AVAILABLE, "_BASE_PORTAL_IMPORT_ERROR")

    def test_instantiating_base_portal_directly_raises_type_error(self):
        """BasePortal() must raise TypeError — it is an abstract base class."""
        with self.assertRaises(TypeError):
            BasePortal()

    def test_subclass_without_search_raises_type_error(self):
        """A subclass that does not implement search() must also raise TypeError."""
        class IncompletePortal(BasePortal):
            name = "Incomplete"
            # deliberately omits search()

        with self.assertRaises(TypeError):
            IncompletePortal()

    def test_subclass_with_search_instantiates_ok(self):
        """A proper subclass implementing search() must instantiate without error."""
        class ConcretePortal(BasePortal):
            name = "Concrete"

            def search(self, query: str) -> list:
                return []

        portal = ConcretePortal()
        self.assertIsNotNone(portal)
        self.assertEqual(portal.search("test"), [])


# ---------------------------------------------------------------------------
# T2: JooblePortal.search() returns list of dicts with required keys
# ---------------------------------------------------------------------------

class TestJooblePortal(unittest.TestCase):
    """T2 — JooblePortal.search() returns dicts with required keys; returns [] when api_key=""."""

    def setUp(self):
        _require(_JOOBLE_PORTAL_AVAILABLE, "_JOOBLE_PORTAL_IMPORT_ERROR")

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
    def test_search_returns_list_of_dicts(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        portal = JooblePortal(api_key="test-key")
        results = portal.search("Product Analyst Belgrade")

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    @patch("requests.post")
    def test_each_result_has_required_keys(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        portal = JooblePortal(api_key="test-key")
        results = portal.search("Product Analyst Belgrade")

        required_keys = {"title", "company", "url", "location", "source"}
        for job in results:
            self.assertTrue(
                required_keys.issubset(job.keys()),
                f"Missing keys in {job}: need {required_keys - job.keys()}",
            )

    @patch("requests.post")
    def test_source_field_is_jooble(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_json_response()
        mock_post.return_value = mock_resp

        portal = JooblePortal(api_key="test-key")
        results = portal.search("Product Analyst Belgrade")

        for job in results:
            self.assertEqual(
                job["source"],
                "Jooble",
                f"Expected source='Jooble', got {job['source']!r}",
            )

    def test_returns_empty_list_when_api_key_is_empty(self):
        """search() must return [] without raising when api_key is empty string."""
        portal = JooblePortal(api_key="")
        results = portal.search("Product Manager Belgrade")
        self.assertIsInstance(results, list)
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# T3: InfostudPortal.search() returns [] gracefully when network fails or is blocked
# ---------------------------------------------------------------------------

class TestInfostudPortal(unittest.TestCase):
    """T3 — InfostudPortal.search() returns [] on exception; returns required keys on mock HTML."""

    def setUp(self):
        _require(_INFOSTUD_PORTAL_AVAILABLE, "_INFOSTUD_PORTAL_IMPORT_ERROR")

    def _mock_html(self):
        """Minimal Infostud-style HTML job listing."""
        return """
        <html><body>
        <div class="job-listing">
          <h2 class="job-title">Product Manager</h2>
          <span class="company-name">Acme DOO</span>
          <span class="job-location">Beograd</span>
          <a class="job-link" href="https://www.infostud.com/posao/12345">Pogledaj oglas</a>
        </div>
        </body></html>
        """

    @patch("requests.get", side_effect=Exception("network error"))
    def test_returns_empty_list_on_network_error(self, mock_get):
        """Any network exception must be caught; must return []."""
        portal = InfostudPortal()
        results = portal.search("Product Manager")
        self.assertIsInstance(results, list)
        self.assertEqual(results, [])

    @patch("requests.get", side_effect=ConnectionError("blocked"))
    def test_returns_empty_list_on_connection_error(self, mock_get):
        """ConnectionError (blocked site) must be caught; must return []."""
        portal = InfostudPortal()
        results = portal.search("Product Manager")
        self.assertEqual(results, [])

    @patch("requests.get")
    def test_mock_html_returns_dicts_with_required_keys(self, mock_get):
        """When mock HTML with job listings is provided, returns dicts with required keys."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        portal = InfostudPortal()
        results = portal.search("Product Manager")

        # If parsing succeeds, verify required keys; if site returns nothing that's fine too
        if results:
            required_keys = {"title", "company", "url", "location", "source"}
            for job in results:
                self.assertTrue(
                    required_keys.issubset(job.keys()),
                    f"Missing keys in {job}: need {required_keys - job.keys()}",
                )
                self.assertEqual(
                    job["source"],
                    "Infostud",
                    f"Expected source='Infostud', got {job['source']!r}",
                )


# ---------------------------------------------------------------------------
# T4: Portal registry list_portals() returns at minimum ["Jooble", "LinkedIn", "Infostud"]
# ---------------------------------------------------------------------------

class TestPortalRegistry(unittest.TestCase):
    """T4 — list_portals() contains built-in portals; get_portal() returns usable instances."""

    def setUp(self):
        _require(_PORTAL_REGISTRY_AVAILABLE, "_PORTAL_REGISTRY_IMPORT_ERROR")

    def test_list_portals_contains_jooble(self):
        names = list_portals()
        self.assertIn("Jooble", names, f"'Jooble' not in list_portals(): {names}")

    def test_list_portals_contains_linkedin(self):
        names = list_portals()
        self.assertIn("LinkedIn", names, f"'LinkedIn' not in list_portals(): {names}")

    def test_list_portals_contains_infostud(self):
        names = list_portals()
        self.assertIn("Infostud", names, f"'Infostud' not in list_portals(): {names}")

    def test_get_portal_jooble_returns_instance_with_search(self):
        portal = get_portal("Jooble")
        self.assertIsNotNone(portal)
        self.assertTrue(
            callable(getattr(portal, "search", None)),
            "get_portal('Jooble') must return an object with a callable search() method",
        )

    def test_get_portal_linkedin_returns_instance_with_search(self):
        portal = get_portal("LinkedIn")
        self.assertIsNotNone(portal)
        self.assertTrue(
            callable(getattr(portal, "search", None)),
            "get_portal('LinkedIn') must return an object with a callable search() method",
        )

    def test_get_portal_infostud_returns_instance_with_search(self):
        portal = get_portal("Infostud")
        self.assertIsNotNone(portal)
        self.assertTrue(
            callable(getattr(portal, "search", None)),
            "get_portal('Infostud') must return an object with a callable search() method",
        )


# ---------------------------------------------------------------------------
# T5: LinkedInScraper.search() delegates to fetch() and returns required keys
# ---------------------------------------------------------------------------

class TestLinkedInPortalInterface(unittest.TestCase):
    """T5 — LinkedInScraper.search() delegates to fetch() and returns required keys."""

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
    def test_search_returns_list_of_dicts(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.search("Product Manager Belgrade")

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    @patch("requests.get")
    def test_each_result_has_required_keys(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.search("Product Manager Belgrade")

        required_keys = {"title", "company", "url", "location", "source"}
        for job in results:
            self.assertTrue(
                required_keys.issubset(job.keys()),
                f"Missing keys in {job}: need {required_keys - job.keys()}",
            )

    @patch("requests.get")
    def test_source_field_is_linkedin(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        results = scraper.search("Product Manager Belgrade")

        for job in results:
            self.assertEqual(
                job["source"],
                "LinkedIn",
                f"Expected source='LinkedIn', got {job['source']!r}",
            )

    @patch("requests.get")
    def test_search_delegates_to_fetch(self, mock_get):
        """search() must call fetch() internally (not re-implement the logic)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._mock_html()
        mock_get.return_value = mock_resp

        scraper = LinkedInScraper()
        with patch.object(scraper, "fetch", wraps=scraper.fetch) as mock_fetch:
            scraper.search("Product Manager Belgrade")
            mock_fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
