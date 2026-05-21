"""
Guest event recommendations: in-memory SQLite (no live API on port 8006).

Covers scoring/sorting, personalization payload, feed bootstrap, and QA-event filtering.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import SeasonalEvent
from app.models.host import HostProfile
from app.services.event_recommendation_service import (
    EventRecommendationService,
    _is_guest_visible_event,
    resolve_event_city_from_offerings,
)


def test_is_guest_visible_event_filters_qa_titles() -> None:
    assert _is_guest_visible_event("Marunada festival", "Autumn chestnuts in Lovran")
    assert not _is_guest_visible_event("QA event for staging", "internal")
    assert not _is_guest_visible_event("Summer fair", "ben qa checklist")


def test_resolve_event_city_from_offerings_prefers_broader_city() -> None:
    offerings = {
        "host_info": {"broader_city": "Opatija", "city": "Lovran 51415"},
        "location_info": {"city": "Oprić"},
        "stay_info": {"city": "Rijeka"},
    }
    assert resolve_event_city_from_offerings(offerings) == "Opatija"


async def _host_session(async_client: AsyncClient) -> dict[str, str]:
    email = f"evt-rec-{uuid.uuid4().hex[:12]}@example.com"
    reg = {
        "email": email,
        "password": "testpassword123",
        "first_name": "Event",
        "last_name": "Host",
        "phone": "+38551111222",
        "business_name": "Lovran Stay",
        "business_type": "apartment",
        "address": "Lungomare 1",
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "postal_code": "51450",
        "country": "Croatia",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "local_specialties": ["seafood"],
        "languages": ["hr", "en"],
        "max_group_size": 6,
        "description": "Test",
        "welcome_message": "Hi",
    }
    r = await async_client.post("/api/v1/hosts/register", json=reg)
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return {"X-Session-Token": login.json()["session_token"]}


@pytest.mark.asyncio
async def test_event_recommendations_api_sorted_and_personalized(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _host_session(async_client)
    me = await async_client.get("/api/v1/hosts/me", headers=headers)
    assert me.status_code == 200, me.text
    host_id = uuid.UUID(str(me.json()["id"]))

    profile = HostProfile(
        host_id=host_id,
        property_name="Coastal Apartment",
        property_type="apartment",
        city="Lovran",
        county="Primorsko-goranska",
        address="Lungomare 1",
        latitude=45.2919,
        longitude=14.2742,
    )
    db_session.add(profile)
    await db_session.commit()

    start = datetime.utcnow() + timedelta(days=2)
    end = start + timedelta(days=5)
    create = await async_client.post(
        "/api/v1/guest-groups/",
        json={
            "group_name": "Food & culture guests",
            "group_size": 2,
            "check_in_date": start.isoformat(),
            "check_out_date": end.isoformat(),
            "lead_guest_name": "Ana Guest",
            "interests": ["food", "culture"],
            "budget_level": "moderate",
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    access_code = create.json()["access_code"]
    assert access_code

    qa_event = SeasonalEvent(
        id=uuid.uuid4(),
        created_by_host_id=host_id,
        name="QA event for automation",
        description="Should never appear for guests",
        event_type="festival",
        city="Lovran",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
        is_active=True,
    )
    db_session.add(qa_event)
    await db_session.commit()

    r = await async_client.get(
        f"/api/v1/guest-groups/access/{access_code}/event-recommendations",
        params={"limit": 10},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert body.get("city")
    assert "personalization" in body
    assert "stay_window" in body
    assert "total_candidates" in body

    recs = body.get("recommendations") or []
    assert isinstance(recs, list)
    assert not any("qa event" in str(x.get("title", "")).lower() for x in recs)

    if len(recs) >= 2:
        scores = [x["relevance_score"] for x in recs]
        assert scores == sorted(scores, reverse=True)
        first = recs[0]
        for key in ("title", "relevance_score", "why_recommended", "plan_hint", "scores"):
            assert key in first


@pytest.mark.asyncio
async def test_event_recommendation_service_unit_scoring(
    db_session: AsyncSession,
) -> None:
    from app.models.guest_group import GuestGroup
    from app.models.host import Host

    host = Host(
        id=uuid.uuid4(),
        email=f"evt-svc-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        first_name="T",
        last_name="H",
        address="1 St",
        city="Lovran",
        latitude=45.29,
        longitude=14.27,
    )
    db_session.add(host)
    group = GuestGroup(
        id=uuid.uuid4(),
        host_id=host.id,
        group_name="Guests",
        group_size=2,
        interests=["food", "wine"],
        check_in_date=datetime.utcnow() + timedelta(days=1),
        check_out_date=datetime.utcnow() + timedelta(days=6),
    )
    db_session.add(group)
    await db_session.commit()

    svc = EventRecommendationService(db_session)
    result = await svc.get_recommendations_for_access_code(
        group,
        host,
        None,
        [],
        limit=8,
        bootstrap_if_empty=True,
    )
    assert result["success"] is True
    assert result["city"] == "Lovran"
    assert result["total_candidates"] >= 0
    recs = result["recommendations"]
    if recs:
        assert recs[0]["relevance_score"] >= recs[-1]["relevance_score"]
