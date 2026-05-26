#!/usr/bin/env bash
# Local/CI harness: Postgres + API (:8000) + Next (:3055) + Playwright guest events smoke.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

API_PORT="${E2E_API_PORT:-8000}"
UI_PORT="${E2E_UI_PORT:-3055}"
API_URL="http://127.0.0.1:${API_PORT}"
UI_URL="http://127.0.0.1:${UI_PORT}"

export ENVIRONMENT="${ENVIRONMENT:-development}"
export DEBUG="${DEBUG:-true}"
export DISABLE_RATE_LIMIT="${DISABLE_RATE_LIMIT:-1}"
export SKIP_SENTENCE_TRANSFORMERS="${SKIP_SENTENCE_TRANSFORMERS:-1}"
export USE_POSTGRESQL=true
export POSTGRES_SERVER="${POSTGRES_SERVER:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5434}"
export POSTGRES_USER="${POSTGRES_USER:-tourist_guide_user}"
export POSTGRES_DB="${POSTGRES_DB:-tourist_guide_db}"
# Always enable dev seed for this harness (ignore .env false — seed script + Playwright need dev@).
export DEV_LOGIN_SEED_ENABLED=true
export DEV_LOGIN_SEED_FORCE=true
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-${API_URL}}"

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PY}" ]]; then
  echo "No python interpreter found (.venv/bin/python, python3, or python)" >&2
  exit 127
fi

API_PID=""
UI_PID=""

cleanup() {
  if [[ -n "${UI_PID}" ]] && kill -0 "${UI_PID}" 2>/dev/null; then
    kill "${UI_PID}" 2>/dev/null || true
    wait "${UI_PID}" 2>/dev/null || true
  fi
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

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

export POSTGRES_PASSWORD="$("${PY}" -c 'from app.core.config import settings; print(settings.postgres_password)')"

echo "Starting API on ${API_URL}..."
"${PY}" -m uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}" >/tmp/hostforguest-e2e-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 90); do
  if curl -sf "${API_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! curl -sf "${API_URL}/health" >/dev/null 2>&1; then
  echo "API did not become ready. Log:" >&2
  tail -40 /tmp/hostforguest-e2e-api.log >&2 || true
  exit 1
fi

echo "Seeding E2E guest group..."
SEED_OUT="$("${PY}" "${SCRIPT_DIR}/seed_e2e_guest.py")"
E2E_GUEST_ACCESS_CODE="$(echo "${SEED_OUT}" | awk -F= '/^E2E_GUEST_ACCESS_CODE=/ {print $2; exit}')"
E2E_GUEST_GROUP_NAME="$(echo "${SEED_OUT}" | sed -n "s/^E2E_GUEST_GROUP_NAME='\(.*\)'$/\1/p")"
export E2E_GUEST_ACCESS_CODE
export E2E_GUEST_GROUP_NAME
export PLAYWRIGHT_API_URL="${API_URL}"
export PLAYWRIGHT_BASE_URL="${UI_URL}"

echo "Building frontend (NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL})..."
npm ci --prefix frontend
npm run build --prefix frontend

echo "Starting Next on ${UI_URL}..."
npm run start --prefix frontend -- -p "${UI_PORT}" -H 127.0.0.1 >/tmp/hostforguest-e2e-ui.log 2>&1 &
UI_PID=$!

for _ in $(seq 1 60); do
  if curl -sf "${UI_URL}/" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! curl -sf "${UI_URL}/" >/dev/null 2>&1; then
  echo "Frontend did not become ready. Log:" >&2
  tail -40 /tmp/hostforguest-e2e-ui.log >&2 || true
  exit 1
fi

echo "Running Playwright (access code ${E2E_GUEST_ACCESS_CODE})..."
npx playwright install chromium
npx playwright test --config tests/e2e/playwright.ci.config.ts

echo "E2E smoke passed (guest events + host dashboard, including create group)."
