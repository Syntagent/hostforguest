#!/usr/bin/env bash
# Full pytest pass against compose Postgres (localhost:5434).
# Requires: docker compose, .env with POSTGRES_PASSWORD (and optional overrides).
#
# Usage:
#   bash scripts/run-postgres-regression.sh          # reuse existing volume
#   bash scripts/run-postgres-regression.sh --fresh  # docker compose down -v postgres first

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FRESH=0
if [[ "${1:-}" == "--fresh" ]]; then
  FRESH=1
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

if [[ $FRESH -eq 1 ]]; then
  echo "Recreating Postgres volume..."
  docker compose stop postgres 2>/dev/null || true
  docker compose rm -f postgres 2>/dev/null || true
  docker volume rm hostforguest_postgres_data 2>/dev/null || true
fi

echo "Starting Postgres..."
docker compose up -d postgres

echo "Waiting for Postgres health..."
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U tourist_guide_user -d tourist_guide_db >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker compose exec -T postgres pg_isready -U tourist_guide_user -d tourist_guide_db >/dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

# Load POSTGRES_PASSWORD from .env via app settings (do not echo secrets).
export POSTGRES_PASSWORD="$("$PYTHON" -c 'from app.core.config import settings; print(settings.postgres_password)')"
export ENVIRONMENT=development
export DISABLE_RATE_LIMIT=1
export SKIP_SENTENCE_TRANSFORMERS=1
export RUN_POSTGRES_TESTS=1
export RUN_INTEGRATION_DB=1
export USE_POSTGRESQL=true
export POSTGRES_SERVER=localhost
export POSTGRES_PORT=5434
export POSTGRES_USER=tourist_guide_user
export POSTGRES_DB=tourist_guide_db
export TOURISTGUIDE_PYTEST=1

echo "Bootstrapping schema on Postgres..."
"$PYTHON" -c "
import asyncio
from app.db.postgresql.connection import init_postgresql, USE_POSTGRESQL
async def main():
    await init_postgresql()
    if not USE_POSTGRESQL:
        raise SystemExit('Expected PostgreSQL but init did not connect')
asyncio.run(main())
"

echo "Running full pytest suite against Postgres (excluding Playwright e2e)..."
"$PYTHON" -m pytest tests/ --ignore=tests/e2e -q --tb=line

echo "Postgres regression pass finished OK."
