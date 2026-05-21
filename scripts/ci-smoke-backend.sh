#!/usr/bin/env bash
# Same test list as GitHub Actions backend job (scripts/ci-smoke-backend.txt).
# Starts compose Postgres on localhost:5434 before pytest (PostgreSQL-only fixtures).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

export ENVIRONMENT="${ENVIRONMENT:-development}"
export DISABLE_RATE_LIMIT="${DISABLE_RATE_LIMIT:-1}"
export SKIP_SENTENCE_TRANSFORMERS="${SKIP_SENTENCE_TRANSFORMERS:-1}"
export TOURISTGUIDE_PYTEST="${TOURISTGUIDE_PYTEST:-1}"
export RUN_POSTGRES_TESTS=1
export USE_POSTGRESQL=true
export POSTGRES_SERVER="${POSTGRES_SERVER:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5434}"

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PY}" ]]; then
  echo "No python interpreter found (.venv/bin/python, python3, or python)" >&2
  exit 127
fi

echo "Starting Postgres for CI smoke..."
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

export POSTGRES_PASSWORD="$("${PY}" -c 'from app.core.config import settings; print(settings.postgres_password)')"

LIST="$SCRIPT_DIR/ci-smoke-backend.txt"
paths=()
while IFS= read -r raw || [[ -n "${raw}" ]]; do
  line="$(echo "${raw}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "${line}" ]] && continue
  [[ "${line}" =~ ^# ]] && continue
  paths+=("${line}")
done < "${LIST}"
if [[ ${#paths[@]} -eq 0 ]]; then
  echo "No test paths in ${LIST}" >&2
  exit 1
fi

exec "${PY}" -m pytest "${paths[@]}" -q --tb=short "$@"
