"""
tools/jobs/dedup.py — Job deduplication utilities.

Provides URL canonicalization (UTM/tracking param stripping) and fuzzy
title+company matching to detect duplicate job listings across sources.
"""

import difflib
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


# Tracking/UTM query parameters to strip during URL canonicalization.
_STRIP_PARAMS = {
    # Google / generic UTM
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    # LinkedIn tracking
    "trk", "trkInfo",
    # HubSpot / Marketo
    "hsa_acc", "hsa_cam", "hsa_grp", "hsa_ad", "hsa_src", "hsa_tgt",
    "hsa_kw", "hsa_mt", "hsa_net", "hsa_ver",
    # Misc referral / click-tracking
    "ref", "referer", "referrer", "fbclid", "gclid", "msclkid",
    "mc_cid", "mc_eid", "yclid", "gbraid", "wbraid",
}


def canonicalize_url(url: str) -> str:
    """Strip UTM/tracking params (utm_*, trk, ref, etc.) using urllib.parse."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in qs.items() if k not in _STRIP_PARAMS}
        # Rebuild in sorted order so canonicalization is deterministic.
        clean_query = urlencode(sorted(filtered.items()), doseq=True)
        canonical = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            "",  # drop fragment
        ))
        return canonical
    except Exception:
        return url


def load_seen(path: str = "logs/seen_jobs.json") -> dict:
    """Load seen jobs dict. Returns {"seen": {}} on missing/invalid file."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict) and "seen" in data:
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {"seen": {}}


def save_seen(seen: dict, path: str = "logs/seen_jobs.json") -> None:
    """Save seen dict to file. Creates logs/ dir if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(seen, indent=2, ensure_ascii=False), encoding="utf-8")


def is_duplicate(job: dict, seen: dict) -> bool:
    """Check if job is duplicate: URL exact match OR fuzzy title+company >= 85%.

    1. Canonical URL check against seen["seen"] keys.
    2. difflib.SequenceMatcher fuzzy check on f"{title} {company}" vs all
       seen entries (stored as "title company" strings in seen["seen"] values).
    """
    seen_map: dict = seen.get("seen", {})

    # 1. Exact canonical URL match.
    canonical = canonicalize_url(job.get("url", ""))
    if canonical in seen_map:
        return True

    # 2. Fuzzy title+company match.
    title = job.get("title", "")
    company = job.get("company", "")
    candidate = f"{title} {company}".lower().strip()

    for entry_data in seen_map.values():
        if not isinstance(entry_data, dict):
            continue
        seen_text = entry_data.get("title_company", "").lower().strip()
        if not seen_text:
            continue
        ratio = difflib.SequenceMatcher(None, candidate, seen_text).ratio()
        if ratio >= 0.85:
            return True

    return False


def mark_seen(job: dict, seen: dict) -> None:
    """Add job's canonical URL to seen["seen"] with today's date string."""
    canonical = canonicalize_url(job.get("url", ""))
    title = job.get("title", "")
    company = job.get("company", "")
    seen.setdefault("seen", {})[canonical] = {
        "date": date.today().isoformat(),
        "title_company": f"{title} {company}",
    }
