"""Unit tests for tools/apply — TDD red phase (iteration 1).

All modules under tools/apply/ are imported with a try/except guard so that
pytest collection succeeds before the implementation exists. Tests will fail
at execution time (not collection time) when modules are absent.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Import guards — collection never fails even before implementation exists
# ---------------------------------------------------------------------------

try:
    from tools.apply.drafter import draft_cover_letter
    _DRAFTER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    draft_cover_letter = None  # type: ignore[assignment]
    _DRAFTER_AVAILABLE = False

try:
    from tools.apply.reviewer import review_cover_letter
    _REVIEWER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    review_cover_letter = None  # type: ignore[assignment]
    _REVIEWER_AVAILABLE = False

try:
    from tools.apply.drafter_reviewer_loop import run_loop
    _LOOP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    run_loop = None  # type: ignore[assignment]
    _LOOP_AVAILABLE = False

try:
    from tools.apply.latex_pdf import render_pdf
    _LATEX_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    render_pdf = None  # type: ignore[assignment]
    _LATEX_AVAILABLE = False

try:
    from tools.apply.notion_logger import log_application
    _NOTION_LOGGER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    log_application = None  # type: ignore[assignment]
    _NOTION_LOGGER_AVAILABLE = False

try:
    from tools.notify import notify_start, notify_progress, notify_done
    _NOTIFY_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    notify_start = notify_progress = notify_done = None  # type: ignore[assignment]
    _NOTIFY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helper to skip if module not available
# ---------------------------------------------------------------------------

def _require(*flags):
    """Return a skip decorator if any flag is False."""
    import functools
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for flag in flags:
                if not flag:
                    raise unittest.SkipTest("Implementation module not yet available")
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# TestDrafter
# ---------------------------------------------------------------------------

class TestDrafter(unittest.TestCase):
    """Tests for tools/apply/drafter.py — draft_cover_letter()."""

    @_require(_DRAFTER_AVAILABLE)
    def test_returns_string(self):
        """draft_cover_letter returns a non-empty string."""
        mock_agent = MagicMock(return_value="Dear Hiring Manager,\n\nI am excited...")
        with patch("tools.apply.drafter.Agent", mock_agent):
            result = draft_cover_letter(
                job_url="https://example.com/job/1",
                jd_text="We need a PM with 5 years experience.",
                cv_text="Sofia has 7 years as PM.",
            )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    @_require(_DRAFTER_AVAILABLE)
    def test_uses_agent(self):
        """draft_cover_letter calls Agent() internally."""
        mock_agent = MagicMock(return_value="Cover letter text")
        with patch("tools.apply.drafter.Agent", mock_agent):
            draft_cover_letter(
                job_url="https://example.com/job/1",
                jd_text="JD text",
                cv_text="CV text",
            )
        mock_agent.assert_called_once()

    @_require(_DRAFTER_AVAILABLE)
    def test_feedback_included_in_prompt(self):
        """When feedback is provided, it appears in the Agent prompt."""
        captured_prompt = {}

        def capture_agent(prompt, **kwargs):
            captured_prompt["prompt"] = prompt
            return "Revised cover letter"

        with patch("tools.apply.drafter.Agent", side_effect=capture_agent):
            draft_cover_letter(
                job_url="https://example.com/job/1",
                jd_text="JD text",
                cv_text="CV text",
                feedback="Score was low because X",
            )
        self.assertIn("Score was low because X", captured_prompt.get("prompt", ""))

    @_require(_DRAFTER_AVAILABLE)
    def test_no_feedback_prompt_clean(self):
        """When feedback is empty string, revision instructions are absent."""
        captured_prompt = {}

        def capture_agent(prompt, **kwargs):
            captured_prompt["prompt"] = prompt
            return "Cover letter"

        with patch("tools.apply.drafter.Agent", side_effect=capture_agent):
            draft_cover_letter(
                job_url="https://example.com/job/1",
                jd_text="JD",
                cv_text="CV",
                feedback="",
            )
        prompt = captured_prompt.get("prompt", "")
        self.assertNotIn("revision", prompt.lower())
        self.assertNotIn("feedback", prompt.lower())


# ---------------------------------------------------------------------------
# TestReviewer
# ---------------------------------------------------------------------------

class TestReviewer(unittest.TestCase):
    """Tests for tools/apply/reviewer.py — review_cover_letter()."""

    @_require(_REVIEWER_AVAILABLE)
    def test_returns_score_and_feedback(self):
        """review_cover_letter returns (int, str) tuple."""
        mock_agent = MagicMock(return_value='{"score": 85, "feedback": "Good letter."}')
        with patch("tools.apply.reviewer.Agent", mock_agent):
            score, feedback = review_cover_letter(
                cover_letter="Dear Hiring Manager...",
                jd_text="We need a PM.",
            )
        self.assertIsInstance(score, int)
        self.assertIsInstance(feedback, str)

    @_require(_REVIEWER_AVAILABLE)
    def test_score_in_range(self):
        """Score is between 0 and 100 inclusive."""
        mock_agent = MagicMock(return_value='{"score": 72, "feedback": "Needs more specifics."}')
        with patch("tools.apply.reviewer.Agent", mock_agent):
            score, _ = review_cover_letter("Letter", "JD")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @_require(_REVIEWER_AVAILABLE)
    def test_unparseable_output_fallback(self):
        """Unparseable Agent output → score fallback to 0."""
        mock_agent = MagicMock(return_value="I think this is pretty good overall.")
        with patch("tools.apply.reviewer.Agent", mock_agent):
            score, feedback = review_cover_letter("Letter", "JD")
        self.assertEqual(score, 0)
        self.assertIsInstance(feedback, str)

    @_require(_REVIEWER_AVAILABLE)
    def test_feedback_non_empty(self):
        """Feedback string is non-empty."""
        mock_agent = MagicMock(return_value='{"score": 60, "feedback": "Missing key achievements."}')
        with patch("tools.apply.reviewer.Agent", mock_agent):
            _, feedback = review_cover_letter("Letter", "JD")
        self.assertTrue(len(feedback) > 0)


# ---------------------------------------------------------------------------
# TestDrafterReviewerLoop
# ---------------------------------------------------------------------------

class TestDrafterReviewerLoop(unittest.TestCase):
    """Tests for tools/apply/drafter_reviewer_loop.py — run_loop()."""

    @_require(_LOOP_AVAILABLE)
    def test_stops_when_score_gte_80(self):
        """Loop stops after round 1 when reviewer returns score >= 80."""
        mock_notify = MagicMock()

        with patch("tools.apply.drafter_reviewer_loop.draft_cover_letter",
                   return_value="Great letter") as mock_draft, \
             patch("tools.apply.drafter_reviewer_loop.review_cover_letter",
                   return_value=(85, "Excellent!")) as mock_review:
            letter, score = run_loop(
                job_url="https://example.com/job/1",
                jd_text="JD text",
                cv_text="CV text",
                notify=mock_notify,
            )

        self.assertEqual(mock_draft.call_count, 1)
        self.assertEqual(mock_review.call_count, 1)
        self.assertGreaterEqual(score, 80)
        self.assertIsInstance(letter, str)

    @_require(_LOOP_AVAILABLE)
    def test_max_two_rounds(self):
        """Loop runs at most 2 rounds even when score stays < 80."""
        mock_notify = MagicMock()

        with patch("tools.apply.drafter_reviewer_loop.draft_cover_letter",
                   return_value="Cover letter") as mock_draft, \
             patch("tools.apply.drafter_reviewer_loop.review_cover_letter",
                   return_value=(50, "Needs improvement")) as mock_review:
            letter, score = run_loop(
                job_url="https://example.com/job/1",
                jd_text="JD",
                cv_text="CV",
                notify=mock_notify,
            )

        self.assertEqual(mock_draft.call_count, 2, "Drafter should be called twice")
        self.assertEqual(mock_review.call_count, 2, "Reviewer should be called twice")
        self.assertIsInstance(letter, str)

    @_require(_LOOP_AVAILABLE)
    def test_notify_progress_called(self):
        """notify_progress is called at each step."""
        notify_calls = []

        with patch("tools.apply.drafter_reviewer_loop.draft_cover_letter",
                   return_value="Letter"), \
             patch("tools.apply.drafter_reviewer_loop.review_cover_letter",
                   return_value=(90, "Good")):
            run_loop(
                job_url="https://example.com/job/1",
                jd_text="JD",
                cv_text="CV",
                notify=notify_calls.append,
            )

        self.assertTrue(len(notify_calls) > 0, "At least one progress notification expected")

    @_require(_LOOP_AVAILABLE)
    def test_returns_tuple(self):
        """run_loop returns a (str, int) tuple."""
        with patch("tools.apply.drafter_reviewer_loop.draft_cover_letter",
                   return_value="Letter"), \
             patch("tools.apply.drafter_reviewer_loop.review_cover_letter",
                   return_value=(80, "OK")):
            result = run_loop("https://example.com/job/1", "JD", "CV")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        letter, score = result
        self.assertIsInstance(letter, str)
        self.assertIsInstance(score, int)


# ---------------------------------------------------------------------------
# TestLatexPdf
# ---------------------------------------------------------------------------

class TestLatexPdf(unittest.TestCase):
    """Tests for tools/apply/latex_pdf.py — render_pdf()."""

    @_require(_LATEX_AVAILABLE)
    def test_pdf_created(self):
        """render_pdf returns a .pdf path when subprocess succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("tools.apply.latex_pdf.subprocess.run", return_value=mock_result), \
             patch("os.makedirs"), \
             patch("builtins.open", unittest.mock.mock_open()):
            pdf_path = render_pdf(
                cover_letter_text="Dear Hiring Manager,\n\nI am excited to apply.",
                job_url="https://example.com/job/1",
            )

        self.assertTrue(pdf_path.endswith(".pdf"))

    @_require(_LATEX_AVAILABLE)
    def test_raises_on_latex_failure(self):
        """render_pdf raises RuntimeError when subprocess returns non-zero."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"lualatex error: undefined control sequence"

        with patch("tools.apply.latex_pdf.subprocess.run", return_value=mock_result), \
             patch("os.makedirs"), \
             patch("builtins.open", unittest.mock.mock_open()):
            with self.assertRaises(RuntimeError):
                render_pdf("Cover letter", "https://example.com/job/1")

    @_require(_LATEX_AVAILABLE)
    def test_subprocess_called_twice(self):
        """lualatex is invoked twice (two-pass compilation for cross-refs)."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("tools.apply.latex_pdf.subprocess.run",
                   return_value=mock_result) as mock_run, \
             patch("os.makedirs"), \
             patch("builtins.open", unittest.mock.mock_open()):
            render_pdf("Cover letter", "https://example.com/job/1")

        self.assertEqual(mock_run.call_count, 2)

    @_require(_LATEX_AVAILABLE)
    def test_uses_latex_engine_env(self):
        """LATEX_ENGINE env var controls the compiler binary."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return mock_result

        with patch.dict(os.environ, {"LATEX_ENGINE": "xelatex"}), \
             patch("tools.apply.latex_pdf.subprocess.run", side_effect=capture_run), \
             patch("os.makedirs"), \
             patch("builtins.open", unittest.mock.mock_open()):
            render_pdf("Cover letter", "https://example.com/job/1")

        self.assertIn("xelatex", captured.get("cmd", []))


# ---------------------------------------------------------------------------
# TestNotionLogger
# ---------------------------------------------------------------------------

class TestNotionLogger(unittest.TestCase):
    """Tests for tools/apply/notion_logger.py — log_application()."""

    @_require(_NOTION_LOGGER_AVAILABLE)
    def test_log_application_calls_create_page(self):
        """log_application calls create_page with correct arguments."""
        mock_page = {"id": "page-abc-123", "object": "page"}

        with patch("tools.apply.notion_logger.create_page",
                   return_value=mock_page) as mock_create, \
             patch.dict(os.environ, {"NOTION_APPLICATIONS_DB_ID": "db-id-xyz"}):
            result = log_application(
                job_id="job-id-001",
                job_url="https://example.com/job/1",
                cover_letter_text="Dear Hiring Manager...",
                pdf_path="/Users/vf/work/hunter-v2/cover_letters/cover_001.pdf",
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args

        # Extract kwargs (parent and properties)
        if call_kwargs.kwargs:
            parent = call_kwargs.kwargs.get("parent", {})
            properties = call_kwargs.kwargs.get("properties", {})
        else:
            args = call_kwargs.args
            parent = args[0] if len(args) > 0 else {}
            properties = args[1] if len(args) > 1 else {}

        self.assertEqual(parent.get("database_id"), "db-id-xyz")
        self.assertIn("cover_letter_text", properties)
        self.assertIn("pdf_path", properties)
        self.assertIn("job_url", properties)
        self.assertEqual(result, mock_page)

    @_require(_NOTION_LOGGER_AVAILABLE)
    def test_status_is_draft(self):
        """Properties include Status=Draft select field."""
        mock_page = {"id": "page-001"}
        captured = {}

        def capture_create(parent, properties, **kwargs):
            captured["properties"] = properties
            return mock_page

        with patch("tools.apply.notion_logger.create_page",
                   side_effect=capture_create), \
             patch.dict(os.environ, {"NOTION_APPLICATIONS_DB_ID": "db-id"}):
            log_application("job-1", "https://example.com/job/1", "Letter", "/path/to.pdf")

        props = captured.get("properties", {})
        status_field = props.get("Status", {})
        select_name = (
            status_field.get("select", {}).get("name")
            if isinstance(status_field, dict) else None
        )
        self.assertEqual(select_name, "Draft")

    @_require(_NOTION_LOGGER_AVAILABLE)
    def test_job_url_rich_text(self):
        """job_url is stored as rich_text property."""
        mock_page = {"id": "page-001"}
        captured = {}

        def capture_create(parent, properties, **kwargs):
            captured["properties"] = properties
            return mock_page

        with patch("tools.apply.notion_logger.create_page",
                   side_effect=capture_create), \
             patch.dict(os.environ, {"NOTION_APPLICATIONS_DB_ID": "db-id"}):
            log_application(
                "job-1",
                "https://example.com/job/42",
                "Letter",
                "/path/to.pdf",
            )

        props = captured.get("properties", {})
        job_url_prop = props.get("job_url", {})
        self.assertIn("rich_text", job_url_prop)


# ---------------------------------------------------------------------------
# TestApplyFlow
# ---------------------------------------------------------------------------

class TestApplyFlow(unittest.TestCase):
    """Integration-level tests for the full /apply flow."""

    @_require(_NOTIFY_AVAILABLE, _LOOP_AVAILABLE, _LATEX_AVAILABLE, _NOTION_LOGGER_AVAILABLE)
    def test_notify_start_called_first(self):
        """notify_start is called before any other module function."""
        call_order = []

        def recording_notify_start(skill_name, sender=None):
            call_order.append("notify_start")
            if sender:
                sender(f"⚡ Начинаю /{skill_name}...")

        def recording_run_loop(*args, **kwargs):
            call_order.append("run_loop")
            return ("Cover letter text", 85)

        def recording_render_pdf(*args, **kwargs):
            call_order.append("render_pdf")
            return "/tmp/cover.pdf"

        def recording_log_application(*args, **kwargs):
            call_order.append("log_application")
            return {"id": "page-1"}

        # Simulate the apply skill flow
        recording_notify_start("apply", sender=lambda msg: None)
        recording_run_loop("https://example.com/job/1", "JD", "CV")
        recording_render_pdf("Cover letter text", "https://example.com/job/1")
        recording_log_application("job-1", "https://example.com/job/1", "Cover letter text", "/tmp/cover.pdf")

        self.assertEqual(call_order[0], "notify_start",
                         "notify_start must be the very first call")

    @_require(_NOTIFY_AVAILABLE)
    def test_notify_functions_callable(self):
        """notify_start, notify_progress, notify_done are all callable."""
        sender = MagicMock()
        notify_start("apply", sender=sender)
        notify_progress("🔍 Drafting round 1...", sender=sender)
        notify_done("apply", "письмо готово, PDF отправлен", sender=sender)
        self.assertEqual(sender.call_count, 3)

    @_require(_NOTIFY_AVAILABLE)
    def test_notify_start_message_format(self):
        """notify_start sends message with ⚡ and skill name."""
        messages = []
        notify_start("apply", sender=messages.append)
        self.assertTrue(len(messages) == 1)
        self.assertIn("⚡", messages[0])
        self.assertIn("apply", messages[0])

    @_require(_NOTIFY_AVAILABLE)
    def test_notify_done_message_format(self):
        """notify_done sends message with ✅ and skill name."""
        messages = []
        notify_done("apply", "PDF доставлен", sender=messages.append)
        self.assertTrue(len(messages) == 1)
        self.assertIn("✅", messages[0])
        self.assertIn("apply", messages[0])


if __name__ == "__main__":
    unittest.main()
