#!/usr/bin/env python3
"""
Seed three rich guest groups for Ben Test host (benediktperak@gmail.com).

Usage (from API container or host with API up):
  python tests/seed_ben_test_three_groups.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")
PREFIX = "Ben Test"


def iso_date(y: int, m: int, d: int, hour: int = 15) -> str:
    return datetime(y, m, d, hour, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def checkout_iso(y: int, m: int, d: int) -> str:
    return datetime(y, m, d, 10, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


GROUPS = [
    {
        "group": {
            "group_name": f"{PREFIX} — Nordic Friends · Jazz Weekend",
            "group_size": 4,
            "check_in_date": iso_date(2026, 6, 20),
            "check_out_date": checkout_iso(2026, 6, 27),
            "lead_guest_name": "Sven Lindström",
            "lead_guest_email": "sven.lindstrom@example.com",
            "lead_guest_phone": "+47 412 88 901",
            "preferred_language": "en",
            "supported_languages": ["en", "no", "hr"],
            "age_groups": ["adults"],
            "interests": ["music", "wine", "coastal_walks", "local_food"],
            "mobility_requirements": [],
            "dietary_restrictions": ["pescatarian"],
            "budget_level": "luxury",
            "preferred_activities": ["Opatija jazz evenings", "Villa rustica wine tasting", "Lungomare sunset walk"],
            "avoided_activities": ["Late-night clubs", "Crowded beaches"],
            "previous_visits_croatia": True,
            "travel_style": "active",
            "group_dynamics": "friends",
            "interested_regions": ["lovran", "opatija", "mošćenička draga"],
            "seasonal_preferences": {"summer": "Prefer shaded terraces after 11:00"},
        },
        "preferences": [
            {
                "guest_name": "Sven Lindström",
                "age_category": "adult",
                "personal_interests": ["jazz", "photography", "history"],
                "dietary_needs": ["Pescatarian"],
                "cultural_interests": ["history", "architecture"],
                "food_interests": ["seafood", "wine"],
                "language_preference": "en",
                "mobility_notes": "Training for half-marathon — happy with 8–12 km hikes.\nBudget: high",
            },
            {
                "guest_name": "Ingrid Solheim",
                "age_category": "adult",
                "personal_interests": ["yoga", "markets", "design"],
                "dietary_needs": [],
                "cultural_interests": ["art", "crafts"],
                "food_interests": ["traditional", "organic"],
                "language_preference": "en",
                "mobility_notes": "Morning yoga on the terrace would be perfect.\nBudget: high",
            },
            {
                "guest_name": "Felix Andersen",
                "age_category": "adult",
                "personal_interests": ["cycling", "beer", "maps"],
                "dietary_needs": [],
                "cultural_interests": [],
                "food_interests": ["beer", "grill"],
                "language_preference": "en",
                "mobility_notes": "Brings e-bikes — needs safe storage at Villa Oprić.\nBudget: medium",
            },
            {
                "guest_name": "Maja Berg",
                "age_category": "adult",
                "personal_interests": ["swimming", "books", "botany"],
                "dietary_needs": ["Gluten-free"],
                "cultural_interests": ["nature"],
                "food_interests": ["seafood"],
                "language_preference": "no",
                "mobility_notes": "Gluten-free bakeries nearby are a plus.\nBudget: medium",
            },
        ],
        "evisitor": [
            ("Sven", "Lindström", "1988-03-14", "Norwegian", "P1234567", "Norway", "sven.lindstrom@example.com"),
            ("Ingrid", "Solheim", "1990-07-02", "Norwegian", "P2345678", "Norway", "ingrid.solheim@example.com"),
            ("Felix", "Andersen", "1987-11-21", "Danish", "P3456789", "Denmark", "felix.andersen@example.com"),
            ("Maja", "Berg", "1992-01-09", "Norwegian", "P4567890", "Norway", "maja.berg@example.com"),
        ],
        "check_in": (2026, 6, 20),
        "check_out": (2026, 6, 27),
    },
    {
        "group": {
            "group_name": f"{PREFIX} — Family Perak · Summer at Oprić",
            "group_size": 5,
            "check_in_date": iso_date(2026, 7, 8),
            "check_out_date": checkout_iso(2026, 7, 18),
            "lead_guest_name": "Ana Perak",
            "lead_guest_email": "ana.perak@example.com",
            "lead_guest_phone": "+385 91 555 0101",
            "preferred_language": "hr",
            "supported_languages": ["hr", "en", "de"],
            "age_groups": ["adults", "children", "seniors"],
            "interests": ["family_fun", "beaches", "truffles", "culture"],
            "mobility_requirements": ["stroller_friendly"],
            "dietary_restrictions": ["gluten_free"],
            "budget_level": "moderate",
            "preferred_activities": [
                "Aquapark Ičići",
                "Lovran Sunday market",
                "Easy Učka viewpoint",
            ],
            "avoided_activities": ["Extreme sports", "Long wine tours without shade"],
            "previous_visits_croatia": True,
            "travel_style": "balanced",
            "group_dynamics": "family",
            "interested_regions": ["lovran", "ičići", "moštreni"],
            "seasonal_preferences": {"july": "Siesta 13:00–16:00, beach mornings"},
        },
        "preferences": [
            {
                "guest_name": "Ana Perak",
                "age_category": "adult",
                "personal_interests": ["food", "history", "photography"],
                "dietary_needs": [],
                "cultural_interests": ["history", "folklore"],
                "food_interests": ["traditional", "truffles"],
                "language_preference": "hr",
                "mobility_notes": "Organising the group — needs clear day plans in Croatian.\nBudget: medium",
            },
            {
                "guest_name": "Tomislav Perak",
                "age_category": "adult",
                "personal_interests": ["sailing", "grill", "football"],
                "dietary_needs": [],
                "cultural_interests": [],
                "food_interests": ["grill", "beer"],
                "language_preference": "hr",
                "mobility_notes": "Happy to skipper a day trip if host recommends a skipper.\nBudget: medium",
            },
            {
                "guest_name": "Marko Perak",
                "age_category": "teen",
                "personal_interests": ["gaming", "adventure", "parks"],
                "dietary_needs": [],
                "cultural_interests": [],
                "food_interests": ["pizza", "ice_cream"],
                "language_preference": "en",
                "mobility_notes": "Teen — wants one 'epic' activity per day.\nBudget: low",
            },
            {
                "guest_name": "Luka Perak",
                "age_category": "child",
                "personal_interests": ["animals", "beach", "trains"],
                "dietary_needs": ["Gluten-free"],
                "cultural_interests": [],
                "food_interests": ["ice_cream"],
                "language_preference": "hr",
                "mobility_notes": "Age 7, gluten-free — kid-friendly restaurants essential.\nBudget: low",
            },
            {
                "guest_name": "Baka Mira",
                "age_category": "senior",
                "personal_interests": ["gardens", "church", "coffee"],
                "dietary_needs": ["Low sodium"],
                "cultural_interests": ["history", "religious_sites"],
                "food_interests": ["traditional", "coffee"],
                "language_preference": "hr",
                "mobility_notes": "Limited walking (20 min max flat). Needs lift access.\nBudget: medium",
            },
        ],
        "evisitor": [
            ("Ana", "Perak", "1985-05-20", "Croatian", "HR1234567", "Croatia", "ana.perak@example.com"),
            ("Tomislav", "Perak", "1983-09-11", "Croatian", "HR2345678", "Croatia", "tomislav.perak@example.com"),
            ("Marko", "Perak", "2010-02-18", "Croatian", "HR3456789", "Croatia", "marko.perak@example.com"),
            ("Luka", "Perak", "2018-08-30", "Croatian", "HR4567890", "Croatia", "luka.perak@example.com"),
            ("Mira", "Perak", "1955-12-03", "Croatian", "HR5678901", "Croatia", "mira.perak@example.com"),
        ],
        "check_in": (2026, 7, 8),
        "check_out": (2026, 7, 18),
    },
    {
        "group": {
            "group_name": f"{PREFIX} — Slow Travel Seniors · Autumn Truffles",
            "group_size": 2,
            "check_in_date": iso_date(2026, 9, 12),
            "check_out_date": checkout_iso(2026, 9, 22),
            "lead_guest_name": "Helga Müller",
            "lead_guest_email": "helga.wolfgang@example.de",
            "lead_guest_phone": "+49 170 555 7788",
            "preferred_language": "de",
            "supported_languages": ["de", "en", "hr"],
            "age_groups": ["seniors"],
            "interests": ["wellness", "truffles", "opera", "train_trips"],
            "mobility_requirements": ["limited_walking", "elevator_preferred"],
            "dietary_restrictions": ["low_sodium"],
            "budget_level": "luxury",
            "preferred_activities": [
                "Truffle dinner in Lovran",
                "Opatija Kaiserpromenade coffee",
                "Gentle botanical garden visit",
            ],
            "avoided_activities": ["Steep trails", "Late events"],
            "previous_visits_croatia": False,
            "travel_style": "relaxed",
            "group_dynamics": "couple",
            "interested_regions": ["lovran", "opatija", "hum"],
            "seasonal_preferences": {"autumn": "Warm layers, indoor backup plans for rain"},
        },
        "preferences": [
            {
                "guest_name": "Helga Müller",
                "age_category": "senior",
                "personal_interests": ["classical_music", "gardens", "painting"],
                "dietary_needs": ["Low sodium"],
                "cultural_interests": ["history", "music"],
                "food_interests": ["traditional", "wine"],
                "language_preference": "de",
                "mobility_notes": "Uses walking stick — prefers benches every 200 m.\nBudget: high",
            },
            {
                "guest_name": "Wolfgang Müller",
                "age_category": "senior",
                "personal_interests": ["trains", "photography", "chess"],
                "dietary_needs": ["Low sodium"],
                "cultural_interests": ["history"],
                "food_interests": ["truffles", "beer"],
                "language_preference": "de",
                "mobility_notes": "Rail enthusiast — Rijeka–Pula bus OK, no night driving.\nBudget: high",
            },
        ],
        "evisitor": [
            ("Helga", "Müller", "1958-04-17", "German", "C01X23456", "Germany", "helga.wolfgang@example.de"),
            ("Wolfgang", "Müller", "1956-10-05", "German", "C02Y34567", "Germany", "wolfgang.mueller@example.de"),
        ],
        "check_in": (2026, 9, 12),
        "check_out": (2026, 9, 22),
    },
]


def evisitor_row(
    group_id: str,
    first: str,
    last: str,
    dob: str,
    nationality: str,
    passport: str,
    country: str,
    email: str,
    cin: tuple[int, int, int],
    cout: tuple[int, int, int],
) -> dict:
    y1, m1, d1 = cin
    y2, m2, d2 = cout
    return {
        "first_name": first,
        "last_name": last,
        "date_of_birth": f"{dob}T00:00:00Z",
        "nationality": nationality,
        "id_type": "passport",
        "id_number": passport,
        "id_issuing_country": country,
        "id_expiry_date": "2031-12-31T00:00:00Z",
        "address_line1": "Seedstraße 12" if country == "Germany" else "Fjordveien 8",
        "city": "Munich" if country == "Germany" else ("Oslo" if country == "Norway" else "Zagreb"),
        "postal_code": "80331" if country == "Germany" else "10001",
        "country": country,
        "arrival_date": iso_date(y1, m1, d1),
        "departure_date": checkout_iso(y2, m2, d2),
        "email": email,
        "phone": "+49 170 000 0001" if country == "Germany" else "+47 400 000 01",
    }


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)
    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text[:300]}", file=sys.stderr)
        return 1
    token = r.json()["session_token"]
    h = {"X-Session-Token": token, "Content-Type": "application/json"}

    listed = c.get("/v1/guest-groups/host", headers=h)
    if listed.status_code != 200:
        print(f"List failed: {listed.status_code}", file=sys.stderr)
        return 1

    for g in listed.json():
        gid = g["id"]
        name = g.get("group_name") or ""
        if name.startswith(PREFIX) or name == "Ben Scenario Family 2026":
            dr = c.delete(f"/v1/guest-groups/{gid}", headers=h)
            print(f"Removed old: {name} ({dr.status_code})")

    created_ids: list[str] = []
    for spec in GROUPS:
        r = c.post("/v1/guest-groups/", headers=h, json=spec["group"])
        if r.status_code not in (200, 201):
            print(f"Create failed {spec['group']['group_name']}: {r.status_code} {r.text[:400]}", file=sys.stderr)
            return 1
        body = r.json()
        gid = body["id"]
        created_ids.append(gid)
        code = body.get("access_code")
        if not code:
            rr = c.post(f"/v1/guest-groups/{gid}/regenerate-code", headers=h, json={})
            code = rr.json().get("code") if rr.status_code == 200 else "?"
        print(f"Created: {body['group_name']} | code={code} | {body.get('check_in_date','')[:10]} → {body.get('check_out_date','')[:10]}")

        for pref in spec["preferences"]:
            pr = c.post(f"/v1/guest-groups/access/{code}/preferences", json=pref)
            if pr.status_code not in (200, 201):
                print(f"  pref {pref['guest_name']}: {pr.status_code}", file=sys.stderr)

        cin, cout = spec["check_in"], spec["check_out"]
        for ev in spec["evisitor"]:
            payload = evisitor_row(gid, *ev, cin=cin, cout=cout)
            er = c.post(f"/v1/guest-groups/{gid}/evisitor-data", headers=h, json=payload)
            if er.status_code not in (200, 201):
                print(f"  evisitor {ev[0]}: {er.status_code} {er.text[:120]}", file=sys.stderr)
            else:
                eid = er.json().get("id")
                c.post(
                    f"/v1/guest-groups/{gid}/evisitor-data/{eid}/register",
                    headers=h,
                    json={"confirmation_number": f"EV-{gid[:8].upper()}-{ev[0][:3].upper()}"},
                )

        ur = c.put(
            f"/v1/guest-groups/{gid}",
            headers=h,
            json={
                "group_name": spec["group"]["group_name"],
                "feedback_notes": (
                    f"Demo group for Ben Test dashboard — seeded {datetime.now(timezone.utc).date().isoformat()}. "
                    "Guests expect personalized Lovran/Kvarner tips."
                ),
            },
        )
        if ur.status_code not in (200, 201):
            print(f"  update notes: {ur.status_code}", file=sys.stderr)

    listed2 = c.get("/v1/guest-groups/host", headers=h)
    n = len([g for g in listed2.json() if (g.get("group_name") or "").startswith(PREFIX)])
    print(f"\nDone. Ben Test groups on account: {n}")
    return 0 if n >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
