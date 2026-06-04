"""
Backfill local_events start_at/end_at from title and description copy.

Usage:
  python scripts/backfill_local_event_dates.py --dry-run --limit 50
  python scripts/backfill_local_event_dates.py --apply
  python scripts/backfill_local_event_dates.py --apply --city Lovran --refresh-times
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
from app.services.events_feed_service import EventsFeedService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill local_events start_at/end_at from Croatian date text in copy."
    )
    parser.add_argument("--apply", action="store_true", help="Persist updates (default: dry-run).")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode.")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to scan (0 = 5000).")
    parser.add_argument("--city", type=str, default=None, help="Optional city/region/title filter.")
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Re-parse rows that already have dates (not only missing start_at).",
    )
    parser.add_argument(
        "--refresh-times",
        action="store_true",
        help="Fill start/end times when copy includes HH:MM but DB has date-only noon.",
    )
    parser.add_argument(
        "--include-expired",
        action="store_true",
        help="Process non-active rows too (default: active only).",
    )
    parser.add_argument(
        "--no-expire-past",
        action="store_true",
        help="Do not mark inferred past events as expired.",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    apply_changes = args.apply and not args.dry_run
    await init_postgresql()

    async with AsyncSessionLocal() as session:
        feed = EventsFeedService(session)
        summary = await feed.backfill_missing_event_dates(
            limit=args.limit if args.limit > 0 else 5000,
            dry_run=not apply_changes,
            only_missing=not args.refresh_all,
            refresh_times=args.refresh_times,
            expire_past=not args.no_expire_past,
            city=args.city,
            active_only=not args.include_expired,
        )

    print("Local events date backfill")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"- mode: {'APPLY' if apply_changes else 'DRY-RUN'}")

    await close_postgresql()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
