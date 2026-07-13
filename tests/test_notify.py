"""TDD tests for notify.py — notification utility functions.

These tests are expected to FAIL until notify.py is created in tools/
(Iteration 2). That is intentional: this is the TDD red phase.

Collection succeeds (tests are visible); execution fails with ImportError
surfaced via setUp so each test case reports as an error.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from notify import notify_start, notify_progress, notify_done, notify_error
    _NOTIFY_AVAILABLE = True
except ImportError as _import_error:
    _NOTIFY_AVAILABLE = False
    _NOTIFY_IMPORT_ERROR = _import_error


def _require_notify():
    """Raise ImportError inside a test so the test fails (not errors at collect)."""
    if not _NOTIFY_AVAILABLE:
        raise ImportError(f"notify module not available: {_NOTIFY_IMPORT_ERROR}")


class TestNotifyStart(unittest.TestCase):
    """notify_start sends an immediate ⚡ message before any work begins."""

    def setUp(self):
        _require_notify()

    def test_start_calls_sender_with_scrape_message(self):
        mock = MagicMock()
        notify_start("scrape", sender=mock)
        mock.assert_called_once()
        msg = mock.call_args[0][0]
        self.assertIn("⚡", msg)
        self.assertIn("/scrape", msg)

    def test_start_message_format(self):
        mock = MagicMock()
        notify_start("scrape", sender=mock)
        msg = mock.call_args[0][0]
        self.assertEqual(msg, "⚡ Начинаю /scrape...")

    def test_start_with_none_sender_does_not_raise(self):
        # When sender is None, notify_start should be a no-op
        notify_start("scrape", sender=None)


class TestNotifyProgress(unittest.TestCase):
    """notify_progress forwards the progress message verbatim to the sender."""

    def setUp(self):
        _require_notify()

    def test_progress_calls_sender_with_message(self):
        mock = MagicMock()
        notify_progress("🔍 Ищу...", sender=mock)
        mock.assert_called_once_with("🔍 Ищу...")

    def test_progress_with_none_sender_does_not_raise(self):
        notify_progress("🔍 Ищу...", sender=None)


class TestNotifyDone(unittest.TestCase):
    """notify_done sends a ✅ message including the result summary."""

    def setUp(self):
        _require_notify()

    def test_done_calls_sender_with_summary(self):
        mock = MagicMock()
        notify_done("scrape", "5 вакансий", sender=mock)
        mock.assert_called_once()
        msg = mock.call_args[0][0]
        self.assertIn("✅", msg)
        self.assertIn("/scrape", msg)
        self.assertIn("5 вакансий", msg)

    def test_done_message_format(self):
        mock = MagicMock()
        notify_done("scrape", "5 вакансий", sender=mock)
        msg = mock.call_args[0][0]
        self.assertEqual(msg, "✅ /scrape готово: 5 вакансий")

    def test_done_with_none_sender_does_not_raise(self):
        notify_done("scrape", "5 вакансий", sender=None)


class TestNotifyError(unittest.TestCase):
    """notify_error routes Russian message to Sofia, English message to admin."""

    def setUp(self):
        _require_notify()

    def test_error_with_admin_msg_en_calls_both_senders(self):
        sofia_sender = MagicMock()
        admin_sender = MagicMock()
        notify_error(
            "scrape",
            "ошибка",
            sender=sofia_sender,
            admin_sender=admin_sender,
            admin_msg_en="scrape failed: timeout",
        )
        # Sofia gets Russian message
        sofia_sender.assert_called_once()
        sofia_msg = sofia_sender.call_args[0][0]
        self.assertIn("❌", sofia_msg)
        self.assertIn("/scrape", sofia_msg)
        # Admin gets English message
        admin_sender.assert_called_once_with("scrape failed: timeout")

    def test_error_without_admin_msg_en_does_not_call_admin(self):
        sofia_sender = MagicMock()
        admin_sender = MagicMock()
        notify_error(
            "scrape",
            "ошибка",
            sender=sofia_sender,
            admin_sender=admin_sender,
        )
        sofia_sender.assert_called_once()
        admin_sender.assert_not_called()

    def test_error_admin_msg_en_defaults_to_none(self):
        # Calling without admin_msg_en keyword must not raise
        sofia_sender = MagicMock()
        admin_sender = MagicMock()
        notify_error("scrape", "ошибка", sender=sofia_sender, admin_sender=admin_sender)
        admin_sender.assert_not_called()

    def test_error_with_none_sender_does_not_raise(self):
        notify_error("scrape", "ошибка", sender=None, admin_sender=None)


if __name__ == "__main__":
    unittest.main()
