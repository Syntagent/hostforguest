#!/usr/bin/env bash
# Apply SQL files listed in migrations/MIGRATION_ORDER.txt to PostgreSQL.
#
# Usage:
#   bash scripts/apply-migrations.sh
#   bash scripts/apply-migrations.sh --dry-run
#   bash scripts/apply-migrations.sh --host 127.0.0.1 --port 5439
#
# Password: set POSTGRES_PASSWORD (or PGPASSWORD) in the environment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PG_HOST="${PGHOST:-localhost}"
PG_PORT="${PGPORT:-5434}"
PG_DATABASE="${PGDATABASE:-tourist_guide_db}"
PG_USER="${PGUSER:-tourist_guide_user}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: apply-migrations.sh [options]

Options:
  --host HOST       Postgres host (default: localhost, or PGHOST)
  --port PORT       Postgres port (default: 5434, or PGPORT)
  --database NAME   Database name (default: tourist_guide_db, or PGDATABASE)
  --user USER       Postgres user (default: tourist_guide_user, or PGUSER)
  --dry-run         List migration files only; do not run psql
  -h, --help        Show this help

Environment:
  POSTGRES_PASSWORD or PGPASSWORD — required unless peer auth works
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      PG_HOST="${2:?--host requires a value}"
      shift 2
      ;;
    --port)
      PG_PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --database)
      PG_DATABASE="${2:?--database requires a value}"
      shift 2
      ;;
    --user)
      PG_USER="${2:?--user requires a value}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ORDER_FILE="${REPO_ROOT}/migrations/MIGRATION_ORDER.txt"
MIGRATIONS_DIR="${REPO_ROOT}/migrations"

if [[ ! -f "${ORDER_FILE}" ]]; then
  echo "Missing ${ORDER_FILE}" >&2
  exit 1
fi

mapfile -t MIGRATION_FILES < <(
  grep -v '^[[:space:]]*#' "${ORDER_FILE}" | grep -v '^[[:space:]]*$' || true
)

if [[ ${#MIGRATION_FILES[@]} -eq 0 ]]; then
  echo "No migrations listed in ${ORDER_FILE}" >&2
  exit 1
fi

echo "Applying ${#MIGRATION_FILES[@]} migration(s) to ${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}"

if [[ "${DRY_RUN}" -eq 0 ]]; then
  if [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
    export PGPASSWORD="${POSTGRES_PASSWORD}"
  elif [[ -z "${PGPASSWORD:-}" ]]; then
    echo "Warning: POSTGRES_PASSWORD and PGPASSWORD are unset; psql may prompt or fail." >&2
  fi
fi

for rel in "${MIGRATION_FILES[@]}"; do
  rel="$(echo "${rel}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  path="${MIGRATIONS_DIR}/${rel}"
  if [[ ! -f "${path}" ]]; then
    echo "Migration file not found: ${path}" >&2
    exit 1
  fi
  echo "---- ${rel} ----"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    continue
  fi
  if ! command -v psql >/dev/null 2>&1; then
    echo "psql not found on PATH; install PostgreSQL client tools." >&2
    exit 127
  fi
  psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" \
    -v ON_ERROR_STOP=1 -f "${path}"
done

echo "Done."
