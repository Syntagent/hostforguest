#!/usr/bin/env python3
"""
Ben Test: events & real-time tourism data feed (sources, scrape feed, seasonal events).

Usage:
  python tests/ben_events_data_check.py
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")
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
state: dict = {}


def record(area: str, action: str, http: int, expected: str, notes: str = "") -> None:
    rows.append(Row(area, action, http, expected, notes[:180]))


def host_h() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if state.get("token"):
        h["X-Session-Token"] = state["token"]
    return h


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)
    tag = uuid.uuid4().hex[:6]

    r = c.get("/v1/realtime/health")
    record("Realtime", "health", r.status_code, "200")

    r = c.post("/v1/realtime/sources/init")
    record("Realtime", "sources/init", r.status_code, "200")
    if r.status_code == 200:
        body = r.json()
        record("Realtime", "init has seed", 200, "200", str(body.get("seed", {}))[:80])

    r = c.post(f"/v1/realtime/events/bootstrap?city={CITY}")
    record("Realtime", "events/bootstrap", r.status_code, "200")
    if r.status_code == 200:
        n = (r.json() or {}).get("events_available", 0)
        record("Realtime", "bootstrap events count", 200 if n > 0 else 404, "200", f"count={n}")

    r = c.get(f"/v1/realtime/events?city={CITY}&limit=20")
    record("Realtime", "GET /events", r.status_code, "200")
    events = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
    record("Realtime", "events non-empty", 200 if len(events) > 0 else 404, "200", f"count={len(events)}")

    r = c.get(f"/v1/realtime/updates?content_types=events&city={CITY}&hours=168&limit=20")
    record("Realtime", "GET /updates?events", r.status_code, "200")

    r = c.get("/v1/realtime/summary")
    record("Realtime", "summary", r.status_code, "200")
    if r.status_code == 200:
        s = r.json()
        record(
            "Realtime",
            "sources active",
            200 if (s.get("active_sources") or 0) > 0 else 404,
            "200",
            f"active={s.get('active_sources')}",
        )

    r = c.get("/v1/realtime/sources/status")
    record("Realtime", "sources/status", r.status_code, "200")

    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    record("Auth", "login", r.status_code, "200")
    if r.status_code == 200:
        state["token"] = r.json().get("session_token")

    r = c.get("/v1/attractions/seasonal-events", params={"city": CITY})
    record("Seasonal", "list", r.status_code, "200")

    if state.get("token"):
        start = date.today()
        end = start + timedelta(days=30)
        r = c.post(
            "/v1/attractions/seasonal-events",
            headers=host_h(),
            json={
                "name": f"Ben QA Event {tag}",
                "description": "Test seasonal event for Ben events QA.",
                "event_type": "festival",
                "city": CITY,
                "location": "Lovran old town",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "host_recommendation": "Worth visiting with guests.",
            },
        )
        record("Seasonal", "create", r.status_code, "201")
        r2 = c.get("/v1/attractions/seasonal-events", params={"city": CITY})
        if r2.status_code == 200 and isinstance(r2.json(), list):
            names = [e.get("name") for e in r2.json()]
            record(
                "Seasonal",
                "created visible",
                200 if any("Ben QA Event" in (n or "") for n in names) else 404,
                "200",
            )

    failed = [x for x in rows if not x.passed]
    print_report()
    return 1 if failed else 0


def print_report() -> None:
    print(f"\nBen events data check — {BASE} — city {CITY}\n")
    print("| Area | Action | HTTP | Expected | OK | Notes |")
    print("|------|--------|------|----------|-----|-------|")
    for row in rows:
        ok = "PASS" if row.passed else "FAIL"
        print(f"| {row.area} | {row.action} | {row.http} | {row.expected} | {ok} | {row.notes} |")
    passed = sum(1 for r in rows if r.passed)
    print(f"\n**{passed}/{len(rows)} passed.**\n")


if __name__ == "__main__":
    sys.exit(main())
