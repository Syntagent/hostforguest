#!/usr/bin/env python3
"""
Ben scenario: guest-facing events APIs (realtime feed + seasonal) for access code group.

Usage:
  python tests/ben_guest_events_check.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
CODE = os.getenv("BEN_GUEST_ACCESS_CODE", "72HQ5TJL")
CITY = os.getenv("BEN_EVENTS_CITY", "Lovran")


@dataclass
class Row:
    area: str
    action: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        codes = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in codes if codes else False


rows: list[Row] = []


def record(area: str, action: str, http: int, expected: str, notes: str = "") -> None:
    rows.append(Row(area, action, http, expected, notes[:180]))


def print_report() -> None:
    passed = sum(1 for r in rows if r.passed)
    print(f"\nBen guest events check: {passed}/{len(rows)} passed\n")
    for r in rows:
        mark = "OK" if r.passed else "FAIL"
        print(f"  [{mark}] {r.area} | {r.action} | HTTP {r.http} (want {r.expected}) {r.notes}")
    print()


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)

    r = c.get(f"/v1/guest-groups/access/{CODE}")
    record("Guest", "GET access group", r.status_code, "200")
    if r.status_code != 200:
        print_report()
        return 1

    r = c.get(f"/v1/guest-groups/access/{CODE}/host-offerings")
    record("Guest", "GET host-offerings", r.status_code, "200")
    city = CITY
    if r.status_code == 200:
        body = r.json() or {}
        ho = (body.get("host_offerings") or {}) if body.get("success") else {}
        stay = ho.get("stay_info") or {}
        host = ho.get("host_info") or {}
        loc = ho.get("location_info") or {}
        for candidate in (
            host.get("broader_city"),
            loc.get("city"),
            host.get("city"),
            stay.get("city"),
            CITY,
        ):
            if candidate and str(candidate).strip():
                city = str(candidate).strip()
                break
        record("Guest", "resolved city", 200, "200", city)

    r = c.post(f"/v1/realtime/events/bootstrap?city={city}")
    record("Events", "bootstrap", r.status_code, "200")

    r = c.get(f"/v1/realtime/events?city={city}&hours=168")
    record("Events", "GET realtime/events", r.status_code, "200")
    n = 0
    if r.status_code == 200 and isinstance(r.json(), list):
        n = len(r.json())
        record("Events", "feed has items", 200 if n > 0 else 404, "200", f"count={n}")

    r = c.get("/v1/attractions/seasonal-events", params={"city": city, "active_only": True})
    record("Events", "GET seasonal-events", r.status_code, "200")
    if r.status_code == 200 and isinstance(r.json(), list):
        record("Events", "seasonal list", 200, "200", f"count={len(r.json())}")

    r = c.get(f"/v1/guest-groups/access/{CODE}/event-recommendations", params={"limit": 10})
    record("Events", "GET event-recommendations", r.status_code, "200")
    if r.status_code == 200:
        body = r.json()
        recs = body.get("recommendations") or []
        record("Events", "scored recommendations", 200 if recs else 404, "200", f"count={len(recs)}")
        if recs:
            top = recs[0]
            has_why = bool(top.get("why_recommended") and top.get("plan_hint"))
            record("Events", "why + plan_hint", 200 if has_why else 404, "200")
            qa_visible = any(
                "qa event" in str(x.get("title", "")).lower()
                or "test seasonal event" in str(x.get("description", "")).lower()
                for x in recs
            )
            record("Events", "no QA artifacts", 404 if qa_visible else 200, "200")
            top_id = str(top.get("id") or "")
            if top_id:
                r_save = c.post(
                    f"/v1/guest-groups/access/{CODE}/saved-events",
                    json={
                        "event_id": top_id,
                        "title": top.get("title"),
                        "source": top.get("source"),
                        "description": top.get("description"),
                        "url": top.get("url"),
                        "event_type": top.get("event_type"),
                        "cities": top.get("cities") or [],
                        "regions": top.get("regions") or [],
                        "start_date": top.get("start_date"),
                        "end_date": top.get("end_date"),
                        "booking_required": top.get("booking_required"),
                        "distance_km": top.get("distance_km"),
                        "why_recommended": top.get("why_recommended"),
                        "plan_hint": top.get("plan_hint"),
                    },
                )
                record("Saved events", "save top event", r_save.status_code, "200")
                r_get = c.get(f"/v1/guest-groups/access/{CODE}/saved-events")
                record("Saved events", "list saved", r_get.status_code, "200")
                if r_get.status_code == 200:
                    ids = r_get.json().get("saved_event_ids") or []
                    saved_rows = r_get.json().get("saved_events") or []
                    saved_row = next(
                        (row for row in saved_rows if str(row.get("event_id")) == top_id),
                        {},
                    )
                    record(
                        "Saved events",
                        "saved id present",
                        200 if top_id in ids else 404,
                        "200",
                    )
                    record(
                        "Saved events",
                        "saved snapshot persisted",
                        200 if saved_row.get("plan_hint") and isinstance(saved_row.get("cities"), list) else 404,
                        "200",
                    )
                r_intent = c.patch(
                    f"/v1/guest-groups/access/{CODE}/saved-events/{top_id}",
                    json={
                        "guest_action": "preferred_day",
                        "guest_note": "Regression check: guest wants this event in the plan.",
                        "preferred_day_plan_id": "regression-day-1",
                        "preferred_day_number": 1,
                        "preferred_day_title": "Arrival ideas",
                    },
                )
                record("Saved events", "add planning intent", r_intent.status_code, "200")
                if r_intent.status_code == 200:
                    saved_rows = r_intent.json().get("saved_events") or []
                    saved_row = next(
                        (row for row in saved_rows if str(row.get("event_id")) == top_id),
                        {},
                    )
                    record(
                        "Saved events",
                        "planning day persisted",
                        200 if saved_row.get("preferred_day_number") == 1 else 404,
                        "200",
                    )
                r_del = c.delete(f"/v1/guest-groups/access/{CODE}/saved-events/{top_id}")
                record("Saved events", "remove saved", r_del.status_code, "200")

    print_report()
    failed = [r for r in rows if not r.passed]
    # Feed may be empty on a fresh DB — only fail on HTTP / access errors.
    soft = ("feed has items", "scored recommendations")
    hard = [r for r in failed if r.action not in soft]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
