#!/usr/bin/env python3
"""Delete guest groups without stay dates or overlapping another group (per host)."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

# Run inside API container: /app is cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select

from app.db.postgresql.connection import get_async_session
from app.models.guest_group import AccessCode, GuestEVisitorData, GuestGroup, GuestPreference
from app.services.guest_group_service import GuestGroupService


@dataclass
class GroupRow:
    id: UUID
    host_id: UUID
    group_name: str
    created_at: datetime
    check_in: date | None
    check_out: date | None
    pref_count: int


def parse_day(dt: datetime | None) -> date | None:
    if not dt:
        return None
    return dt.date() if hasattr(dt, "date") else None


def ranges_overlap(a: GroupRow, b: GroupRow) -> bool:
    if not all([a.check_in, a.check_out, b.check_in, b.check_out]):
        return False
    return a.check_in < b.check_out and b.check_in < a.check_out


def score_keep(g: GroupRow) -> tuple:
    return (1 if g.check_in and g.check_out else 0, g.pref_count, g.created_at.isoformat())


def pick_deletions(groups: list[GroupRow]) -> list[GroupRow]:
    to_delete: list[GroupRow] = []
    undated = [g for g in groups if not g.check_in or not g.check_out]
    to_delete.extend(undated)

    dated = [g for g in groups if g.check_in and g.check_out and g not in to_delete]
    dated_sorted = sorted(dated, key=score_keep, reverse=True)
    kept: list[GroupRow] = []
    for g in dated_sorted:
        if any(ranges_overlap(g, k) for k in kept):
            to_delete.append(g)
        else:
            kept.append(g)

    seen: set[UUID] = set()
    unique: list[GroupRow] = []
    for g in to_delete:
        if g.id not in seen:
            seen.add(g.id)
            unique.append(g)
    return unique


async def run(host_filter: str | None = None) -> int:
    dry = os.getenv("CLEANUP_DRY_RUN", "0").strip() in ("1", "true", "yes")
    deleted = 0

    async for db in get_async_session():
        svc = GuestGroupService(db)
        result = await db.execute(select(GuestGroup).order_by(GuestGroup.host_id, GuestGroup.created_at))
        all_groups = result.scalars().all()

        by_host: dict[UUID, list[GroupRow]] = {}
        for g in all_groups:
            if host_filter and str(g.host_id) != host_filter:
                continue
            prefs = await db.execute(
                select(GuestPreference).where(GuestPreference.guest_group_id == g.id)
            )
            pref_count = len(prefs.scalars().all())
            row = GroupRow(
                id=g.id,
                host_id=g.host_id,
                group_name=g.group_name or "",
                created_at=g.created_at,
                check_in=parse_day(g.check_in_date),
                check_out=parse_day(g.check_out_date),
                pref_count=pref_count,
            )
            by_host.setdefault(g.host_id, []).append(row)

        for host_id, rows in by_host.items():
            to_delete = pick_deletions(rows)
            if not to_delete:
                continue
            print(f"\nHost {host_id}: delete {len(to_delete)} / {len(rows)} groups")
            for g in to_delete:
                span = (
                    f"{g.check_in} → {g.check_out}"
                    if g.check_in and g.check_out
                    else "NO DATES"
                )
                print(f"  {'[dry]' if dry else '[-]'} {g.group_name} ({span})")
                if not dry:
                    ok = await svc.delete_guest_group(g.id)
                    if ok:
                        deleted += 1
                    else:
                        # cascade children then retry
                        gid = g.id
                        for model in (GuestPreference, GuestEVisitorData, AccessCode):
                            await db.execute(delete(model).where(model.guest_group_id == gid))
                        await db.execute(delete(GuestGroup).where(GuestGroup.id == gid))
                        await db.commit()
                        deleted += 1
                        print(f"      (forced cascade delete)")

        break

    print(f"\n{'Would delete' if dry else 'Deleted'}: {deleted if not dry else sum(len(pick_deletions(v)) for v in by_host.values())}")
    return 0


if __name__ == "__main__":
    host = os.getenv("CLEANUP_HOST_ID")
    raise SystemExit(asyncio.run(run(host)))
