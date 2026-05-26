#!/usr/bin/env python3
"""Full API UX test against production (hostforguest.syntagent.com)."""
from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

BASE = "https://hostforguest.syntagent.com/api"
EMAIL = "bperak@uniri.hr"
PASSWORD = "Drinkable1A"
HOST_ID = "cd609520-8ab2-409f-87ea-328077c4f9e0"


@dataclass
class Row:
    num: str
    endpoint: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        exp = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in exp if exp else False


results: list[Row] = []
state: dict[str, Any] = {
    "token": None,
    "host_id": HOST_ID,
    "attraction_id": None,
    "guest_group_id": None,
    "access_code": None,
    "old_token": None,
}


def record(num: str, endpoint: str, http: int, expected: str, notes: str = "") -> None:
    results.append(Row(num, endpoint, http, expected, notes[:120]))


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=120.0)


def auth_headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if state["token"]:
        h["X-Session-Token"] = state["token"]
    return h


def main() -> int:
    c = client()

    # TASK 1 — login if already registered, else register
    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        data = r.json()
        state["token"] = data.get("session_token")
        state["host_id"] = (data.get("host") or {}).get("id") or state["host_id"]
        record("1", "POST /hosts/login (existing)", r.status_code, "200", f"host_id={state['host_id']}")
    else:
        r = c.post(
            "/v1/hosts/register",
            json={
                "email": EMAIL,
                "password": PASSWORD,
                "first_name": "Benedikt",
                "last_name": "Perak",
                "business_name": "Syntagent",
                "business_type": "private_accommodation",
                "address": "Oprić 71",
                "city": "Lovran",
                "county": "Primorsko-goranska",
                "postal_code": "51415",
                "country": "Croatia",
                "phone": "+38598622793",
                "languages": ["hr", "en", "de", "it"],
            },
        )
        if r.status_code == 201:
            state["host_id"] = r.json().get("id") or state["host_id"]
            record("1", "POST /hosts/register", r.status_code, "201", "new host")
        else:
            record("1", "POST /hosts/register", r.status_code, "201/400", r.text[:80])
        r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code == 200:
            data = r.json()
            state["token"] = data.get("session_token")
            state["host_id"] = (data.get("host") or {}).get("id") or state["host_id"]
            record("1b", "POST /hosts/login", r.status_code, "200", f"host_id={state['host_id']}")
        else:
            record("1b", "POST /hosts/login", r.status_code, "200", r.text[:80])
            print("FATAL: cannot login", file=sys.stderr)
            print_table()
            return 1

    # TASK 2
    profile_payload = {
        "property_name": "Villa Oprić 71",
        "property_type": "apartment",
        "max_guests": 6,
        "amenities": [
            "wifi",
            "parking",
            "terrace",
            "sea_view",
            "kitchen",
            "air_conditioning",
            "heating",
        ],
        "location_story": (
            "Docent na Filozofskom fakultetu Sveučilišta u Rijeci i osnivač Syntagent-a. "
            "Nudim smještaj u mirnom dijelu Lovrana s pogledom na Kvarner."
        ),
        "expertise_areas": [
            "Lovran old town",
            "Opatija riviera",
            "Učka nature park",
            "Kvarner islands",
        ],
        "services_offered": ["hr", "en", "de", "it"],
    }
    r = c.post("/v1/hosts/me/profile", headers=auth_headers(), json=profile_payload)
    if r.status_code == 201:
        record("2", "POST /hosts/me/profile", r.status_code, "201", "created")
    elif r.status_code == 400:
        r2 = c.put("/v1/hosts/me/profile", headers=auth_headers(), json=profile_payload)
        record("2", "PUT /hosts/me/profile", r2.status_code, "200", "profile existed, updated")
    else:
        record("2", "POST /hosts/me/profile", r.status_code, "201/200", r.text[:80])

    # TASK 3
    r = c.get(f"/v1/onboarding/progress/{state['host_id']}")
    record("3.1", f"GET /onboarding/progress/{state['host_id']}", r.status_code, "200", "progress")

    r = c.put(
        "/v1/hosts/me",
        headers=auth_headers(),
        json={"latitude": 45.2739, "longitude": 14.2711},
    )
    record("2b", "PUT /hosts/me (coords)", r.status_code, "200", "Lovran coords for nearby")

    onboarding_basic = {
        "first_name": "Benedikt",
        "last_name": "Perak",
        "business_name": "Syntagent",
        "city": "Lovran",
        "address": "Oprić 71",
        "region": "Primorsko-goranska",
        "business_type": "apartment",
        "max_group_size": 6,
        "amenities": profile_payload["amenities"],
        "local_experience": "experienced",
        "location_story": profile_payload["location_story"],
        "specialties": ["culture", "nature", "gastronomy"],
        "preferred_guests": ["families", "couples"],
        "languages": ["hr", "en", "de", "it"],
        "hosting_experience": 6,
        "interests": ["history", "hiking", "local food"],
    }
    r = c.post(
        "/v1/onboarding/generate-profile-suggestions",
        headers=auth_headers(),
        json=onboarding_basic,
    )
    record(
        "3.2",
        "POST /onboarding/generate-profile-suggestions",
        r.status_code,
        "200",
        "AI" if r.status_code == 200 else r.text[:60],
    )

    r = c.post(
        "/v1/onboarding/validate-profile",
        headers=auth_headers(),
        json={
            **onboarding_basic,
            "property_name": "Villa Oprić 71",
            "email": EMAIL,
        },
    )
    record("3.3", "POST /onboarding/validate-profile", r.status_code, "200", "validation")

    # TASK 4
    r = c.get("/v1/attractions/")
    record("4.1", "GET /attractions/", r.status_code, "200")

    r = c.get("/v1/attractions/search", params={"q": "Lovran"})
    record("4.2", "GET /attractions/search?q=Lovran", r.status_code, "200")

    r = c.get("/v1/attractions/search", params={"city": "Opatija"})
    record("4.3", "GET /attractions/search?city=Opatija", r.status_code, "200")

    attr_body = {
        "name": "Lovran Old Town",
        "description": "Historical core of Lovran with its medieval architecture",
        "attraction_type": "landmark",
        "category_tags": ["culture", "history", "walking"],
        "city": "Lovran",
    }
    r = c.post("/v1/attractions/", headers=auth_headers(), json=attr_body)
    if r.status_code in (200, 201):
        state["attraction_id"] = r.json().get("id")
    record("4.4", "POST /attractions/", r.status_code, "201", f"id={state['attraction_id']}")

    r = c.get("/v1/attractions/host", headers=auth_headers())
    record("4.5", "GET /attractions/host", r.status_code, "200")

    aid = state["attraction_id"]
    if aid:
        r = c.get(f"/v1/attractions/{aid}", headers=auth_headers())
        record("4.6", f"GET /attractions/{aid}", r.status_code, "200")
    else:
        record("4.6", "GET /attractions/{id}", 0, "200", "skipped — no id")

    r = c.post(
        "/v1/attractions/ai-enhance",
        headers=auth_headers(),
        json={
            "attraction_name": "Lovran Old Town",
            "location": "Lovran",
            "attraction_type": "landmark",
            "current_description": attr_body["description"],
            "host_location": "Lovran",
        },
    )
    record(
        "4.7",
        "POST /attractions/ai-enhance",
        r.status_code,
        "200",
        "AI ok" if r.status_code == 200 else r.text[:60],
    )

    # TASK 5
    gg_body = {
        "group_name": "Obitelj Oprić - Srpanj 2026",
        "group_size": 4,
        "check_in_date": "2026-07-01T14:00:00Z",
        "check_out_date": "2026-07-14T10:00:00Z",
        "lead_guest_name": "Mario Horvat",
        "lead_guest_email": "mario@example.com",
    }
    r = c.post("/v1/guest-groups/", headers=auth_headers(), json=gg_body)
    if r.status_code in (200, 201):
        j = r.json()
        state["guest_group_id"] = j.get("id")
        state["access_code"] = j.get("access_code")
    record("5.1", "POST /guest-groups/", r.status_code, "201", f"code={state['access_code']}")

    r = c.get("/v1/guest-groups/host", headers=auth_headers())
    record("5.2", "GET /guest-groups/host", r.status_code, "200")

    gid = state["guest_group_id"]
    if gid:
        r = c.get(f"/v1/guest-groups/{gid}", headers=auth_headers())
        record("5.3", f"GET /guest-groups/{gid}", r.status_code, "200")

        r = c.put(
            f"/v1/guest-groups/{gid}",
            headers=auth_headers(),
            json={"group_size": 5},
        )
        record("5.4", f"PUT /guest-groups/{gid}", r.status_code, "200", "group_size=5")

        code = state["access_code"]
        if code:
            r = c.post(
                "/v1/guest-groups/access/validate",
                json={"access_code": code},
            )
            record("5.5", "POST /guest-groups/access/validate", r.status_code, "200", code)

            r = c.get(f"/v1/guest-groups/access/{code}")
            record("5.6", f"GET /guest-groups/access/{code}", r.status_code, "200")
        else:
            record("5.5", "POST /guest-groups/access/validate", 0, "200", "no access_code")
            record("5.6", "GET /guest-groups/access/{code}", 0, "200", "skipped")

        ev = {
            "first_name": "Mario",
            "last_name": "Horvat",
            "date_of_birth": "1985-03-15T00:00:00Z",
            "nationality": "Croatia",
            "id_type": "id_card",
            "id_number": "12345678901",
            "id_issuing_country": "Croatia",
            "arrival_date": "2026-07-01T14:00:00Z",
            "departure_date": "2026-07-14T10:00:00Z",
            "email": "mario@example.com",
        }
        r = c.post(
            f"/v1/guest-groups/{gid}/evisitor-data",
            headers=auth_headers(),
            json=ev,
        )
        record("5.7", f"POST /guest-groups/{gid}/evisitor-data", r.status_code, "201")

        r = c.get(
            f"/v1/guest-groups/{gid}/evisitor-data",
            headers=auth_headers(),
        )
        record("5.8", f"GET /guest-groups/{gid}/evisitor-data", r.status_code, "200")
    else:
        for n, ep in [
            ("5.3", "GET /guest-groups/{id}"),
            ("5.4", "PUT /guest-groups/{id}"),
            ("5.5", "POST access/validate"),
            ("5.6", "GET access/{code}"),
            ("5.7", "POST evisitor-data"),
            ("5.8", "GET evisitor-data"),
        ]:
            record(n, ep, 0, "200/201", "skipped — no guest group")

    # TASK 6
    if gid:
        r = c.post(
            "/v1/recommendations/host/generate",
            headers=auth_headers(),
            json={"guest_group_id": gid, "max_recommendations": 5},
        )
        record(
            "6.1",
            "POST /recommendations/host/generate",
            r.status_code,
            "200",
            "AI" if r.status_code == 200 else r.text[:60],
        )
    else:
        record("6.1", "POST /recommendations/host/generate", 0, "200", "skipped")

    r = c.get("/v1/recommendations/host/analytics", headers=auth_headers())
    record("6.2", "GET /recommendations/host/analytics", r.status_code, "200")

    if gid:
        r = c.get(
            f"/v1/recommendations/host/guest-groups/{gid}/analytics",
            headers=auth_headers(),
        )
        record("6.3", f"GET .../guest-groups/{gid}/analytics", r.status_code, "200")
    else:
        record("6.3", "GET .../guest-groups/{id}/analytics", 0, "200", "skipped")

    # TASK 7
    for n, path in [
        ("7.1", "/v1/bi/dashboard"),
        ("7.2", "/v1/bi/revenue"),
        ("7.3", "/v1/bi/seasonal-trends"),
        ("7.4", "/v1/bi/ltv"),
        ("7.5", "/v1/hosts/analytics"),
    ]:
        r = c.get(path, headers=auth_headers())
        record(n, f"GET {path.replace('/v1', '')}", r.status_code, "200")

    # TASK 8
    if gid:
        r = c.post(
            "/v1/communications/welcome-kit/generate",
            headers=auth_headers(),
            json={"guest_group_id": gid},
        )
        record("8.1", "POST /communications/welcome-kit/generate", r.status_code, "200")

        r = c.post(
            "/v1/communications/welcome-kit/send",
            headers=auth_headers(),
            json={"guest_group_id": gid, "delivery_method": "email"},
        )
        record("8.2", "POST /communications/welcome-kit/send", r.status_code, "200")

        r = c.post(
            "/v1/communications/pre-arrival-email",
            headers=auth_headers(),
            json={"guest_group_id": gid},
        )
        record("8.3", "POST /communications/pre-arrival-email", r.status_code, "200")
    else:
        for n, ep in [("8.1", "welcome-kit/generate"), ("8.2", "welcome-kit/send"), ("8.3", "pre-arrival-email")]:
            record(n, f"POST /communications/{ep}", 0, "200", "skipped")

    r = c.post(
        "/v1/communications/sms",
        headers=auth_headers(),
        json={
            "phone_number": "+38598622793",
            "message": "HostForGuest test SMS",
            "language": "hr",
        },
    )
    record("8.4", "POST /communications/sms", r.status_code, "200", r.text[:60] if r.status_code != 200 else "ok")

    # TASK 9
    r = c.get(f"/v1/locations/nearby/{state['host_id']}", headers=auth_headers())
    record("9.1", f"GET /locations/nearby/{state['host_id']}", r.status_code, "200")

    r = c.get("/v1/cleaning/providers", headers=auth_headers())
    record("9.2", "GET /cleaning/providers", r.status_code, "200")

    r = c.get(
        f"/v1/partners/hosts/{state['host_id']}/partners",
        headers=auth_headers(),
    )
    record("9.3", f"GET /partners/hosts/{state['host_id']}/partners", r.status_code, "200")

    # TASK 10
    if aid:
        r = c.post(
            "/v1/content-generation/attractions/description",
            json={"attraction_id": aid, "language": "en"},
        )
        record("10.1", "POST /content-generation/attractions/description", r.status_code, "200")
    else:
        record("10.1", "POST content-generation/attractions/description", 0, "200", "skipped")

    r = c.post(
        "/v1/content-generation/email",
        json={
            "template_type": "welcome",
            "host_id": state["host_id"],
            "guest_group_id": gid,
            "language": "hr",
        },
    )
    record("10.2", "POST /content-generation/email", r.status_code, "200")

    if aid:
        r = c.post(
            "/v1/content-generation/social-media",
            json={"attraction_id": aid, "post_type": "instagram", "language": "hr"},
        )
        record("10.3", "POST /content-generation/social-media", r.status_code, "200")
    else:
        record("10.3", "POST /content-generation/social-media", 0, "200", "skipped")

    r = c.post(
        "/v1/content-generation/tips",
        json={"host_id": state["host_id"], "language": "hr", "count": 3},
    )
    record("10.4", "POST /content-generation/tips", r.status_code, "200")

    r = c.post(
        "/v1/content-generation/translate",
        json={
            "source_text": "Dobrodošli u Lovran!",
            "source_language": "hr",
            "target_languages": ["en", "de"],
        },
    )
    record("10.5", "POST /content-generation/translate", r.status_code, "200")

    # TASK 11 — error handling
    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": "WrongPassword!"})
    record("11.1", "POST /hosts/login (wrong pwd)", r.status_code, "401")

    r = c.post("/v1/hosts/register", json={"email": EMAIL, "password": PASSWORD, "first_name": "X"})
    record("11.2", "POST /hosts/register (dup)", r.status_code, "400/422")

    r = c.get("/v1/hosts/me")
    record("11.3", "GET /hosts/me (no token)", r.status_code, "401")

    r = c.post("/v1/guest-groups/", json={})
    record("11.4", "POST /guest-groups/ (no fields)", r.status_code, "401/422")

    r = c.get(f"/v1/guest-groups/{uuid.uuid4()}", headers=auth_headers())
    record("11.5", f"GET /guest-groups/{{fake}}", r.status_code, "404")

    # TASK 12 — session
    state["old_token"] = state["token"]
    r = c.post("/v1/hosts/refresh", headers=auth_headers(), json={})
    if r.status_code == 200:
        state["token"] = r.json().get("session_token") or state["token"]
    record("12.1", "POST /hosts/refresh", r.status_code, "200")

    r = c.get("/v1/hosts/sessions", headers=auth_headers())
    record("12.2", "GET /hosts/sessions", r.status_code, "200")

    r = c.post("/v1/hosts/logout", headers=auth_headers())
    record("12.3", "POST /hosts/logout", r.status_code, "200")

    r = c.get("/v1/hosts/me", headers={"X-Session-Token": state["old_token"]})
    record("12.4", "GET /hosts/me (old token)", r.status_code, "401")

    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        state["token"] = r.json().get("session_token")
    record("12.5", "POST /hosts/login (again)", r.status_code, "200")

    print_table()
    passed = sum(1 for x in results if x.passed)
    print(f"\n**Summary: {passed}/{len(results)} passed.**")
    return 0 if passed == len(results) else 1


def print_table() -> None:
    print("\n| # | Endpoint | HTTP | Expected | PASS/FAIL | Notes |")
    print("|---|----------|------|----------|-----------|-------|")
    for row in results:
        status = "PASS" if row.passed else "FAIL"
        print(
            f"| {row.num} | {row.endpoint} | {row.http} | {row.expected} | {status} | {row.notes} |"
        )


if __name__ == "__main__":
    sys.exit(main())
