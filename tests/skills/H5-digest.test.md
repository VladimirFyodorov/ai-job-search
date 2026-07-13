---
test_id: H5-digest
skill: digest
description: Daily digest cron — APScheduler, PTY injection, file logging
---

# H5 Daily Digest Cron — Expected Behavior

## T1: APScheduler CronTrigger configured with correct schedule
**Trigger:** `create_scheduler()` called (or scheduler module initialized)
**Expected:**
- `CronTrigger` is instantiated with `hour=9`, `minute=0`, `timezone='Europe/Belgrade'`
- The trigger is added to the APScheduler `BackgroundScheduler` (or `BlockingScheduler`)
- The scheduler is configured before `scheduler.start()` is called

## T2: inject_trigger returns True on successful docker exec
**Trigger:** `inject_trigger(container_name)` called with a valid container name
**Expected:**
- Calls `subprocess.run` with command: `docker exec -i <container_name> sh -c 'echo "DAILY_DIGEST: run daily job search digest" > /proc/1/fd/0'`
- When subprocess returns `returncode=0`, the function returns `True`
- No exception is raised

## T3: inject_trigger returns False and logs error on non-zero exit code
**Trigger:** `inject_trigger(container_name)` called and `subprocess.run` returns `returncode=1`
**Expected:**
- Returns `False`
- Logs an error message containing the exit code (via `logger.error`)
- Does not raise an exception

## T4: inject_trigger returns False and logs error on TimeoutExpired
**Trigger:** `inject_trigger(container_name)` called and `subprocess.run` raises `subprocess.TimeoutExpired`
**Expected:**
- Returns `False`
- Logs an error message mentioning the timeout (via `logger.error`)
- Does not propagate the exception

## T5: scheduler logs run start and result to logs/daily-digest.log
**Trigger:** Scheduled job fires (or `run_daily_digest()` called directly)
**Expected:**
- A log entry is written to `logs/daily-digest.log` indicating the run started
- After `inject_trigger` returns, a second log entry records the result (success or failure)
- Log entries include a timestamp
