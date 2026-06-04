"""
LLM re-extraction of event dates from detail pages (undated local_events).

Usage:
  python scripts/enrich_local_event_dates_llm.py --dry-run --limit 10
  python scripts/enrich_local_event_dates_llm.py --apply --limit 40
  python scripts/enrich_local_event_dates_llm.py --apply --city Rijeka
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.db.postgresql.connection import AsyncSessionLocal, close_postgresql, init_postgresql
from app.services.event_llm_date_enrichment import EventLlmDateEnrichmentService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM detail-page enrichment for undated local_events."
    )
    parser.add_argument("--apply", action="store_true", help="Persist updates (default: dry-run).")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode.")
    parser.add_argument("--limit", type=int, default=30, help="Max undated rows to process.")
    parser.add_argument("--city", type=str, default=None, help="Optional city/region/title filter.")
    parser.add_argument(
        "--include-expired",
        action="store_true",
        help="Process non-active rows too (default: active only).",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    apply_changes = args.apply and not args.dry_run
    await init_postgresql()

    async with AsyncSessionLocal() as session:
        service = EventLlmDateEnrichmentService(session)
        try:
            summary = await service.enrich_undated_events(
                limit=args.limit,
                dry_run=not apply_changes,
                city=args.city,
                active_only=not args.include_expired,
            )
        finally:
            await service.close()

    print("LLM local event date enrichment")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"- mode: {'APPLY' if apply_changes else 'DRY-RUN'}")

    await close_postgresql()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
