#!/usr/bin/env python3
"""
Ben Test: exercise every host dashboard component via API (read + write).

Usage:
  python tests/ben_host_full_components.py
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
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
state: dict = {}


def record(component: str, action: str, http: int, expected: str, notes: str = "") -> None:
    rows.append(Row(component, action, http, expected, notes[:180]))


def h() -> dict[str, str]:
    out = {"Content-Type": "application/json"}
    if state.get("token"):
        out["X-Session-Token"] = state["token"]
    return out


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)
    tag = uuid.uuid4().hex[:6]

    r = c.post("/v1/hosts/login", json={"email": EMAIL, "password": PASSWORD})
    record("Auth", "login", r.status_code, "200")
    if r.status_code != 200:
        print_report()
        return 1
    d = r.json()
    state["token"] = d.get("session_token")
    state["host_id"] = (d.get("host") or {}).get("id")

    # --- Overview ---
    r = c.get("/v1/hosts/analytics", headers=h())
    record("Overview", "analytics", r.status_code, "200")
    r = c.get("/v1/hosts/me", headers=h())
    record("Overview", "hosts/me", r.status_code, "200")

    # --- Stay (accommodation profile) ---
    profile = {
        "property_name": "Villa Oprić 71",
        "property_type": "apartment",
        "max_guests": 6,
        "amenities": ["wifi", "parking", "kitchen"],
        "expertise_areas": ["Lovran", "Opatija", "Kvarner"],
        "location_story": f"Ben Test host — Kvarner hospitality QA {tag}.",
        "services_offered": ["hr", "en"],
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "address": "Oprić 71",
        "latitude": 45.2919,
        "longitude": 14.2742,
    }
    r = c.get("/v1/hosts/me/profile", headers=h())
    record("Stay", "GET profile", r.status_code, "200/404")
    if r.status_code == 200 and (r.json().get("property_name") or r.json().get("max_guests")):
        r = c.put("/v1/hosts/me/profile", headers=h(), json=profile)
        record("Stay", "PUT profile", r.status_code, "200")
    else:
        r = c.post("/v1/hosts/me/profile", headers=h(), json=profile)
        record("Stay", "POST profile", r.status_code, "201/200")
        if r.status_code not in (200, 201):
            r = c.put("/v1/hosts/me/profile", headers=h(), json=profile)
            record("Stay", "PUT profile fallback", r.status_code, "200")

    r = c.put("/v1/hosts/me", headers=h(), json={"latitude": 45.2919, "longitude": 14.2742})
    record("Stay", "PUT hosts/me coords", r.status_code, "200")

    # --- Attractions ---
    r = c.get("/v1/attractions/host", headers=h())
    record("Attractions", "list host", r.status_code, "200")
    ap = {
        "name": f"Ben Component {tag}",
        "description": "Host full-component QA attraction in Lovran.",
        "attraction_type": "cultural",
        "city": "Lovran",
        "address": "Lovran, Croatia",
        "latitude": 45.2733,
        "longitude": 14.2711,
    }
    r = c.post("/v1/attractions/", headers=h(), json=ap)
    record("Attractions", "create", r.status_code, "201")
    aid = r.json().get("id") if r.status_code == 201 else None
    if aid:
        r = c.put(f"/v1/attractions/{aid}/", headers=h(), json={"host_personal_tip": f"Tip {tag}"})
        record("Attractions", "update", r.status_code, "200")
        r = c.get(f"/v1/attractions/{aid}", headers=h())
        record("Attractions", "get one", r.status_code, "200")

    # --- Guests ---
    r = c.get("/v1/guest-groups/host", headers=h())
    record("Guests", "list", r.status_code, "200")
    groups = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
    state["group_id"] = groups[0]["id"] if groups else None
    now = datetime.now(timezone.utc)
    gr = {
        "group_name": f"Ben Host QA {tag}",
        "group_size": 2,
        "check_in_date": now.isoformat(),
        "check_out_date": (now + timedelta(days=5)).isoformat(),
        "lead_guest_name": "QA Lead",
        "lead_guest_email": f"qa.{tag}@example.com",
    }
    r = c.post("/v1/guest-groups/", headers=h(), json=gr)
    record("Guests", "create group", r.status_code, "201/200")
    if r.status_code in (200, 201):
        state["group_id"] = r.json().get("id")
        state["access_code"] = r.json().get("access_code")

    if state.get("group_id"):
        gid = state["group_id"]
        r = c.get(f"/v1/guest-groups/{gid}", headers=h())
        record("Guests", "get group", r.status_code, "200")
        r = c.get(f"/v1/guest-groups/{gid}/guest-experience", headers=h())
        record("Guests", "guest-experience", r.status_code, "200")
        saved = []
        if state.get("access_code"):
            code = state["access_code"]
            r_save = c.post(
                f"/v1/guest-groups/access/{code}/saved-events",
                json={
                    "event_id": f"host-visible-{tag}",
                    "title": f"Host visible saved event {tag}",
                    "source": "qa",
                },
            )
            record("Guests", "guest saves event", r_save.status_code, "200")
            r_host_group = c.get(f"/v1/guest-groups/{gid}", headers=h())
            record("Guests", "host sees saved event payload", r_host_group.status_code, "200")
            if r_host_group.status_code == 200:
                saved = r_host_group.json().get("saved_event_recommendations") or []
                seen = any(str(x.get("event_id")) == f"host-visible-{tag}" for x in saved)
                record("Guests", "saved event visible to host", 200 if seen else 404, "200")
            r_plan = c.put(
                f"/v1/guest-groups/{gid}/saved-events/host-visible-{tag}",
                headers=h(),
                json={"host_status": "planned", "host_note": "QA planned by host"},
            )
            record("Guests", "mark saved event planned", r_plan.status_code, "200")
            if r_plan.status_code == 200:
                planned = any(
                    str(x.get("event_id")) == f"host-visible-{tag}"
                    and x.get("host_status") == "planned"
                    for x in (r_plan.json().get("saved_events") or [])
                )
                record("Guests", "planned status persisted", 200 if planned else 404, "200")
        r2 = c.get("/v1/guest-groups/host", headers=h())
        prefs = []
        if r2.status_code == 200:
            for g in r2.json():
                if str(g.get("id")) == str(gid):
                    prefs = g.get("preferences") or []
                    break
        record("Guests", "preferences on group", r2.status_code, "200", f"count={len(prefs)}")

    # --- Routes ---
    r = c.get("/v1/itineraries/host/templates", headers=h())
    record("Routes", "list templates", r.status_code, "200")
    r = c.get("/v1/itineraries/host/itineraries", headers=h())
    record("Routes", "list itineraries", r.status_code, "200")
    r = c.post(
        "/v1/itineraries/",
        headers=h(),
        json={
            "title": f"Ben Route {tag}",
            "description": "QA route template",
            "base_location": "Lovran, Croatia",
            "is_template": True,
            "pace": "moderate",
            "budget_level": "medium",
        },
    )
    record("Routes", "create template", r.status_code, "201")
    tid = r.json().get("id") if r.status_code == 201 else None
    if tid and state.get("group_id"):
        r = c.post(
            f"/v1/itineraries/templates/{tid}/assign",
            headers=h(),
            json={
                "guest_group_id": state["group_id"],
                "start_date": datetime.now(timezone.utc).date().isoformat(),
            },
        )
        record("Routes", "assign template", r.status_code, "201/400", r.text[:80] if r.status_code >= 400 else "")
        assigned_itinerary_id = r.json().get("id") if r.status_code == 201 else None
        if not assigned_itinerary_id:
            start_date = datetime.now(timezone.utc).date()
            r_direct = c.post(
                f"/v1/itineraries/?guest_group_id={state['group_id']}",
                headers=h(),
                json={
                    "title": f"Ben Direct Route {tag}",
                    "description": "QA guest route for saved event conversion",
                    "base_location": "Lovran, Croatia",
                    "start_date": start_date.isoformat(),
                    "end_date": (start_date + timedelta(days=2)).isoformat(),
                    "is_template": False,
                    "pace": "moderate",
                    "budget_level": "medium",
                },
            )
            record("Routes", "create direct guest itinerary", r_direct.status_code, "201")
            assigned_itinerary_id = r_direct.json().get("id") if r_direct.status_code == 201 else None
        if assigned_itinerary_id and state.get("access_code"):
            day_date = datetime.now(timezone.utc).date().isoformat()
            r_day = c.post(
                f"/v1/itineraries/{assigned_itinerary_id}/day-plans",
                headers=h(),
                json={
                    "day_number": 1,
                    "date": day_date,
                    "title": "Guest event requests",
                    "theme": "Guest-picked events",
                },
            )
            record("Routes", "create day for event request", r_day.status_code, "201")
            day_plan_id = r_day.json().get("id") if r_day.status_code == 201 else None
            if day_plan_id:
                event_id = f"route-convert-{tag}"
                r_save = c.post(
                    f"/v1/guest-groups/access/{state['access_code']}/saved-events",
                    json={
                        "event_id": event_id,
                        "title": f"Route converted event {tag}",
                        "source": "qa",
                    },
                )
                record("Routes", "guest saves event for conversion", r_save.status_code, "200")
                r_intent = c.patch(
                    f"/v1/guest-groups/access/{state['access_code']}/saved-events/{event_id}",
                    json={
                        "guest_action": "preferred_day",
                        "preferred_day_plan_id": day_plan_id,
                        "preferred_day_number": 1,
                        "preferred_day_title": "Guest-picked events",
                    },
                )
                record("Routes", "guest requests event day", r_intent.status_code, "200")
                r_convert = c.post(
                    f"/v1/guest-groups/{state['group_id']}/saved-events/{event_id}/itinerary-activity",
                    headers=h(),
                    json={
                        "day_plan_id": day_plan_id,
                        "scheduled_start_time": "19:30",
                        "estimated_duration": 120,
                    },
                )
                record("Routes", "convert saved event to activity", r_convert.status_code, "200")
                if r_convert.status_code == 200:
                    body = r_convert.json()
                    saved_rows = body.get("saved_events") or []
                    first_activity_id = (body.get("activity") or {}).get("id")
                    converted = any(
                        row.get("event_id") == event_id
                        and row.get("itinerary_activity_id")
                        and "T19:30:00" in str(row.get("itinerary_activity_start_time"))
                        and "T21:30:00" in str(row.get("itinerary_activity_end_time"))
                        for row in saved_rows
                    )
                    record("Routes", "conversion metadata persisted on saved event", 200 if converted else 404, "200")
                    r_retry = c.post(
                        f"/v1/guest-groups/{state['group_id']}/saved-events/{event_id}/itinerary-activity",
                        headers=h(),
                        json={
                            "day_plan_id": day_plan_id,
                            "scheduled_start_time": "20:00",
                            "estimated_duration": 60,
                        },
                    )
                    record("Routes", "retry conversion is idempotent", r_retry.status_code, "200")
                    if r_retry.status_code == 200:
                        retry_body = r_retry.json()
                        same_activity = (
                            retry_body.get("already_added") is True
                            and (retry_body.get("activity") or {}).get("id") == first_activity_id
                        )
                        record("Routes", "retry returns existing activity", 200 if same_activity else 409, "200")
                r_guest_saved = c.get(f"/v1/guest-groups/access/{state['access_code']}/saved-events")
                record("Routes", "guest sees converted saved event", r_guest_saved.status_code, "200")
                if r_guest_saved.status_code == 200:
                    guest_rows = r_guest_saved.json().get("saved_events") or []
                    guest_converted = any(
                        row.get("event_id") == event_id
                        and row.get("itinerary_activity_id")
                        and "T19:30:00" in str(row.get("itinerary_activity_start_time"))
                        for row in guest_rows
                    )
                    record("Routes", "guest conversion metadata visible", 200 if guest_converted else 404, "200")

                host_pick_event_id = f"host-picks-day-{tag}"
                r_save_host_pick = c.post(
                    f"/v1/guest-groups/access/{state['access_code']}/saved-events",
                    json={
                        "event_id": host_pick_event_id,
                        "title": f"Host picks day event {tag}",
                        "source": "qa",
                    },
                )
                record("Routes", "guest saves plan-request event", r_save_host_pick.status_code, "200")
                r_plan_request = c.patch(
                    f"/v1/guest-groups/access/{state['access_code']}/saved-events/{host_pick_event_id}",
                    json={
                        "guest_action": "plan_request",
                        "guest_note": "Please place this wherever it fits.",
                    },
                )
                record("Routes", "guest asks host to pick day", r_plan_request.status_code, "200")
                r_host_pick_convert = c.post(
                    f"/v1/guest-groups/{state['group_id']}/saved-events/{host_pick_event_id}/itinerary-activity",
                    headers=h(),
                    json={
                        "day_plan_id": day_plan_id,
                        "scheduled_start_time": "18:15",
                        "estimated_duration": 75,
                    },
                )
                record("Routes", "host converts plan-request with selected day", r_host_pick_convert.status_code, "200")
                if r_host_pick_convert.status_code == 200:
                    converted_rows = r_host_pick_convert.json().get("saved_events") or []
                    host_selected_day = any(
                        row.get("event_id") == host_pick_event_id
                        and row.get("itinerary_day_plan_id") == day_plan_id
                        and row.get("itinerary_activity_id")
                        and "T18:15:00" in str(row.get("itinerary_activity_start_time"))
                        for row in converted_rows
                    )
                    record("Routes", "host-selected day conversion persisted", 200 if host_selected_day else 404, "200")

    # --- Maintenance ---
    r = c.get("/v1/maintenance/categories", headers=h())
    record("Maintenance", "categories", r.status_code, "200")
    r = c.get("/v1/maintenance/issues", headers=h())
    record("Maintenance", "list issues", r.status_code, "200")
    r = c.post(
        "/v1/maintenance/issues",
        headers=h(),
        json={
            "category": "plumbing",
            "title": f"Ben QA leak {tag}",
            "description": "Automated maintenance issue for host component test.",
        },
    )
    record("Maintenance", "create issue", r.status_code, "201")
    iid = r.json().get("id") if r.status_code == 201 else None
    if iid:
        r = c.post(f"/v1/maintenance/issues/{iid}/suggest-partners", headers=h(), json={})
        record("Maintenance", "suggest partners", r.status_code, "200/503")
    r = c.post(
        "/v1/maintenance/schedules",
        headers=h(),
        json={"title": f"HVAC check {tag}", "category": "hvac", "interval_days": 180},
    )
    record("Maintenance", "create schedule", r.status_code, "201")

    # --- Adaptation ---
    r = c.get("/v1/adaptation/projects", headers=h())
    record("Adaptation", "list projects", r.status_code, "200")
    r = c.post(
        "/v1/adaptation/projects",
        headers=h(),
        json={
            "title": f"Ben Adaptation {tag}",
            "brief": "Refresh guest bathroom — QA project",
            "style_tags": ["modern", "coastal"],
            "budget_band": "medium",
        },
    )
    record("Adaptation", "create project", r.status_code, "201")
    pid = r.json().get("id") if r.status_code == 201 else None
    if pid:
        r = c.post(f"/v1/adaptation/projects/{pid}/analyze", headers=h(), json={})
        record("Adaptation", "analyze", r.status_code, "200/503")

    # --- Channels ---
    r = c.get("/v1/channel-integrations/status", headers=h())
    record("Channels", "status", r.status_code, "200")

    # --- Cleaning ---
    r = c.get("/v1/cleaning/providers", headers=h())
    record("Cleaning", "providers", r.status_code, "200")
    r = c.get("/v1/cleaning/upcoming-checkouts", headers=h())
    record("Cleaning", "upcoming checkouts", r.status_code, "200")
    r = c.post("/v1/cleaning/discover", headers=h(), json={"city": "Lovran", "intent": "turnover"})
    record("Cleaning", "discover", r.status_code, "200/500/503")

    # --- Insights ---
    r = c.get("/v1/recommendations/host/analytics?days=30", headers=h())
    record("Insights", "rec analytics", r.status_code, "200")
    r = c.get("/v1/realtime/updates", headers=h())
    record("Insights", "realtime", r.status_code, "200")
    r = c.get("/v1/realtime/events?city=Lovran&limit=10", headers=h())
    record("Insights", "realtime/events", r.status_code, "200")
    r = c.post("/v1/realtime/events/bootstrap?city=Lovran", headers=h())
    record("Insights", "events bootstrap", r.status_code, "200")
    r = c.get("/v1/attractions/seasonal-events?city=Lovran", headers=h())
    record("Insights", "seasonal-events list", r.status_code, "200")
    if state.get("group_id"):
        r = c.post(
            "/v1/recommendations/host/generate",
            headers=h(),
            json={"guest_group_id": state["group_id"], "max_recommendations": 5},
        )
        record("Insights", "generate recs", r.status_code, "200/503")

    # --- Settings / Account ---
    r = c.get("/v1/settings/", headers=h())
    record("Account", "GET settings", r.status_code, "200")
    r = c.get("/v1/hosts/sessions", headers=h())
    record("Account", "sessions", r.status_code, "200")
    r = c.post(
        "/v1/hosts/me/change-password",
        headers=h(),
        json={"current_password": "wrong", "new_password": "Ben@Host2X"},
    )
    record("Account", "change-password wrong", r.status_code, "400")

    # --- Map / search (public + host) ---
    r = c.get("/v1/attractions/search", params={"city": "Lovran"}, headers=h())
    record("Map/Discover", "search attractions", r.status_code, "200")
    if state.get("host_id"):
        r = c.get(f"/v1/locations/nearby/{state['host_id']}", headers=h())
        record("Map/Discover", "nearby locations", r.status_code, "200")

    print_report()
    failed = [x for x in rows if not x.passed]
    return 0 if not failed else 1


def print_report() -> None:
    print(f"\nBen host full components — {BASE} — {EMAIL}\n")
    print("| Component | Action | HTTP | Expected | OK | Notes |")
    print("|-----------|--------|------|----------|-----|-------|")
    for row in rows:
        ok = "PASS" if row.passed else "FAIL"
        print(f"| {row.component} | {row.action} | {row.http} | {row.expected} | {ok} | {row.notes} |")
    passed = sum(1 for x in rows if x.passed)
    print(f"\n**{passed}/{len(rows)} passed.**\n")


if __name__ == "__main__":
    sys.exit(main())
