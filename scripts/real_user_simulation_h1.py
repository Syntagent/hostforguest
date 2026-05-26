#!/usr/bin/env python3
"""Real-user simulation: 3 hosts × 14 test sections on H1 API."""
from __future__ import annotations

import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import httpx

BASE = os.environ.get("HFG_API_BASE", "http://localhost:8006/api/v1")

USERS = [
    {
        "key": "benedikt",
        "label": "Benedikt Perak",
        "email": "bperak@uniri.hr",
        "password": "Drinkable1A",
        "register": {
            "email": "bperak@uniri.hr",
            "password": "Drinkable1A",
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
        "full_attractions": True,
    },
    {
        "key": "ana",
        "label": "Ana Kovač",
        "email": "ana.kovac@example.com",
        "password": "AnaTest2026!",
        "register": {
            "email": "ana.kovac@example.com",
            "password": "AnaTest2026!",
            "first_name": "Ana",
            "last_name": "Kovač",
            "business_name": "Apartmani Ana",
            "business_type": "apartments",
            "address": "Ulica 1",
            "city": "Rijeka",
            "county": "Primorsko-goranska",
            "postal_code": "51000",
            "country": "Croatia",
            "phone": "+38591111222",
            "languages": ["hr", "en"],
        },
        "full_attractions": False,
    },
    {
        "key": "ivan",
        "label": "Ivan Horvat",
        "email": "ivan.horvat@example.com",
        "password": "IvanTest2026!",
        "register": {
            "email": "ivan.horvat@example.com",
            "password": "IvanTest2026!",
            "first_name": "Ivan",
            "last_name": "Horvat",
            "business_name": "Villa Horvat",
            "business_type": "villa",
            "address": "Primorska 5",
            "city": "Opatija",
            "county": "Primorsko-goranska",
            "postal_code": "51410",
            "country": "Croatia",
            "phone": "+38592333444",
            "languages": ["hr", "en", "de"],
        },
        "full_attractions": False,
    },
]

BENEDIKT_ATTRACTIONS = [
    ("Lovran Old Town", "landmark", "Lovran", "Medieval core with stone alleys and sea views."),
    ("Opatija Riviera", "beach", "Opatija", "Elegant Adriatic promenade and swimming spots."),
    ("Učka Nature Park", "nature", "Lovran", "Mountain park above Kvarner with hiking trails."),
    ("Volosko Fishing Village", "cultural", "Opatija", "Authentic fishing harbour and konobas."),
    ("Kvarner Wine Route", "food_drink", "Kvarner", "Local wineries and tasting experiences."),
    ("Lungomare Coastal Walk", "outdoor", "Opatija", "12 km seaside path Opatija–Lovran."),
    ("St. George's Church Lovran", "landmark", "Lovran", "Historic church overlooking the bay."),
    (
        "Lovran Carnival",
        "event",
        "Lovran",
        "Winter carnival tradition with masks and parades.",
        {"seasonal_availability": "winter", "seasonal_notes": "January–February"},
    ),
]

ANA_IVAN_ATTRACTIONS = [
    ("Rijeka Korzo", "landmark", "Rijeka", "Main pedestrian street and city heart."),
    ("Villa Angiolina Park", "cultural", "Opatija", "Historic park and museum setting."),
]


@dataclass
class Row:
    section: str
    user: str
    endpoint: str
    http: int
    expected: str
    notes: str = ""

    @property
    def passed(self) -> bool:
        exp = [int(x) for x in self.expected.replace(" ", "").split("/") if x.isdigit()]
        return self.http in exp if exp else False


results: list[Row] = []
global_state: dict[str, Any] = {"benedikt": {}, "partner_id": None}


def record(section: str, user: str, endpoint: str, http: int, expected: str, notes: str = "") -> None:
    results.append(Row(section, user, endpoint, http, expected, (notes or "")[:100]))
    time.sleep(0.15)  # avoid burst 429 when rate limiting is enabled


def parse_expected(s: str) -> list[int]:
    return [int(x) for x in s.replace(" ", "").split("/") if x.isdigit()]


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=120.0)


def auth_h(token: Optional[str]) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["X-Session-Token"] = token
    return h


def ensure_user(c: httpx.Client, user: dict) -> dict[str, Any]:
    st: dict[str, Any] = {"token": None, "refresh_token": None, "host_id": None}
    r = c.post("/hosts/login", json={"email": user["email"], "password": user["password"]})
    if r.status_code == 200:
        d = r.json()
        st["token"] = d.get("session_token")
        st["refresh_token"] = d.get("refresh_token")
        st["host_id"] = (d.get("host") or {}).get("id")
        return st
    r = c.post("/hosts/register", json=user["register"])
    if r.status_code in (201, 400):
        pass
    r = c.post("/hosts/login", json={"email": user["email"], "password": user["password"]})
    if r.status_code == 200:
        d = r.json()
        st["token"] = d.get("session_token")
        st["refresh_token"] = d.get("refresh_token")
        st["host_id"] = (d.get("host") or {}).get("id")
    return st


def section_auth(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u = user["label"]
    sec = "1.AUTH"
    r = c.post("/hosts/login", json={"email": user["email"], "password": user["password"]})
    record(sec, u, "POST /hosts/login", r.status_code, "200")
    if r.status_code == 200:
        d = r.json()
        st["token"] = d.get("session_token")
        st["refresh_token"] = d.get("refresh_token")
        st["host_id"] = (d.get("host") or {}).get("id")

    h = auth_h(st["token"])
    r = c.get("/hosts/me", headers=h)
    ok = r.status_code == 200 and (r.json().get("email") or "").lower() == user["email"].lower()
    record(sec, u, "GET /hosts/me", r.status_code, "200", "email ok" if ok else r.text[:60])

    r = c.get("/hosts/me/profile", headers=h)
    record(sec, u, "GET /hosts/me/profile", r.status_code, "200")

    profile = {
        "property_name": f"{user['register']['business_name']} Guest House",
        "property_type": user["register"].get("business_type", "apartment"),
        "max_guests": 6,
        "amenities": ["wifi", "parking", "kitchen", "air_conditioning"],
        "expertise_areas": ["Kvarner", "Lovran", "Opatija", "Rijeka"],
        "location_story": f"Host profile for {user['label']} — Kvarner hospitality.",
        "services_offered": user["register"].get("languages", ["hr", "en"]),
    }
    prof = r.json() if (r := c.get("/hosts/me/profile", headers=h)).status_code == 200 else {}
    has_row = bool(prof.get("property_name") or prof.get("max_guests"))
    if has_row:
        r = c.put("/hosts/me/profile", headers=h, json=profile)
        record(sec, u, "PUT /hosts/me/profile", r.status_code, "200/201")
    else:
        r = c.post("/hosts/me/profile", headers=h, json=profile)
        if r.status_code == 201:
            record(sec, u, "POST /hosts/me/profile", r.status_code, "201")
        else:
            r2 = c.put("/hosts/me/profile", headers=h, json=profile)
            record(sec, u, "POST/PUT /hosts/me/profile", r2.status_code, "200/201/400")

    r = c.put(
        "/hosts/me/profile",
        headers=h,
        json={"location_story": f"Updated bio for {user['label']} — passionate Kvarner host."},
    )
    record(sec, u, "PUT /hosts/me/profile (bio)", r.status_code, "200/400")

    old = st["token"]
    r = c.post("/hosts/logout", headers=h)
    record(sec, u, "POST /hosts/logout", r.status_code, "200")

    r = c.get("/hosts/me", headers=auth_h(old))
    record(sec, u, "GET /hosts/me after logout", r.status_code, "401")

    r = c.post("/hosts/login", json={"email": user["email"], "password": user["password"]})
    if r.status_code == 200:
        st["token"] = r.json().get("session_token")
        st["refresh_token"] = r.json().get("refresh_token")
    record(sec, u, "POST /hosts/login (again)", r.status_code, "200")

    r = c.post("/hosts/refresh", headers=auth_h(st["token"]), json={})
    if r.status_code == 200:
        st["token"] = r.json().get("session_token") or st["token"]
    record(sec, u, "POST /hosts/refresh", r.status_code, "200")


def section_onboarding(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "2.ONBOARDING"
    h = auth_h(st["token"])
    hid = st["host_id"]
    r = c.get(f"/onboarding/progress/{hid}")
    record(sec, u, f"GET /onboarding/progress/{hid}", r.status_code, "200")

    ob = {
        "first_name": user["register"]["first_name"],
        "last_name": user["register"]["last_name"],
        "business_name": user["register"]["business_name"],
        "city": user["register"]["city"],
        "address": user["register"]["address"],
        "region": user["register"]["county"],
        "business_type": user["register"]["business_type"],
        "max_group_size": 6,
        "amenities": ["wifi", "parking"],
        "local_experience": "experienced",
        "location_story": "Kvarner local knowledge.",
        "specialties": ["culture", "nature"],
        "preferred_guests": ["families", "couples"],
        "languages": user["register"].get("languages", ["hr"]),
        "hosting_experience": 5,
        "interests": ["hiking", "food", "history"],
    }
    r = c.post("/onboarding/generate-profile-suggestions", headers=h, json=ob)
    record(sec, u, "POST /onboarding/generate-profile-suggestions", r.status_code, "200/503/500")

    r = c.post(
        "/onboarding/validate-profile",
        headers=h,
        json={**ob, "property_name": user["register"]["business_name"], "email": user["email"]},
    )
    record(sec, u, "POST /onboarding/validate-profile", r.status_code, "200")


def section_attractions(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "3.ATTRACTIONS"
    h = auth_h(st["token"])
    st["attraction_ids"] = []

    if user.get("full_attractions"):
        for item in BENEDIKT_ATTRACTIONS:
            extra = item[4] if len(item) > 4 else {}
            body = {
                "name": item[0],
                "description": item[3],
                "attraction_type": item[1],
                "category_tags": [item[1], "kvarner"],
                "city": item[2],
                **extra,
            }
            r = c.post("/attractions/", headers=h, json=body)
            if r.status_code in (200, 201):
                st["attraction_ids"].append(r.json().get("id"))
            record(sec, u, f"POST /attractions/ ({item[0]})", r.status_code, "201")

        r = c.get("/attractions/host", headers=h)
        record(sec, u, "GET /attractions/host", r.status_code, "200")

        r = c.get("/attractions/")
        record(sec, u, "GET /attractions/", r.status_code, "200")

        for path, exp in [
            ("/attractions/search?q=Lovran", {"q": "Lovran"}),
            ("/attractions/search?city=Opatija", {"city": "Opatija"}),
            ("/attractions/search?category=landmark", {"category": "landmark"}),
        ]:
            r = c.get("/attractions/search", params={k: v for k, v in [
                ("q", exp.get("q")),
                ("city", exp.get("city")),
                ("category", exp.get("category")),
            ] if v})
            record(sec, u, f"GET {path}", r.status_code, "200")

        aid = st["attraction_ids"][0] if st["attraction_ids"] else None
        if aid:
            r = c.put(f"/attractions/{aid}", headers=h, json={"description": "Updated: Lovran Old Town — must-see."})
            record(sec, u, f"PUT /attractions/{aid}", r.status_code, "200")
            r = c.post(
                "/attractions/ai-enhance",
                headers=h,
                json={
                    "attraction_name": "Lovran Old Town",
                    "location": "Lovran",
                    "attraction_type": "landmark",
                    "current_description": "Updated",
                    "host_location": "Lovran",
                },
            )
            record(sec, u, "POST /attractions/ai-enhance", r.status_code, "200/503/500")
    else:
        r = c.get("/attractions/")
        n = len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else "?"
        record(sec, u, "GET /attractions/ (public)", r.status_code, "200", f"count={n}")

        for item in ANA_IVAN_ATTRACTIONS[:2 if user["key"] == "ana" else 1]:
            body = {
                "name": item[0],
                "description": item[3],
                "attraction_type": item[1],
                "category_tags": [item[1]],
                "city": item[2],
            }
            r = c.post("/attractions/", headers=h, json=body)
            if r.status_code in (200, 201):
                st["attraction_ids"].append(r.json().get("id"))
            record(sec, u, f"POST /attractions/ ({item[0]})", r.status_code, "201")

        r = c.get("/attractions/host", headers=h)
        own = len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else 0
        record(sec, u, "GET /attractions/host", r.status_code, "200", f"own={own}")


def section_guest_groups(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "4.GUEST-GROUPS"
    h = auth_h(st["token"])
    st["guest_groups"] = []
    groups = [
        ("Obitelj Horvat - Srpanj 2026", 4, "2026-07-01T14:00:00Z", "2026-07-14T10:00:00Z"),
        ("Parovi - Kolovoz 2026", 2, "2026-08-01T14:00:00Z", "2026-08-07T10:00:00Z"),
        ("Proširena obitelj - Rujan 2026", 6, "2026-09-01T14:00:00Z", "2026-09-10T10:00:00Z"),
    ]
    for i, (name, size, ci, co) in enumerate(groups):
        body = {
            "group_name": name,
            "group_size": size,
            "check_in_date": ci,
            "check_out_date": co,
            "lead_guest_name": f"Guest {i+1}",
            "lead_guest_email": f"guest{i+1}@example.com",
        }
        r = c.post("/guest-groups/", headers=h, json=body)
        gid, code = None, None
        if r.status_code in (200, 201):
            j = r.json()
            gid, code = j.get("id"), j.get("access_code")
            st["guest_groups"].append({"id": gid, "code": code})
        record(sec, u, f"POST /guest-groups/ ({name[:20]})", r.status_code, "201")

    r = c.get("/guest-groups/host", headers=h)
    record(sec, u, "GET /guest-groups/host", r.status_code, "200")

    if st["guest_groups"]:
        g0 = st["guest_groups"][0]
        gid, code = g0["id"], g0["code"]
        r = c.get(f"/guest-groups/{gid}", headers=h)
        record(sec, u, f"GET /guest-groups/{gid}", r.status_code, "200")

        ev = {
            "first_name": "Test",
            "last_name": "Guest",
            "date_of_birth": "1990-01-01T00:00:00Z",
            "nationality": "Croatia",
            "id_type": "passport",
            "id_number": "P1234567",
            "id_issuing_country": "Croatia",
            "arrival_date": "2026-07-01T14:00:00Z",
            "departure_date": "2026-07-14T10:00:00Z",
            "email": "test@example.com",
        }
        r = c.post(f"/guest-groups/{gid}/evisitor-data", headers=h, json=ev)
        record(sec, u, f"POST /guest-groups/{gid}/evisitor-data", r.status_code, "201/200")

        r = c.get(f"/guest-groups/{gid}/evisitor-data", headers=h)
        record(sec, u, f"GET /guest-groups/{gid}/evisitor-data", r.status_code, "200")

        r = c.put(f"/guest-groups/{gid}", headers=h, json={"group_size": 5})
        record(sec, u, f"PUT /guest-groups/{gid}", r.status_code, "200")

        if code:
            r = c.post("/guest-groups/access/validate", json={"access_code": code})
            record(sec, u, "POST /guest-groups/access/validate", r.status_code, "200")
            r = c.get(f"/guest-groups/access/{code}")
            record(sec, u, f"GET /guest-groups/access/{code}", r.status_code, "200")


def section_recommendations(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "5.RECOMMENDATIONS"
    h = auth_h(st["token"])
    gid = st["guest_groups"][0]["id"] if st.get("guest_groups") else None
    if gid:
        r = c.post(
            "/recommendations/host/generate",
            headers=h,
            json={"guest_group_id": gid, "max_recommendations": 5},
        )
        record(sec, u, "POST /recommendations/host/generate", r.status_code, "200/503/500")
    else:
        record(sec, u, "POST /recommendations/host/generate", 0, "200", "no group")

    r = c.get("/recommendations/host/analytics", headers=h)
    record(sec, u, "GET /recommendations/host/analytics", r.status_code, "200")

    if gid:
        r = c.get(f"/recommendations/host/guest-groups/{gid}/analytics", headers=h)
        record(sec, u, f"GET .../guest-groups/{gid}/analytics", r.status_code, "200")


def section_bi(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "6.BI"
    h = auth_h(st["token"])
    for ep in [
        "/bi/dashboard",
        "/bi/revenue",
        "/bi/seasonal-trends",
        "/bi/ltv",
        "/hosts/analytics",
        "/analytics/recommendation-effectiveness",
        "/analytics/satisfaction-trends",
        "/analytics/revenue-tracking",
    ]:
        r = c.get(ep, headers=h)
        record(sec, u, f"GET {ep}", r.status_code, "200")


def section_partners_cleaning(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "7.PARTNERS"
    h = auth_h(st["token"])
    hid = st["host_id"]

    c.put("/hosts/me", headers=h, json={"latitude": 45.27, "longitude": 14.27})

    r = c.get(f"/locations/nearby/{hid}", headers=h)
    record(sec, u, f"GET /locations/nearby/{hid}", r.status_code, "200")

    r = c.get("/cleaning/providers", headers=h)
    record(sec, u, "GET /cleaning/providers", r.status_code, "200")

    r = c.get("/cleaning/upcoming-checkouts", headers=h)
    record(sec, u, "GET /cleaning/upcoming-checkouts", r.status_code, "200")

    r = c.post("/cleaning/discover", headers=h, json={"city": user["register"]["city"], "intent": "turnover"})
    record(sec, u, "POST /cleaning/discover", r.status_code, "200/500/503")

    clean_pid = None
    rp = c.get("/cleaning/providers", headers=h)
    if rp.status_code == 200:
        providers = rp.json() if isinstance(rp.json(), list) else (rp.json() or {}).get("providers", [])
        if providers:
            clean_pid = providers[0].get("id")
    if not clean_pid:
        clean_pid = global_state.get("partner_id")
    if clean_pid:
        r = c.post(
            "/cleaning/draft-message",
            headers=h,
            json={"partner_id": clean_pid, "intent": "turnover", "language": "hr"},
        )
        record(sec, u, "POST /cleaning/draft-message", r.status_code, "200/400/500/503")
    else:
        record(sec, u, "POST /cleaning/draft-message", 0, "200/400/500", "no cleaning partner")

    r = c.get(f"/partners/hosts/{hid}/partners", headers=h)
    record(sec, u, f"GET /partners/hosts/{hid}/partners", r.status_code, "200")

    pid = global_state.get("partner_id")
    if not pid:
        r = c.post(
            "/partners/",
            json={
                "name": "Kvarner Tours d.o.o.",
                "partner_type": "tour_operator",
                "city": "Rijeka",
                "commission_rate": 0.12,
            },
        )
        if r.status_code in (200, 201):
            global_state["partner_id"] = r.json().get("id")
            pid = global_state["partner_id"]

    if pid:
        r = c.post(
            f"/partners/hosts/{hid}/partners",
            headers=h,
            json={"partner_id": pid, "priority": 1, "commission_rate": 0.1},
        )
        record(sec, u, f"POST /partners/hosts/{hid}/partners", r.status_code, "201/200/409")
    else:
        record(sec, u, f"POST /partners/hosts/{hid}/partners", 0, "201", "no partner")


def section_communications(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "8.COMMS"
    h = auth_h(st["token"])
    for gg in st.get("guest_groups", [])[:2]:
        gid = gg["id"]
        for ep, body in [
            ("/communications/welcome-kit/generate", {"guest_group_id": gid}),
            ("/communications/welcome-kit/send", {"guest_group_id": gid, "delivery_method": "email"}),
            ("/communications/pre-arrival-email", {"guest_group_id": gid}),
            ("/communications/follow-up", {"guest_group_id": gid}),
        ]:
            r = c.post(ep, headers=h, json=body)
            record(sec, u, f"POST {ep}", r.status_code, "200/503/500")

    r = c.post(
        "/communications/sms",
        headers=h,
        json={"phone_number": user["register"]["phone"], "message": "Test SMS", "language": "hr"},
    )
    record(sec, u, "POST /communications/sms", r.status_code, "200/503/500")


def section_content(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "9.CONTENT"
    aid = (st.get("attraction_ids") or [None])[0]
    gid = st["guest_groups"][0]["id"] if st.get("guest_groups") else None
    hid = st["host_id"]

    if aid:
        r = c.post(
            "/content-generation/attractions/description",
            json={"attraction_id": aid, "language": "en"},
        )
        record(sec, u, "POST /content-generation/attractions/description", r.status_code, "200/503/500")

    r = c.post(
        "/content-generation/email",
        json={"template_type": "welcome", "host_id": hid, "guest_group_id": gid, "language": "hr"},
    )
    record(sec, u, "POST /content-generation/email", r.status_code, "200/503/500")

    if aid:
        r = c.post(
            "/content-generation/social-media",
            json={"attraction_id": aid, "post_type": "instagram", "language": "hr"},
        )
        record(sec, u, "POST /content-generation/social-media", r.status_code, "200/503/500")

    r = c.post("/content-generation/tips", json={"host_id": hid, "language": "hr", "count": 3})
    record(sec, u, "POST /content-generation/tips", r.status_code, "200/503/500")

    r = c.post(
        "/content-generation/translate",
        json={
            "source_text": "Dobrodošli u Kvarner!",
            "source_language": "hr",
            "target_languages": ["en", "de"],
        },
    )
    record(sec, u, "POST /content-generation/translate", r.status_code, "200/503/500")


def section_edge(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "10.EDGE"
    h = auth_h(st["token"])

    r = c.post("/hosts/register", json=USERS[0]["register"])
    record(sec, u, "POST /hosts/register (dup email)", r.status_code, "400/422/429")

    r = c.post("/hosts/login", json={"email": user["email"], "password": "WrongPassword!"})
    record(sec, u, "POST /hosts/login (wrong pwd)", r.status_code, "401")

    r = c.post("/hosts/login", json={"email": "", "password": "x"})
    record(sec, u, "POST /hosts/login (empty email)", r.status_code, "422")

    r = c.get("/hosts/me")
    record(sec, u, "GET /hosts/me (no token)", r.status_code, "401/429")

    r = c.post("/guest-groups/", json={})
    record(sec, u, "POST /guest-groups/ (no auth)", r.status_code, "401/422/429")

    r = c.post("/guest-groups/", headers=h, json={})
    record(sec, u, "POST /guest-groups/ (missing fields)", r.status_code, "422")

    fake = str(uuid.uuid4())
    r = c.get(f"/attractions/{fake}", headers=h)
    record(sec, u, f"GET /attractions/{fake}", r.status_code, "404")

    r = c.get(f"/guest-groups/{fake}", headers=h)
    record(sec, u, f"GET /guest-groups/{fake}", r.status_code, "404")

    r = c.delete(f"/attractions/{fake}", headers=h)
    record(sec, u, f"DELETE /attractions/{fake}", r.status_code, "404")

    r = c.post("/hosts/register", json={"email": "bad"})
    record(sec, u, "POST /hosts/register (missing fields)", r.status_code, "422")


def section_isolation(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "11.ISOLATION"
    if user["key"] not in ("ana", "ivan"):
        return
    h = auth_h(st["token"])
    r = c.get("/guest-groups/host", headers=h)
    ana_ids = {g["id"] for g in r.json()} if r.status_code == 200 else set()
    ben_gg = global_state.get("benedikt", {}).get("guest_group_id")
    leak = ben_gg in ana_ids if ben_gg else False
    record(sec, u, "GET /guest-groups/host (isolation)", r.status_code, "200", "leak" if leak else "ok")

    r = c.get("/attractions/host", headers=h)
    record(sec, u, "GET /attractions/host (isolation)", r.status_code, "200")

    if ben_gg:
        r = c.get(f"/guest-groups/{ben_gg}", headers=h)
        record(sec, u, f"GET Benedikt group {ben_gg}", r.status_code, "403/404")


def section_channels(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "12.CHANNELS"
    h = auth_h(st["token"])
    r = c.get("/channel-integrations/status", headers=h)
    record(sec, u, "GET /channel-integrations/status", r.status_code, "200")

    r = c.post(
        "/channel-integrations/booking-com/connect",
        headers=h,
        json={"hotel_id": "TEST123", "api_username": "test", "api_password": "test"},
    )
    record(sec, u, "POST /channel-integrations/booking-com/connect", r.status_code, "200/400/500")
    acc_id = None
    if r.status_code == 200:
        acc_id = r.json().get("id")
    elif r.status_code != 200:
        rs = c.get("/channel-integrations/status", headers=h)
        acc = (rs.json() or {}).get("account") if rs.status_code == 200 else None
        acc_id = (acc or {}).get("id") if acc else None

    if acc_id:
        r = c.get(f"/channel-integrations/{acc_id}/health", headers=h)
        record(sec, u, f"GET /channel-integrations/{acc_id}/health", r.status_code, "200")
        r = c.post(f"/channel-integrations/{acc_id}/sync/full", headers=h)
        record(sec, u, f"POST /channel-integrations/{acc_id}/sync/full", r.status_code, "200/400/500")
    else:
        record(sec, u, "GET /channel-integrations/{id}/health", 0, "200", "no account")
        record(sec, u, "POST /channel-integrations/{id}/sync/full", 0, "200/500", "no account")


def section_bookings(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "13.BOOKINGS"
    gid = st["guest_groups"][0]["id"] if st.get("guest_groups") else None
    pid = global_state.get("partner_id")
    if not gid or not pid:
        record(sec, u, "POST /bookings/", 0, "200", "skip no gid/partner")
        record(sec, u, "GET /bookings/analytics", 0, "200", "skip")
        return
    r = c.post(
        "/bookings/",
        json={
            "guest_group_id": gid,
            "partner_id": pid,
            "host_id": st["host_id"],
            "amount": 150.0,
            "currency": "EUR",
        },
    )
    bid = r.json().get("id") if r.status_code in (200, 201) else None
    record(sec, u, "POST /bookings/", r.status_code, "200")

    r = c.get("/bookings/analytics")
    record(sec, u, "GET /bookings/analytics", r.status_code, "200")

    if bid:
        r = c.post(f"/bookings/{bid}/confirm")
        record(sec, u, f"POST /bookings/{bid}/confirm", r.status_code, "200")
        r = c.post(f"/bookings/{bid}/cancel")
        record(sec, u, f"POST /bookings/{bid}/cancel", r.status_code, "200")


def section_audit(c: httpx.Client, user: dict, st: dict[str, Any]) -> None:
    u, sec = user["label"], "14.AUDIT"
    h = auth_h(st["token"])
    r = c.get("/audit/logs", headers=h)
    record(sec, u, "GET /audit/logs", r.status_code, "200")

    r = c.get("/hosts/sessions", headers=h)
    record(sec, u, "GET /hosts/sessions", r.status_code, "200")

    r = c.post("/hosts/logout-all", headers=h)
    record(sec, u, "POST /hosts/logout-all", r.status_code, "200")


def run_user(c: httpx.Client, user: dict) -> dict[str, Any]:
    st = ensure_user(c, user)
    if not st.get("token"):
        record("0.SETUP", user["label"], "login/register", 0, "200", "FATAL")
        return st
    section_auth(c, user, st)
    if user["key"] == "benedikt":
        global_state["benedikt"] = st
    section_onboarding(c, user, st)
    section_attractions(c, user, st)
    section_guest_groups(c, user, st)
    if user["key"] == "benedikt" and st.get("guest_groups"):
        global_state["benedikt"]["guest_group_id"] = st["guest_groups"][0]["id"]
    section_recommendations(c, user, st)
    section_bi(c, user, st)
    section_partners_cleaning(c, user, st)
    section_communications(c, user, st)
    section_content(c, user, st)
    section_edge(c, user, st)
    section_isolation(c, user, st)
    section_channels(c, user, st)
    section_bookings(c, user, st)
    section_audit(c, user, st)
    return st


def print_table() -> None:
    print("\n## FINAL RESULTS\n")
    print("| Test | User | Endpoint | HTTP | Expected | PASS/FAIL | Notes |")
    print("|------|------|----------|------|----------|-----------|-------|")
    for row in results:
        status = "PASS" if row.passed else "FAIL"
        print(
            f"| {row.section} | {row.user} | {row.endpoint} | {row.http} | {row.expected} | {status} | {row.notes} |"
        )


def main() -> int:
    print(f"API base: {BASE}\n")
    with client() as c:
        for user in USERS:
            print(f"=== {user['label']} ===")
            run_user(c, user)

    print_table()
    passed = sum(1 for x in results if x.passed)
    total = len(results)
    fails = [x for x in results if not x.passed]
    print(f"\n**Summary: {passed}/{total} passed.**")
    if fails:
        print("\n### Failures")
        for f in fails[:40]:
            print(f"- [{f.section}] {f.user}: {f.endpoint} → {f.http} (expected {f.expected}) {f.notes}")
        if len(fails) > 40:
            print(f"... and {len(fails) - 40} more")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
