#!/usr/bin/env bash
# Same test list as GitHub Actions backend job (scripts/ci-smoke-backend.txt).
# Bash 3.2+ (macOS): no mapfile.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
export DISABLE_RATE_LIMIT="${DISABLE_RATE_LIMIT:-1}"
export SKIP_SENTENCE_TRANSFORMERS="${SKIP_SENTENCE_TRANSFORMERS:-1}"
export TOURISTGUIDE_PYTEST="${TOURISTGUIDE_PYTEST:-1}"
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
exec python -m pytest "${paths[@]}" -q --tb=short "$@"
