#!/usr/bin/env python3
"""
Ben Test: create a scenario guest group and simulate multi-guest interaction.

Usage:
  python tests/ben_guest_interaction_scenario.py
  BEN_SCENARIO_REUSE=1  # reuse existing "Ben Scenario Family 2026" if present
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    )
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")
SCENARIO_GROUP_NAME = os.getenv("BEN_SCENARIO_GROUP_NAME", "Ben Scenario Family 2026")

GUEST_PERSONAS = [
    {
        "guest_name": "Ana Perak",
        "age_category": "adult",
        "personal_interests": ["food", "history"],
        "dietary_needs": [],
        "cultural_interests": ["history"],
        "food_interests": ["food"],
        "language_preference": "hr",
        "mobility_notes": "Email: ana.perak@example.com\nMobility: high\nBudget: medium",
    },
    {
        "guest_name": "Marko Perak",
        "age_category": "teen",
        "personal_interests": ["adventure", "nature"],
        "dietary_needs": [],
        "cultural_interests": [],
        "food_interests": [],
        "language_preference": "en",
        "mobility_notes": "Email: marko.perak@example.com\nMobility: high\nBudget: medium",
    },
    {
        "guest_name": "Luka Perak",
        "age_category": "child",
        "personal_interests": ["nature"],
        "dietary_needs": ["Gluten-free"],
        "cultural_interests": [],
        "food_interests": [],
        "language_preference": "en",
        "mobility_notes": "Email: luka.perak@example.com\nMobility: medium\nBudget: low",
    },
]


@dataclass
class Row:
    step: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        codes = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in codes if codes else False


rows: list[Row] = []
state: dict = {"token": None, "group_id": None, "access_code": None, "rec_id": None}


def record(step: str, http: int, expected: str, notes: str = "") -> None:
    rows.append(Row(step, http, expected, notes[:200]))


def host_headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if state["token"]:
        h["X-Session-Token"] = state["token"]
    return h


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)

    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    record("host login", r.status_code, "200")
    if r.status_code != 200:
        print_report()
        return 1
    state["token"] = r.json().get("session_token")

    reuse = os.getenv("BEN_SCENARIO_REUSE", "1") == "1"
    existing = None
    if reuse:
        r = c.get("/v1/guest-groups/host", headers=host_headers())
        if r.status_code == 200 and isinstance(r.json(), list):
            for g in r.json():
                if g.get("group_name") == SCENARIO_GROUP_NAME:
                    existing = g
                    break

    if existing:
        state["group_id"] = existing.get("id")
        state["access_code"] = existing.get("access_code")
        record("reuse scenario group", 200, "200", str(state["group_id"]))
        if not state["access_code"]:
            r = c.post(
                f"/v1/guest-groups/{state['group_id']}/regenerate-code",
                headers=host_headers(),
                json={},
            )
            record("regenerate access code", r.status_code, "200")
            if r.status_code == 200:
                state["access_code"] = r.json().get("access_code")
    else:
        now = datetime.now(timezone.utc)
        body = {
            "group_name": SCENARIO_GROUP_NAME,
            "group_size": len(GUEST_PERSONAS),
            "check_in_date": now.isoformat(),
            "check_out_date": (now + timedelta(days=7)).isoformat(),
            "lead_guest_name": "Ana Perak",
            "lead_guest_email": "ana.perak@example.com",
        }
        r = c.post("/v1/guest-groups/", headers=host_headers(), json=body)
        record("create scenario group", r.status_code, "201/200")
        if r.status_code not in (200, 201):
            print_report()
            return 1
        g = r.json()
        state["group_id"] = g.get("id")
        state["access_code"] = g.get("access_code")

    code = state["access_code"]
    if not code:
        print_report()
        return 1

    r = c.get(f"/v1/guest-groups/access/{code}")
    record("guest validate access code", r.status_code, "200")

    r = c.get(f"/v1/guest-groups/access/{code}/preferences")
    existing_names = set()
    if r.status_code == 200 and isinstance(r.json(), list):
        existing_names = {p.get("guest_name") for p in r.json()}

    for persona in GUEST_PERSONAS:
        if persona["guest_name"] in existing_names:
            record(f"skip existing guest {persona['guest_name']}", 200, "200", "already registered")
            continue
        r = c.post(
            f"/v1/guest-groups/access/{code}/preferences",
            json=persona,
        )
        record(f"guest registers: {persona['guest_name']}", r.status_code, "201")

    r = c.get(f"/v1/guest-groups/access/{code}/preferences")
    n = len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else 0
    record("list guest preferences", r.status_code, "200", f"count={n}")

    r = c.get(f"/v1/guest-groups/access/{code}/host-offerings")
    record("guest host offerings", r.status_code, "200")

    r = c.post(
        f"/v1/guest-groups/access/{code}/host-message",
        json={
            "message": "We would love a family-friendly restaurant near Lovran for tonight.",
            "guest_name": "Ana Perak",
        },
    )
    record("guest message to host", r.status_code, "200")

    r = c.post(
        "/v1/recommendations/host/generate",
        headers=host_headers(),
        json={"guest_group_id": state["group_id"], "max_recommendations": 6},
    )
    record("host generate recommendations", r.status_code, "200/503")

    r = c.post(f"/v1/recommendations/guest/{code}", json={})
    recs = []
    if r.status_code == 200:
        data = r.json()
        recs = data.get("recommendations", data) if isinstance(data, dict) else data
        if isinstance(recs, list) and recs:
            state["rec_id"] = recs[0].get("id")
    record("guest fetch recommendations", r.status_code, "200", f"count={len(recs) if isinstance(recs, list) else 0}")

    r = c.get(f"/v1/recommendations/guest/{code}/history")
    record("guest recommendation history", r.status_code, "200")

    if state["rec_id"]:
        r = c.post(
            f"/v1/recommendations/guest/{code}/feedback",
            json={
                "recommendation_id": state["rec_id"],
                "rating": 5,
                "feedback_text": "Great pick from Ben scenario test!",
            },
        )
        record("guest recommendation feedback", r.status_code, "200/201")

    r = c.get(f"/v1/itineraries/guest/{code}/itinerary")
    record("guest itinerary", r.status_code, "200/404", "null itinerary is ok")

    r = c.get(
        f"/v1/guest-groups/{state['group_id']}/guest-experience",
        headers=host_headers(),
    )
    record("host guest-experience view", r.status_code, "200")

    failed = [x for x in rows if not x.passed]
    print_report()
    print()
    print("--- Scenario credentials (share with guests) ---")
    print(f"Group: {SCENARIO_GROUP_NAME}")
    print(f"Access code: {code}")
    print(f"Join URL: https://hostforguest.syntagent.com/guest/join")
    print(f"Direct:   https://hostforguest.syntagent.com/guest/{code}")
    return 1 if failed else 0


def print_report() -> None:
    print(f"\nBen guest interaction scenario — {BASE}\n")
    print("| Step | HTTP | Expected | OK | Notes |")
    print("|------|------|----------|-----|-------|")
    for row in rows:
        ok = "PASS" if row.passed else "FAIL"
        print(f"| {row.step} | {row.http} | {row.expected} | {ok} | {row.notes} |")
    passed = sum(1 for r in rows if r.passed)
    print(f"\n**{passed}/{len(rows)} passed.**\n")


if __name__ == "__main__":
    sys.exit(main())
