"""
Backfill missing attraction coordinates.

Usage:
  python scripts/backfill_attraction_coordinates.py --apply
  python scripts/backfill_attraction_coordinates.py --dry-run --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import select, or_

# Ensure repository root is importable when script is run directly.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.db.postgresql.connection import AsyncSessionLocal, close_postgresql, init_postgresql
from app.models.attraction import Attraction
from app.services.attraction_service import AttractionService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing attraction coordinates.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist updates to database. Without this flag it runs in dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run mode (no writes).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit of processed attractions (0 = no limit).",
    )
    return parser.parse_args()


def _has_missing_coordinates(attraction: Attraction) -> bool:
    return attraction.latitude is None or attraction.longitude is None


def _build_query(limit: int):
    stmt = (
        select(Attraction)
        .where(
            or_(
                Attraction.latitude.is_(None),
                Attraction.longitude.is_(None),
            )
        )
        .order_by(Attraction.updated_at.asc())
    )
    if limit > 0:
        stmt = stmt.limit(limit)
    return stmt


async def _run_backfill(apply_changes: bool, limit: int) -> int:
    await init_postgresql()

    processed = 0
    updated = 0
    skipped = 0
    unresolved = 0
    errors = 0

    async with AsyncSessionLocal() as session:
        service = AttractionService(session)
        stmt = _build_query(limit=limit)
        result = await session.execute(stmt)
        attractions = result.scalars().all()

        print(f"Found {len(attractions)} attractions with missing coordinates.")

        for attraction in attractions:
            processed += 1

            if not _has_missing_coordinates(attraction):
                skipped += 1
                continue

            resolved_latitude, resolved_longitude = service._resolve_coordinates(
                address=attraction.address,
                city=attraction.city,
                latitude=attraction.latitude,
                longitude=attraction.longitude,
            )

            if resolved_latitude is None or resolved_longitude is None:
                unresolved += 1
                print(
                    f"[UNRESOLVED] {attraction.id} | {attraction.name} | "
                    f"city='{attraction.city}' address='{attraction.address}'"
                )
                continue

            # No-op if coordinates are effectively already set
            if (
                attraction.latitude == resolved_latitude
                and attraction.longitude == resolved_longitude
            ):
                skipped += 1
                continue

            print(
                f"[UPDATE] {attraction.id} | {attraction.name} | "
                f"({attraction.latitude}, {attraction.longitude}) -> "
                f"({resolved_latitude}, {resolved_longitude})"
            )

            if apply_changes:
                try:
                    attraction.latitude = resolved_latitude
                    attraction.longitude = resolved_longitude
                    attraction.updated_at = datetime.utcnow()
                    updated += 1
                except Exception as exc:
                    errors += 1
                    print(f"[ERROR] Failed update for {attraction.id}: {exc}")

        if apply_changes:
            try:
                await session.commit()
            except Exception as exc:
                await session.rollback()
                print(f"[ERROR] Commit failed: {exc}")
                raise

    print("\nBackfill summary")
    print(f"- processed:  {processed}")
    print(f"- updated:    {updated}")
    print(f"- skipped:    {skipped}")
    print(f"- unresolved: {unresolved}")
    print(f"- errors:     {errors}")
    print(f"- mode:       {'APPLY' if apply_changes else 'DRY-RUN'}")

    await close_postgresql()
    return 0 if errors == 0 else 1


async def main() -> int:
    args = _parse_args()
    apply_changes = args.apply and not args.dry_run
    return await _run_backfill(apply_changes=apply_changes, limit=args.limit)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
