#!/usr/bin/env python3
"""
Ben scenario: exercise every guest-side component via API (read + write).

Usage:
  python tests/ben_guest_full_components.py
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
CODE = os.getenv("BEN_GUEST_ACCESS_CODE", "72HQ5TJL")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")


@dataclass
class Row:
    component: str
    action: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        codes = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in codes if codes else False


rows: list[Row] = []
state: dict = {"pref_id": None, "rec_id": None, "host_token": None}


def record(component: str, action: str, http: int, expected: str, notes: str = "") -> None:
    rows.append(Row(component, action, http, expected, notes[:180]))


def host_h() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if state.get("host_token"):
        h["X-Session-Token"] = state["host_token"]
    return h


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)
    tag = uuid.uuid4().hex[:6]

    # --- Join / access ---
    r = c.post("/v1/guest-groups/access/validate", json={"access_code": CODE})
    record("Join", "POST access/validate", r.status_code, "200")

    r = c.get(f"/v1/guest-groups/access/{CODE}")
    record("Join", "GET access group", r.status_code, "200")
    if r.status_code != 200:
        print_report()
        return 1
    group = r.json()
    group_name = group.get("group_name", "")

    r = c.get(f"/v1/guest-groups/access/INVALID{tag}")
    record("Join", "invalid access code", r.status_code, "401/404")

    # --- Preferences ---
    r = c.get(f"/v1/guest-groups/access/{CODE}/preferences")
    record("Preferences", "list", r.status_code, "200")
    prefs = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
    if prefs:
        state["pref_id"] = prefs[0].get("id")

    guest_name = f"Ben API Guest {tag}"
    test_pref_id = None
    r = c.post(
        f"/v1/guest-groups/access/{CODE}/preferences",
        json={
            "guest_name": guest_name,
            "age_category": "adult",
            "personal_interests": ["food", "nature"],
            "dietary_needs": [],
            "cultural_interests": ["history"],
            "food_interests": ["food"],
            "language_preference": "en",
            "mobility_notes": "Mobility: high\nBudget: medium",
        },
    )
    record("Preferences", "create", r.status_code, "201")
    if r.status_code == 201:
        test_pref_id = r.json().get("id")

    if test_pref_id:
        r = c.put(
            f"/v1/guest-groups/access/{CODE}/preferences/{test_pref_id}",
            json={"personal_interests": ["food", "history", "nature"]},
        )
        record("Preferences", "update", r.status_code, "200")
        r = c.delete(f"/v1/guest-groups/access/{CODE}/preferences/{test_pref_id}")
        record("Preferences", "delete test guest", r.status_code, "204")

    # --- Welcome / host offerings ---
    r = c.get(f"/v1/guest-groups/access/{CODE}/host-offerings")
    record("Welcome", "host-offerings", r.status_code, "200")
    if r.status_code == 200:
        payload = r.json()
        ok = bool(payload.get("success")) and bool(payload.get("host_offerings"))
        record("Welcome", "offerings shape", 200 if ok else 500, "200", "success+host_offerings")

    # --- Message host ---
    r = c.post(
        f"/v1/guest-groups/access/{CODE}/host-message",
        json={
            "message": f"Guest API test message {tag}",
            "guest_name": guest_name,
        },
    )
    record("Message", "host-message", r.status_code, "200")

    # --- Discover (recommendations) ---
    r = c.post(f"/v1/recommendations/guest/{CODE}", json={})
    recs = []
    if r.status_code == 200:
        data = r.json()
        recs = data.get("recommendations", data) if isinstance(data, dict) else data
        if isinstance(recs, list) and recs:
            state["rec_id"] = recs[0].get("id")
    record("Discover", "fetch recommendations", r.status_code, "200", f"count={len(recs) if isinstance(recs, list) else 0}")

    r = c.get(f"/v1/recommendations/guest/{CODE}/history")
    record("Discover", "history", r.status_code, "200")

    if state["rec_id"]:
        r = c.post(
            f"/v1/recommendations/guest/{CODE}/feedback",
            json={
                "recommendation_id": state["rec_id"],
                "rating": 5,
                "feedback_text": f"API guest feedback {tag}",
            },
        )
        record("Discover", "feedback", r.status_code, "200/201")

    # --- Plan (itinerary) ---
    r = c.get(f"/v1/itineraries/guest/{CODE}/itinerary")
    record("Plan", "itinerary", r.status_code, "200/404")

    # --- Report issue (maintenance) ---
    r = c.post(
        "/v1/maintenance/guest-reports",
        json={
            "access_code": CODE,
            "category": "plumbing",
            "title": f"Guest report {tag}",
            "description": "Automated guest-side QA test report.",
        },
    )
    record("Maintenance", "guest-reports", r.status_code, "201")

    # Host can see maintenance issue (sanity)
    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        state["host_token"] = r.json().get("session_token")
        r2 = c.get("/v1/maintenance/issues", headers=host_h())
        record("Maintenance", "host lists issues", r2.status_code, "200")

    failed = [x for x in rows if not x.passed]
    print_report()
    return 1 if failed else 0


def print_report() -> None:
    print(f"\nBen guest full components — {BASE} — code {CODE}\n")
    print("| Component | Action | HTTP | Expected | OK | Notes |")
    print("|-----------|--------|------|----------|-----|-------|")
    for row in rows:
        ok = "PASS" if row.passed else "FAIL"
        print(f"| {row.component} | {row.action} | {row.http} | {row.expected} | {ok} | {row.notes} |")
    passed = sum(1 for r in rows if r.passed)
    print(f"\n**{passed}/{len(rows)} passed.**\n")


if __name__ == "__main__":
    sys.exit(main())
