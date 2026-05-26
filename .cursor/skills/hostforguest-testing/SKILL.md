---
name: hostforguest-testing
description: Run and fix tests for HostForGuest -- pytest, CI smoke, PostgreSQL regression suite. Use when running tests, debugging failures, or adding tests.
---

# HostForGuest -- Testing Guide

## Quick Commands

Backend tests (full suite):
  cd /home/bperak/development/hostforguest
  .venv/bin/pytest -q

CI smoke (same as GitHub Actions):
  npm run test:ci-smoke

PostgreSQL regression (429 tests):
  bash scripts/run-postgres-regression.sh

## Test Configuration

- `PYTEST_CURRENT_TEST` is set automatically, which skips in-app rate limiting.
- `DISABLE_RATE_LIMIT=1` can also be set manually.
- CI smoke sets `TOURISTGUIDE_PYTEST=1` and uses Compose Postgres on `localhost:5434`.
- Test fixtures in `tests/conftest.py` handle database connections.

## CI Smoke Details

Paths live in `scripts/ci-smoke-backend.txt` -- edit that file to widen or narrow coverage.

## Common Failures

- **Connection refused:** PostgreSQL not running on port 5434.
- **Rate limiting blocks tests:** Set `DISABLE_RATE_LIMIT=1` or run via pytest (auto-handled).
- **pgvector missing:** Run CREATE EXTENSION command in deployment skill.

## Adding Tests

1. Add test file to `tests/` directory.
2. Use existing fixtures from `conftest.py`.
3. Run `pytest -xvs tests/your_test.py` for debug output.
4. Full suite must pass before committing.
