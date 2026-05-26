#!/usr/bin/env python3
"""Full platform check as Ben Test host."""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")


@dataclass
class Row:
    area: str
    endpoint: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        exp = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in exp if exp else False


results: list[Row] = []
state: dict = {"token": None, "host_id": None, "attraction_id": None, "guest_group_id": None}


def record(area: str, endpoint: str, http: int, expected: str, notes: str = "") -> None:
    results.append(Row(area, endpoint, http, expected, notes[:160]))


def headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if state["token"]:
        h["X-Session-Token"] = state["token"]
    return h


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)

    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    record("auth", "POST /hosts/login", r.status_code, "200", r.text[:80] if r.status_code != 200 else "")
    if r.status_code != 200:
        print_table()
        return 1
    data = r.json()
    state["token"] = data.get("session_token")
    state["host_id"] = (data.get("host") or {}).get("id")

    r = c.get("/v1/hosts/me", headers=headers())
    record("auth", "GET /hosts/me", r.status_code, "200")

    r = c.get("/v1/hosts/me/profile", headers=headers())
    record("auth", "GET /hosts/me/profile", r.status_code, "200/404")

    r = c.get("/v1/hosts/sessions", headers=headers())
    record("auth", "GET /hosts/sessions", r.status_code, "200")

    r = c.get("/v1/settings/", headers=headers())
    record("settings", "GET /settings/", r.status_code, "200")

    r = c.get("/v1/attractions/host", headers=headers())
    record("attractions", "GET /attractions/host", r.status_code, "200")
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        state["attraction_id"] = r.json()[0].get("id")

    payload = {
        "name": f"Ben QA {uuid.uuid4().hex[:6]}",
        "description": "Automated Ben Test attraction for platform QA.",
        "attraction_type": "cultural",
        "city": "Lovran",
        "address": "Lovran, Croatia",
        "latitude": 45.2733,
        "longitude": 14.2711,
    }
    r = c.post("/v1/attractions/", headers=headers(), json=payload)
    record("attractions", "POST /attractions/", r.status_code, "201", r.text[:80] if r.status_code != 201 else "")
    if r.status_code == 201:
        state["attraction_id"] = r.json().get("id")

    if state["attraction_id"]:
        aid = state["attraction_id"]
        r = c.get(f"/v1/attractions/{aid}", headers=headers())
        record("attractions", "GET /attractions/{id}", r.status_code, "200")
        r = c.put(
            f"/v1/attractions/{aid}/",
            headers=headers(),
            json={"host_personal_tip": "Ben QA tip"},
        )
        record("attractions", "PUT /attractions/{id}/", r.status_code, "200")

    r = c.get("/v1/guest-groups/host", headers=headers())
    record("guests", "GET /guest-groups/host", r.status_code, "200")

    gr = {
        "group_name": f"Ben QA Group {uuid.uuid4().hex[:6]}",
        "group_size": 2,
        "preferences": [{"category": "food", "interest_level": 8}],
    }
    r = c.post("/v1/guest-groups/", headers=headers(), json=gr)
    record("guests", "POST /guest-groups/", r.status_code, "201/200", r.text[:80] if r.status_code not in (200, 201) else "")

    r = c.get("/v1/hosts/analytics", headers=headers())
    record("dashboard", "GET /hosts/analytics", r.status_code, "200")

    r = c.get("/v1/recommendations/host/analytics?days=30", headers=headers())
    record("insights", "GET /recommendations/host/analytics", r.status_code, "200")

    r = c.get("/v1/realtime/updates", headers=headers())
    record("insights", "GET /realtime/updates", r.status_code, "200")

    r = c.get("/v1/channel-integrations/status", headers=headers())
    record("channels", "GET /channel-integrations/status", r.status_code, "200")

    for path, area in [
        ("/v1/maintenance/issues", "ops"),
        ("/v1/maintenance/categories", "ops"),
        ("/v1/cleaning/providers", "ops"),
        ("/v1/adaptation/projects", "ops"),
        ("/v1/itineraries/host/templates", "routes"),
    ]:
        r = c.get(path, headers=headers())
        record(area, f"GET {path}", r.status_code, "200")

    r = c.post(
        "/v1/hosts/me/change-password",
        headers=headers(),
        json={"current_password": "wrong", "new_password": "Ben@Host2New"},
    )
    record("account", "POST change-password (wrong)", r.status_code, "400")

    print_table()
    failed = [x for x in results if not x.passed]
    return 0 if not failed else 1


def print_table() -> None:
    print(f"\nBen platform check — {BASE} — {EMAIL}\n")
    print("| Area | Endpoint | HTTP | Expected | PASS | Notes |")
    print("|------|----------|------|----------|------|-------|")
    for row in results:
        status = "PASS" if row.passed else "FAIL"
        print(f"| {row.area} | {row.endpoint} | {row.http} | {row.expected} | {status} | {row.notes} |")
    passed = sum(1 for x in results if x.passed)
    print(f"\n**{passed}/{len(results)} passed.**\n")


if __name__ == "__main__":
    sys.exit(main())
