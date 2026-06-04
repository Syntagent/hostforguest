"""
Backfill missing local_events coordinates from city centroids.

Usage:
  python scripts/backfill_local_event_coordinates.py --apply
  python scripts/backfill_local_event_coordinates.py --dry-run --limit 100
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
    parser = argparse.ArgumentParser(description="Backfill local_events lat/lng from city centroids.")
    parser.add_argument("--apply", action="store_true", help="Persist updates (default: dry-run).")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode.")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all).")
    parser.add_argument(
        "--geocode-venues",
        action="store_true",
        help="Geocode venue_name/title via Nominatim (slower, more accurate).",
    )
    parser.add_argument(
        "--geocode-limit",
        type=int,
        default=25,
        help="Max venue geocode lookups per run when --geocode-venues is set.",
    )
    parser.add_argument(
        "--no-refresh-stale",
        action="store_true",
        help="Skip rows that already have coordinates (even if outdated).",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    apply_changes = args.apply and not args.dry_run
    await init_postgresql()

    async with AsyncSessionLocal() as session:
        feed = EventsFeedService(session)
        summary = await feed.backfill_missing_coordinates(
            limit=args.limit if args.limit > 0 else 5000,
            dry_run=not apply_changes,
            refresh_stale=not args.no_refresh_stale,
            geocode_venues=args.geocode_venues,
            geocode_venue_limit=args.geocode_limit,
        )

    print("Local events coordinate backfill")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"- mode: {'APPLY' if apply_changes else 'DRY-RUN'}")

    await close_postgresql()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
