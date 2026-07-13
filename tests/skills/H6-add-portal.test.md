---
test_id: H6-add-portal
skill: add-portal
description: Portal plugin system — BasePortal ABC, portal registry, JooblePortal, InfostudPortal, /add-portal skill
---

# H6 /add-portal Skill — Expected Behavior

## T1: BasePortal ABC enforces search() abstract method
**Trigger:** `BasePortal()` instantiated directly (no subclass)
**Expected:**
- Instantiating `BasePortal` directly raises `TypeError`
- The error indicates that `search` is an abstract method that has not been implemented
- Subclasses that do NOT implement `search(query: str)` also raise `TypeError` on instantiation
- Subclasses that DO implement `search()` can be instantiated without error

## T2: JooblePortal.search() returns list of dicts with required keys
**Trigger:** `JooblePortal(api_key="test-key").search("Product Manager Belgrade")` called with mocked `requests.post`
**Expected:**
- Returns a non-empty `list` of `dict` objects
- Each dict contains all required keys: `title`, `company`, `url`, `location`, `source`
- The `source` field equals `"Jooble"` for every result
- When `JOOBLE_API_KEY` is unset (empty string or None), `search()` returns `[]` without raising an exception

## T3: InfostudPortal.search() returns [] gracefully when network fails or is blocked
**Trigger:** `InfostudPortal().search("Product Manager")` called when `requests.get` raises an exception
**Expected:**
- Returns `[]` (empty list) — no exception propagated to caller
- Optionally prints a `[InfostudPortal] ...` message to stdout
- When a mock HTML response is provided with valid job listing markup, returns a list of dicts with required keys: `title`, `company`, `url`, `location`, `source`
- The `source` field equals `"Infostud"` for every result

## T4: Portal registry list_portals() returns at minimum ["Jooble", "LinkedIn", "Infostud"] after import
**Trigger:** `from tools.jobs.portals import list_portals` — registry is imported
**Expected:**
- `list_portals()` returns a `list` (or list-like) containing at least `"Jooble"`, `"LinkedIn"`, and `"Infostud"`
- `get_portal("Jooble")` returns an object with a callable `search` method
- `get_portal("LinkedIn")` returns an object with a callable `search` method
- `get_portal("Infostud")` returns an object with a callable `search` method
- `get_portal("NonExistent")` raises `KeyError` or returns `None` gracefully

## T5: LinkedInScraper.search() delegates to fetch() and returns required keys
**Trigger:** `LinkedInScraper().search("Product Manager Belgrade")` called with mocked `requests.get`
**Expected:**
- `search()` internally calls `fetch()` (delegates, not re-implements)
- Returns a non-empty `list` of `dict` objects
- Each dict contains all required keys: `title`, `company`, `url`, `location`, `source`
- The `source` field equals `"LinkedIn"` for every result
- The existing `fetch()` method still works independently after adding `search()`

## T6: /add-portal skill generates a valid portal stub file at tools/jobs/portals/<name>.py
**Trigger:** `/add-portal infostud https://www.infostud.com/oglasi-za-posao/` invoked
**Expected:**
- A new file is created at `tools/jobs/portals/infostud.py` (or the given `<name>.py`)
- The generated file imports `BasePortal` from `tools.jobs.portals.base`
- The generated stub class has `name = "<Name>"` class attribute
- The stub implements `search(query: str) -> list[dict]` that returns `[]` on any error
- The `source` field in returned dicts matches `<Name>` (the capitalized portal name)
- The generated file registers the new portal in `tools/jobs/portals/__init__.py` via `register()`
