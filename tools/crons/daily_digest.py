"""
Daily digest cron trigger.

Injects the DAILY_DIGEST trigger message into the running Hunter Claude container
via docker exec + /proc/1/fd/0 (PTY stdin injection).

Usage:
    python tools/crons/daily_digest.py

Environment variables:
    HUNTER_CONTAINER_NAME — Docker container name (default: hunter-v2-1)

This script is run by launchd (launchd/com.hunter.plist) at 09:00 Belgrade time,
or by any other scheduler. It logs to stdout; launchd redirects to
/tmp/hunter-daily-digest.log.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [daily_digest] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

TRIGGER_MESSAGE = "DAILY_DIGEST: run daily job search digest"


def inject_trigger(container_name: str) -> bool:
    """Inject DAILY_DIGEST trigger into the Claude container's stdin.

    Uses docker exec with PTY stdin to write directly to /proc/1/fd/0,
    which is Claude's controlling terminal (PTY master).

    Args:
        container_name: Docker container name (e.g. 'hunter-v2-1').

    Returns:
        True on success, False on failure.
    """
    cmd = [
        "docker", "exec", "-i",
        container_name,
        "sh", "-c",
        f'echo "{TRIGGER_MESSAGE}" > /proc/1/fd/0',
    ]
    logger.info("Injecting trigger into container '%s'", container_name)
    logger.info("Command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        logger.error("docker exec timed out after 60s — Docker daemon may be unresponsive")
        return False

    if result.returncode == 0:
        logger.info("Trigger injected successfully")
        return True
    else:
        logger.error(
            "docker exec failed (exit %d): stdout=%r stderr=%r",
            result.returncode,
            result.stdout,
            result.stderr,
        )
        return False


LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'daily-digest.log')


def run_daily_digest(container_name: str | None = None) -> bool:
    """Run the daily digest: inject trigger into hunter container and log result.

    Writes log entries to logs/daily-digest.log (in addition to stdout logging).

    Args:
        container_name: Docker container name. Defaults to HUNTER_CONTAINER_NAME env var
                        or 'hunter-v2-1'.

    Returns:
        True on success, False on failure.
    """
    if container_name is None:
        container_name = os.environ.get('HUNTER_CONTAINER_NAME', 'hunter-v2-1')

    now = datetime.now().isoformat(timespec='seconds')
    logger.info("run_daily_digest: starting run for container=%s at %s", container_name, now)

    result = inject_trigger(container_name)

    status = "completed successfully" if result else "failed"
    log_line = f"{now} INFO daily_digest: {status} container={container_name}\n"

    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(f"{now} INFO daily_digest: starting run for container={container_name}\n")
            fh.write(log_line)
    except OSError as exc:
        logger.warning("run_daily_digest: could not write log file %s: %s", LOG_FILE, exc)

    if result:
        logger.info("run_daily_digest: completed successfully")
    else:
        logger.error("run_daily_digest: failed")

    return result


def main() -> None:
    container_name = os.environ.get("HUNTER_CONTAINER_NAME", "hunter-v2-1")
    now = datetime.now().isoformat(timespec="seconds")

    logger.info("=== daily_digest.py start — %s ===", now)
    logger.info("Container: %s", container_name)

    success = inject_trigger(container_name)

    if success:
        logger.info("=== daily_digest.py done (OK) ===")
        sys.exit(0)
    else:
        logger.error("=== daily_digest.py done (ERROR) ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
