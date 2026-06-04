#!/usr/bin/env python3
"""Remove guest groups without stay dates or overlapping with another group."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("HOSTFORGUEST_API_URL", os.getenv("API_BASE_URL", "https://hostforguest.syntagent.com")).rstrip("/")
if not BASE.endswith("/api"):
    BASE = f"{BASE}/api" if "/api" not in BASE else BASE
EMAIL = os.getenv("BEN_TEST_EMAIL", os.getenv("VERIFY_HOST_EMAIL", "benediktperak@gmail.com"))
PASSWORD = os.getenv("BEN_TEST_PASSWORD", os.getenv("VERIFY_HOST_PASSWORD", ""))
DRY_RUN = os.getenv("CLEANUP_DRY_RUN", "0").strip() in ("1", "true", "yes")


@dataclass
class GroupRow:
    id: str
    group_name: str
    created_at: str
    check_in: date | None
    check_out: date | None
    pref_count: int
    raw: dict[str, Any]


def parse_day(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.date()
    except ValueError:
        return None


def ranges_overlap(a: GroupRow, b: GroupRow) -> bool:
    if not all([a.check_in, a.check_out, b.check_in, b.check_out]):
        return False
    return a.check_in < b.check_out and b.check_in < a.check_out


def score_keep(g: GroupRow) -> tuple:
    """Higher = prefer to keep when resolving overlap."""
    return (
        1 if g.check_in and g.check_out else 0,
        g.pref_count,
        g.created_at,
    )


def pick_deletions(groups: list[GroupRow]) -> tuple[list[GroupRow], list[str]]:
    to_delete: list[GroupRow] = []
    reasons: list[str] = []

    undated = [g for g in groups if not g.check_in or not g.check_out]
    for g in undated:
        to_delete.append(g)
        reasons.append(f"{g.group_name} ({g.id[:8]}…): no stay dates")

    dated = [g for g in groups if g.check_in and g.check_out and g not in to_delete]
    dated_sorted = sorted(dated, key=score_keep, reverse=True)
    kept: list[GroupRow] = []

    for g in dated_sorted:
        collides = [k for k in kept if ranges_overlap(g, k)]
        if collides:
            to_delete.append(g)
            names = ", ".join(k.group_name for k in collides)
            reasons.append(
                f"{g.group_name} ({g.id[:8]}…): overlaps {names} "
                f"({g.check_in}–{g.check_out})"
            )
        else:
            kept.append(g)

    # dedupe
    seen: set[str] = set()
    unique_delete: list[GroupRow] = []
    for g in to_delete:
        if g.id not in seen:
            seen.add(g.id)
            unique_delete.append(g)
    return unique_delete, reasons


def main() -> int:
    if not PASSWORD:
        print("Set BEN_TEST_PASSWORD or VERIFY_HOST_PASSWORD in .env", file=sys.stderr)
        return 1

    with httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True) as c:
        login = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
        if login.status_code != 200:
            print(f"Login failed ({login.status_code}): {login.text[:200]}", file=sys.stderr)
            return 1
        token = login.json().get("session_token")
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}

        listed = c.get("/v1/guest-groups/host", headers=headers)
        if listed.status_code != 200:
            print(f"List failed ({listed.status_code}): {listed.text[:200]}", file=sys.stderr)
            return 1

        groups_raw = listed.json()
        rows: list[GroupRow] = []
        for g in groups_raw:
            prefs = g.get("preferences") or []
            rows.append(
                GroupRow(
                    id=str(g["id"]),
                    group_name=str(g.get("group_name") or "Unnamed"),
                    created_at=str(g.get("created_at") or ""),
                    check_in=parse_day(g.get("check_in_date")),
                    check_out=parse_day(g.get("check_out_date")),
                    pref_count=len(prefs) if isinstance(prefs, list) else 0,
                    raw=g,
                )
            )

        print(f"Host: {EMAIL}")
        print(f"Total groups: {len(rows)}")
        for r in rows:
            span = (
                f"{r.check_in} → {r.check_out}"
                if r.check_in and r.check_out
                else "NO DATES"
            )
            print(f"  - {r.group_name}: {span} (prefs={r.pref_count})")

        to_delete, reasons = pick_deletions(rows)
        if not to_delete:
            print("\nNothing to delete.")
            return 0

        print(f"\nWill delete {len(to_delete)} group(s):" + (" [DRY RUN]" if DRY_RUN else ""))
        for reason in reasons:
            print(f"  • {reason}")

        if DRY_RUN:
            return 0

        ok = 0
        for g in to_delete:
            r = c.delete(f"/v1/guest-groups/{g.id}", headers=headers)
            if r.status_code in (200, 204):
                print(f"  deleted {g.group_name}")
                ok += 1
            else:
                print(f"  FAIL {g.group_name}: {r.status_code} {r.text[:120]}", file=sys.stderr)

        listed2 = c.get("/v1/guest-groups/host", headers=headers)
        remaining = len(listed2.json()) if listed2.status_code == 200 else "?"
        print(f"\nDeleted {ok}/{len(to_delete)}. Remaining groups: {remaining}")
        return 0 if ok == len(to_delete) else 1


if __name__ == "__main__":
    sys.exit(main())
