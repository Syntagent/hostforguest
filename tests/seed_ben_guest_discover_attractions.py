#!/usr/bin/env python3
"""Add guest-friendly Lovran attractions for Ben Test host and refresh guest recommendations."""

from __future__ import annotations

import os
import sys
import uuid

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
EMAIL = os.getenv("BEN_TEST_EMAIL", "benediktperak@gmail.com")
PASSWORD = os.getenv("BEN_TEST_PASSWORD", "Ben@Host1")
ACCESS = os.getenv("BEN_GUEST_ACCESS_CODE", "VHF89RMP")

ATTRACTIONS = [
    {
        "name": "Lovran Lungomare Walk",
        "description": "Easy seaside promenade from Lovran to Ičići — perfect for families and evening strolls.",
        "attraction_type": "nature",
        "city": "Lovran",
        "address": "Lungomare, Lovran",
        "region": "Kvarner",
        "county": "Primorsko-goranska",
        "latitude": 45.273,
        "longitude": 14.275,
        "category_tags": ["nature", "coastal_walks"],
        "host_personal_tip": "Go at sunset; stop for gelato at the harbour before you walk toward Ičići.",
        "host_favorite_time": "18:00–20:00",
        "host_insider_info": "Flat path — fine for strollers and Baka Mira's pace.",
        "difficulty_level": "easy",
        "seasonal_availability": "year_round",
    },
    {
        "name": "Villa Oprić Cherry Garden",
        "description": "Terraced garden behind the villa — quiet morning coffee spot with sea glimpses.",
        "attraction_type": "cultural",
        "city": "Lovran",
        "address": "Oprić 71, Lovran",
        "region": "Kvarner",
        "county": "Primorsko-goranska",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "category_tags": ["cultural", "relaxation"],
        "host_personal_tip": "Pick cherries in June; in July–August it's shaded and ideal before the beach.",
        "host_favorite_time": "08:00–10:00",
        "host_insider_info": "Guests can take breakfast trays outside — ask us for cushions.",
        "difficulty_level": "easy",
        "seasonal_availability": "year_round",
    },
    {
        "name": "Opatija Riviera Day Trip",
        "description": "Historic villas, cafés, and the famous coastal walk toward Volosko.",
        "attraction_type": "cultural",
        "city": "Opatija",
        "address": "Slatina, Opatija",
        "region": "Kvarner",
        "county": "Primorsko-goranska",
        "latitude": 45.335,
        "longitude": 14.305,
        "category_tags": ["culture", "food"],
        "host_personal_tip": "Take the bus from Lovran (20 min) — we can mark the best café for seniors on the map.",
        "host_favorite_time": "10:00–14:00",
        "host_insider_info": "Helga & Wolfgang love the Kaiserpromenade benches.",
        "difficulty_level": "easy",
        "seasonal_availability": "year_round",
    },
    {
        "name": "Učka Nature Park Viewpoint",
        "description": "Short drive to Vojak — panoramic views over Kvarner bay (best on clear mornings).",
        "attraction_type": "nature",
        "city": "Lovran",
        "address": "Učka, Lovran",
        "region": "Kvarner",
        "county": "Primorsko-goranska",
        "latitude": 45.285,
        "longitude": 14.201,
        "category_tags": ["nature", "adventure"],
        "host_personal_tip": "Marko loves it — bring a light jacket even in summer.",
        "host_favorite_time": "09:00–11:00",
        "host_insider_info": "Not ideal for limited mobility; flat bay views from Lovran are the alternative.",
        "difficulty_level": "moderate",
        "seasonal_availability": "year_round",
    },
]


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0)
    login = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    if login.status_code != 200:
        print(f"Login failed: {login.text[:200]}", file=sys.stderr)
        return 1
    h = {"X-Session-Token": login.json()["session_token"], "Content-Type": "application/json"}

    group = c.get(f"/v1/guest-groups/access/{ACCESS}", headers=h)
    if group.status_code != 200:
        print(f"Access code invalid: {ACCESS}", file=sys.stderr)
        return 1
    gid = group.json()["id"]

    for att in ATTRACTIONS:
        body = {**att, "description": att["description"]}
        r = c.post("/v1/attractions/", headers=h, json=body)
        print(f"Attraction {att['name']}: {r.status_code}")

    rec = c.post(
        "/v1/recommendations/host/generate",
        headers=h,
        json={"guest_group_id": gid, "max_recommendations": 12},
    )
    print(f"Regenerate recommendations: {rec.status_code}")

    guest = c.post(f"/v1/recommendations/guest/{ACCESS}", json={})
    if guest.status_code == 200:
        data = guest.json()
        recs = data.get("recommendations", [])
        print(f"Guest sees {len(recs)} places")
        for r in recs[:5]:
            print(f"  - {r.get('attraction', {}).get('name', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
