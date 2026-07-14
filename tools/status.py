"""
tools/status.py — Collect stats for /status command.

Exports a single function: get_status(context_pct=None) -> str
"""

import os
import subprocess
from datetime import datetime, timezone, timedelta

# Belgrade timezone: Europe/Belgrade (UTC+2 summer / UTC+1 winter)
try:
    from zoneinfo import ZoneInfo
    _BELGRADE_TZ = ZoneInfo("Europe/Belgrade")
except Exception:
    _BELGRADE_TZ = None

# Fallback: UTC+2 offset (summer)
_BELGRADE_OFFSET = timedelta(hours=2)


def _now_belgrade() -> datetime:
    """Return current datetime in Belgrade timezone."""
    if _BELGRADE_TZ is not None:
        return datetime.now(_BELGRADE_TZ)
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2)))


def _next_digest_str() -> str:
    """
    Return formatted string like "09:00 (через 3ч 45м)".
    Next daily digest is at 09:00 Belgrade time.
    """
    now = _now_belgrade()
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= target:
        # Already past 09:00 today — next digest is tomorrow
        target = target + timedelta(days=1)
    delta = target - now
    total_minutes = int(delta.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        time_str = f"{hours}ч {minutes}м"
    else:
        time_str = f"{minutes}м"
    return f"09:00 (через {time_str})"


def _check_latex() -> bool:
    """Return True if lualatex or latex is available."""
    for cmd in ("lualatex", "latex"):
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _format_time_ago(dt_str: str) -> str:
    """
    Format an ISO datetime string as a human-readable "X ч назад" / "вчера" / "N дней назад".
    dt_str: ISO 8601 string (e.g. "2024-01-15T10:30:00.000Z")
    Returns fallback "—" on parse error.
    """
    if not dt_str:
        return "—"
    try:
        # Parse ISO string
        dt_str_clean = dt_str.rstrip("Z")
        if "+" in dt_str_clean:
            dt_str_clean = dt_str_clean.split("+")[0]
        dt = datetime.fromisoformat(dt_str_clean).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        total_hours = int(delta.total_seconds() // 3600)
        total_days = delta.days
        if total_hours < 1:
            return "только что"
        if total_hours < 24:
            return f"{total_hours} ч назад"
        if total_days == 1:
            return "вчера"
        return f"{total_days} дней назад"
    except Exception:
        return "—"


def _get_config_value(config_results: list, key: str, default=None):
    """Extract a value from Config DB query results (key-value store)."""
    for page in config_results:
        props = page.get("properties", {})
        # Config DB stores key in "Name" (title) property and value in "Value" (rich_text)
        name_prop = props.get("Name", {})
        name_val = ""
        if name_prop.get("type") == "title":
            title_list = name_prop.get("title", [])
            if title_list:
                name_val = title_list[0].get("plain_text", "")
        elif name_prop.get("type") == "rich_text":
            rt_list = name_prop.get("rich_text", [])
            if rt_list:
                name_val = rt_list[0].get("plain_text", "")

        if name_val == key:
            value_prop = props.get("Value", {})
            if value_prop.get("type") == "rich_text":
                rt = value_prop.get("rich_text", [])
                if rt:
                    return rt[0].get("plain_text", default)
            elif value_prop.get("type") == "number":
                return value_prop.get("number", default)
    return default


def get_status(context_pct=None) -> str:
    """
    Collect stats from Notion and return a formatted status string.

    Args:
        context_pct: int 0-100 or None. If None, reads CLAUDE_CONTEXT_PCT env var.

    Returns:
        Formatted multi-line status string.
    """
    # 1. context_pct
    if context_pct is None:
        env_val = os.environ.get("CLAUDE_CONTEXT_PCT", "")
        context_pct = int(env_val) if env_val.isdigit() else "?"

    # 2. Next digest time
    digest_str = _next_digest_str()

    # 3. Check LaTeX
    latex_ok = _check_latex()
    latex_icon = "✅" if latex_ok else "❌"

    # 4. Notion DB IDs from env
    jobs_db_id = os.environ.get("NOTION_JOBS_DB_ID", "")
    apps_db_id = os.environ.get("NOTION_APPLICATIONS_DB_ID", "")
    config_db_id = os.environ.get("NOTION_CONFIG_DB_ID", "")

    # Import Notion client (lazy, so failures are caught gracefully)
    try:
        from tools.notion import client as notion
    except ImportError:
        try:
            import sys
            import os as _os
            _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            if _root not in sys.path:
                sys.path.insert(0, _root)
            from tools.notion import client as notion
        except ImportError:
            notion = None

    # Default values (shown on Notion failure)
    notion_ok = False
    jobs_total = "?"
    jobs_today = "?"
    jobs_matching = "?"
    apps_total = "?"
    apps_waiting = "?"
    apps_interview = "?"
    last_search = "?"
    last_apply = "?"
    min_score = 60  # default

    if notion and jobs_db_id and apps_db_id and config_db_id:
        try:
            # Ping Notion via Config DB
            config_results = notion.query_db(config_db_id, page_size=100)
            notion_ok = True

            # Get min_score from config
            min_score_val = _get_config_value(config_results, "min_score", None)
            if min_score_val is not None:
                try:
                    min_score = int(float(str(min_score_val)))
                except (ValueError, TypeError):
                    pass

        except Exception:
            notion_ok = False

    notion_icon = "✅" if notion_ok else "❌"

    if notion_ok and notion:
        # ── Jobs DB queries ──
        try:
            # Today's date in Belgrade
            now_bel = _now_belgrade()
            today_str = now_bel.strftime("%Y-%m-%d")

            # Total jobs count
            all_jobs = notion.query_db(jobs_db_id, page_size=1000)
            jobs_total = len(all_jobs)

            # Jobs added today: filter by Date Added property
            today_filter = {
                "property": "Date Added",
                "date": {"equals": today_str},
            }
            jobs_today_results = notion.query_db(
                jobs_db_id, filter=today_filter, page_size=1000
            )
            jobs_today = len(jobs_today_results)

            # Jobs with Score >= min_score
            score_filter = {
                "property": "Score",
                "number": {"greater_than_or_equal_to": min_score},
            }
            jobs_matching_results = notion.query_db(
                jobs_db_id, filter=score_filter, page_size=1000
            )
            jobs_matching = len(jobs_matching_results)

            # Last search: newest job by Date Added
            if all_jobs:
                # Sort by Date Added desc — use created_time as fallback
                newest_job = None
                newest_date = None
                for job in all_jobs:
                    props = job.get("properties", {})
                    date_prop = props.get("Date Added", {})
                    date_val = None
                    if date_prop.get("type") == "date":
                        date_info = date_prop.get("date") or {}
                        date_val = date_info.get("start")
                    if date_val is None:
                        date_val = job.get("created_time", "")
                    if newest_date is None or date_val > newest_date:
                        newest_date = date_val
                        newest_job = job
                if newest_date:
                    last_search = _format_time_ago(newest_date)

        except Exception:
            pass

        # ── Applications DB queries ──
        try:
            all_apps = notion.query_db(apps_db_id, page_size=1000)
            apps_total = len(all_apps)

            apps_waiting_count = 0
            apps_interview_count = 0
            newest_app_date = None

            for app in all_apps:
                props = app.get("properties", {})
                status_prop = props.get("Status", {})
                status_val = ""
                if status_prop.get("type") == "select":
                    sel = status_prop.get("select") or {}
                    status_val = sel.get("name", "")
                elif status_prop.get("type") == "status":
                    sel = status_prop.get("status") or {}
                    status_val = sel.get("name", "")

                if status_val in ("Sent", "Acknowledged"):
                    apps_waiting_count += 1
                elif status_val == "Interview":
                    apps_interview_count += 1

                created = app.get("created_time", "")
                if created:
                    if newest_app_date is None or created > newest_app_date:
                        newest_app_date = created

            apps_waiting = apps_waiting_count
            apps_interview = apps_interview_count

            if newest_app_date:
                last_apply = _format_time_ago(newest_app_date)

        except Exception:
            pass

    # ── Build formatted output ──
    lines = [
        f"🤖 Hunter v2 · контекст {context_pct}%",
        "",
        f"📅 Дайджест: следующий в {digest_str}",
        "",
        "📊 Вакансии:",
        f"  Всего: {jobs_total} | Новых сегодня: {jobs_today} | Подходящих: {jobs_matching}",
        "",
        "📬 Заявки (из Notion Applications DB):",
        f"  Всего: {apps_total} | Ожидают ответа: {apps_waiting} | Интервью: {apps_interview}",
        "",
        "🕒 Последняя активность:",
        f"  Поиск: {last_search} | Заявка: {last_apply}",
        "",
        "🔧 Сервисы:",
        f"  Telegram: ✅ | Notion: {notion_icon} | LaTeX: {latex_icon}",
    ]
    return "\n".join(lines)
