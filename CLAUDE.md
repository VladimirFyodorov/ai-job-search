# Hunter v2

Source of truth for this repo: `AGENTS.md`.

## Quick Start

1. `cp .env.example .env` — fill in tokens
2. `docker compose run --rm hunter python3 tools/notion/setup.py` — create Notion DBs
3. Fill Sofia's CV in Notion (Hunter v2 → CV/Profile)
4. `docker compose up -d` — start

## TDD

Always write tests first: `tests/skills/<feature>.test.md` before implementing.
See `tests/skills/H1-foundation.test.md` for the pattern.
