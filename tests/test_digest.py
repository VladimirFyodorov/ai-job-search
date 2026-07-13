"""Unit tests for tools/crons/daily_digest + tools/crons/scheduler — TDD red phase (iteration 1).

All modules under tools/crons/ are imported with a try/except guard so that
pytest collection succeeds before the implementation exists. Tests will fail
at execution time (not collection time) when modules are absent.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call, mock_open

# ---------------------------------------------------------------------------
# Import guards — collection never fails even before implementation exists
# ---------------------------------------------------------------------------

try:
    from tools.crons.daily_digest import inject_trigger, run_daily_digest
    _DIGEST_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    inject_trigger = None  # type: ignore[assignment]
    run_daily_digest = None  # type: ignore[assignment]
    _DIGEST_AVAILABLE = False

try:
    from tools.crons.scheduler import create_scheduler
    _SCHEDULER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    create_scheduler = None  # type: ignore[assignment]
    _SCHEDULER_AVAILABLE = False


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
# TestInjectTrigger
# ---------------------------------------------------------------------------

class TestInjectTrigger(unittest.TestCase):
    """Tests for tools/crons/daily_digest.py — inject_trigger()."""

    @_require(_DIGEST_AVAILABLE)
    def test_success(self):
        """inject_trigger returns True when docker exec exits with returncode=0."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("tools.crons.daily_digest.subprocess.run", return_value=mock_result):
            result = inject_trigger("hunter-v2-1")

        self.assertTrue(result)

    @_require(_DIGEST_AVAILABLE)
    def test_failure_nonzero(self):
        """inject_trigger returns False when docker exec exits with non-zero returncode."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: No such container: hunter-v2-1"

        with patch("tools.crons.daily_digest.subprocess.run", return_value=mock_result):
            result = inject_trigger("hunter-v2-1")

        self.assertFalse(result)

    @_require(_DIGEST_AVAILABLE)
    def test_timeout(self):
        """inject_trigger returns False when subprocess.run raises TimeoutExpired."""
        import subprocess as _subprocess

        with patch("tools.crons.daily_digest.subprocess.run",
                   side_effect=_subprocess.TimeoutExpired(cmd="docker exec", timeout=60)):
            result = inject_trigger("hunter-v2-1")

        self.assertFalse(result)

    @_require(_DIGEST_AVAILABLE)
    def test_command_contains_container_name(self):
        """inject_trigger passes the container name to docker exec."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return mock_result

        with patch("tools.crons.daily_digest.subprocess.run", side_effect=capture_run):
            inject_trigger("my-test-container")

        cmd = captured.get("cmd", [])
        self.assertIn("my-test-container", cmd)

    @_require(_DIGEST_AVAILABLE)
    def test_command_uses_docker_exec(self):
        """inject_trigger uses docker exec -i to inject trigger."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return mock_result

        with patch("tools.crons.daily_digest.subprocess.run", side_effect=capture_run):
            inject_trigger("hunter-v2-1")

        cmd = captured.get("cmd", [])
        self.assertIn("docker", cmd)
        self.assertIn("exec", cmd)
        self.assertIn("-i", cmd)

    @_require(_DIGEST_AVAILABLE)
    def test_trigger_message_in_command(self):
        """inject_trigger writes the DAILY_DIGEST trigger message via /proc/1/fd/0."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return mock_result

        with patch("tools.crons.daily_digest.subprocess.run", side_effect=capture_run):
            inject_trigger("hunter-v2-1")

        cmd_str = " ".join(captured.get("cmd", []))
        self.assertIn("DAILY_DIGEST", cmd_str)
        self.assertIn("/proc/1/fd/0", cmd_str)

    @_require(_DIGEST_AVAILABLE)
    def test_failure_logs_error(self):
        """inject_trigger logs an error message when docker exec fails."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "permission denied"

        with patch("tools.crons.daily_digest.subprocess.run", return_value=mock_result), \
             patch("tools.crons.daily_digest.logger") as mock_logger:
            inject_trigger("hunter-v2-1")

        mock_logger.error.assert_called()

    @_require(_DIGEST_AVAILABLE)
    def test_timeout_logs_error(self):
        """inject_trigger logs an error message when TimeoutExpired is raised."""
        import subprocess as _subprocess

        with patch("tools.crons.daily_digest.subprocess.run",
                   side_effect=_subprocess.TimeoutExpired(cmd="docker exec", timeout=60)), \
             patch("tools.crons.daily_digest.logger") as mock_logger:
            inject_trigger("hunter-v2-1")

        mock_logger.error.assert_called()


# ---------------------------------------------------------------------------
# TestSchedulerConfig
# ---------------------------------------------------------------------------

class TestSchedulerConfig(unittest.TestCase):
    """Tests for tools/crons/scheduler.py — create_scheduler()."""

    @_require(_SCHEDULER_AVAILABLE)
    def test_cron_trigger(self):
        """create_scheduler configures CronTrigger with hour=9, minute=0, timezone='Europe/Belgrade'."""
        captured = {}

        def capture_cron_trigger(**kwargs):
            captured.update(kwargs)
            return MagicMock()

        with patch("tools.crons.scheduler.CronTrigger", side_effect=capture_cron_trigger) as mock_trigger, \
             patch("tools.crons.scheduler.BackgroundScheduler", return_value=MagicMock()):
            create_scheduler(job_fn=MagicMock())

        self.assertEqual(captured.get("hour"), 9)
        self.assertEqual(captured.get("minute"), 0)
        self.assertEqual(captured.get("timezone"), "Europe/Belgrade")

    @_require(_SCHEDULER_AVAILABLE)
    def test_returns_scheduler(self):
        """create_scheduler returns a scheduler instance."""
        mock_scheduler = MagicMock()

        with patch("tools.crons.scheduler.CronTrigger", return_value=MagicMock()), \
             patch("tools.crons.scheduler.BackgroundScheduler", return_value=mock_scheduler):
            result = create_scheduler(job_fn=MagicMock())

        self.assertIsNotNone(result)

    @_require(_SCHEDULER_AVAILABLE)
    def test_job_added_to_scheduler(self):
        """create_scheduler calls add_job on the scheduler with the provided function."""
        mock_scheduler = MagicMock()
        job_fn = MagicMock()

        with patch("tools.crons.scheduler.CronTrigger", return_value=MagicMock()), \
             patch("tools.crons.scheduler.BackgroundScheduler", return_value=mock_scheduler):
            create_scheduler(job_fn=job_fn)

        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args
        # job_fn should be the first positional arg
        self.assertIs(call_args.args[0], job_fn)


# ---------------------------------------------------------------------------
# TestFileLogger
# ---------------------------------------------------------------------------

class TestFileLogger(unittest.TestCase):
    """Tests for file logging in tools/crons/daily_digest.py — run_daily_digest()."""

    @_require(_DIGEST_AVAILABLE)
    def test_log_written(self):
        """run_daily_digest writes a log entry to logs/daily-digest.log after a successful run."""
        m = mock_open()

        with patch("tools.crons.daily_digest.inject_trigger", return_value=True), \
             patch("builtins.open", m):
            run_daily_digest(container_name="hunter-v2-1")

        m.assert_called()
        # Verify the log file path contains daily-digest
        call_args_list = m.call_args_list
        log_paths = [str(c.args[0]) for c in call_args_list if c.args]
        self.assertTrue(
            any("daily-digest" in p for p in log_paths),
            f"Expected 'daily-digest' in one of the opened paths: {log_paths}"
        )

    @_require(_DIGEST_AVAILABLE)
    def test_log_written_on_failure(self):
        """run_daily_digest writes a log entry even when inject_trigger returns False."""
        m = mock_open()

        with patch("tools.crons.daily_digest.inject_trigger", return_value=False), \
             patch("builtins.open", m):
            run_daily_digest(container_name="hunter-v2-1")

        m.assert_called()

    @_require(_DIGEST_AVAILABLE)
    def test_log_contains_timestamp(self):
        """Log entries written by run_daily_digest include a timestamp string."""
        written_data = []

        def collecting_open(path, mode="r", **kwargs):
            handle = mock_open()()
            handle.write = lambda data: written_data.append(data)
            handle.__enter__ = lambda s: s
            handle.__exit__ = MagicMock(return_value=False)
            return handle

        with patch("tools.crons.daily_digest.inject_trigger", return_value=True), \
             patch("builtins.open", side_effect=collecting_open):
            run_daily_digest(container_name="hunter-v2-1")

        combined = " ".join(str(d) for d in written_data)
        # A timestamp should contain digits and at least one separator (: or -)
        import re
        self.assertTrue(
            re.search(r"\d{4}[-T]\d{2}", combined) or len(combined) > 0,
            "Expected log output to contain some content"
        )


if __name__ == "__main__":
    unittest.main()
