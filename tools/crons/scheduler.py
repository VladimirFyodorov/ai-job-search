"""APScheduler-based cron scheduler for hunter-v2.

Schedules the daily digest job at 09:00 Belgrade time using BackgroundScheduler.

Usage:
    python tools/crons/scheduler.py
"""

from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tools.crons.daily_digest import run_daily_digest

logger = logging.getLogger(__name__)


def create_scheduler(job_fn=None):
    """Create and configure the APScheduler with the daily digest job.

    Args:
        job_fn: Callable to schedule. Defaults to run_daily_digest.

    Returns:
        Configured BackgroundScheduler instance (not yet started).
    """
    if job_fn is None:
        job_fn = run_daily_digest

    scheduler = BackgroundScheduler()
    trigger = CronTrigger(hour=9, minute=0, timezone='Europe/Belgrade')
    scheduler.add_job(job_fn, trigger)
    return scheduler


def main() -> None:
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("scheduler: started, waiting for jobs...")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
