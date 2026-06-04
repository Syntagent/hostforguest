#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

echo "== Event scraper registry =="
"$PY" -m pytest tests/test_event_scraper_registry.py tests/test_event_normalizer_hr_dates.py tests/test_tz_lovran_events_parser.py -q

echo "== CLI fixture parse (no network) =="
"$PY" -m app.scraping.events.cli --slug tz-lovran --html tests/fixtures/events/tz_lovran/listing.html | head -c 500

echo ""
echo "validate_event_scraper.sh OK"
