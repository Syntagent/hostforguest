"""
Backfill host profile coordinates from address fields.

Usage:
  python scripts/backfill_host_profile_coordinates.py --apply
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

from sqlalchemy import select

from app.db.postgresql.connection import AsyncSessionLocal, close_postgresql, init_postgresql
from app.models.host import HostProfile
from app.services.host_service import _apply_geocode_if_needed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Geocode host profiles missing or stale GPS.")
    parser.add_argument("--apply", action="store_true", help="Persist updates.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run.")
    parser.add_argument("--limit", type=int, default=0, help="Max profiles (div0 = all).")
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    apply_changes = args.apply and not args.dry_run
    await init_postgresql()

    updated = 0
    async with AsyncSessionLocal() as session:
        stmt = select(HostProfile).order_by(HostProfile.updated_at.asc())
        if args.limit > 0:
            stmt = stmt.limit(args.limit)
        result = await session.execute(stmt)
        profiles = list(result.scalars().all())

        for profile in profiles:
            before = (profile.latitude, profile.longitude)
            _apply_geocode_if_needed(profile)
            after = (profile.latitude, profile.longitude)
            if before != after:
                updated += 1
                print(
                    f"[{'UPDATE' if apply_changes else 'DRY'}] {profile.id} "
                    f"{profile.address or ''} {profile.city or ''}: {before} -> {after}"
                )

        if apply_changes and updated:
            await session.commit()

    print(f"Profiles scanned: {len(profiles)}, updated: {updated}, mode: {'APPLY' if apply_changes else 'DRY-RUN'}")
    await close_postgresql()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
