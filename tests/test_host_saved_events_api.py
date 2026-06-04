"""Host-visible guest saved events API."""

import uuid

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_host_sees_saved_events_on_guest_group(async_client: AsyncClient):
    email = f"saved-host-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Saved",
            "last_name": "Host",
            "address": "Oprić 71",
            "city": "Lovran",
            "country": "Croatia",
        },
    )
    assert reg.status_code == status.HTTP_201_CREATED, reg.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    headers = {"X-Session-Token": login.json()["session_token"]}

    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Saved events group", "group_size": 2},
    )
    assert create.status_code == status.HTTP_201_CREATED, create.text
    group = create.json()
    group_id = group["id"]
    code = group.get("access_code")
    assert code

    event_id = f"pytest-saved-{uuid.uuid4().hex[:8]}"
    save = await async_client.post(
        f"/api/v1/guest-groups/access/{code}/saved-events",
        json={
            "event_id": event_id,
            "title": "Pytest festival",
            "source": "feed",
            "plan_hint": "Test event for host visibility.",
        },
    )
    assert save.status_code == status.HTTP_200_OK, save.text

    detail = await async_client.get(f"/api/v1/guest-groups/{group_id}", headers=headers)
    assert detail.status_code == status.HTTP_200_OK, detail.text
    saved = detail.json().get("saved_event_recommendations") or []
    assert any(str(x.get("event_id")) == event_id for x in saved)

    plan = await async_client.put(
        f"/api/v1/guest-groups/{group_id}/saved-events/{event_id}",
        headers=headers,
        json={"host_status": "planned", "host_note": "pytest planned"},
    )
    assert plan.status_code == status.HTTP_200_OK, plan.text
    rows = plan.json().get("saved_events") or []
    match = next((r for r in rows if r.get("event_id") == event_id), None)
    assert match and match.get("host_status") == "planned"


@pytest.mark.asyncio
async def test_guest_assistant_events_fallback(async_client: AsyncClient):
    email = f"asst-{uuid.uuid4().hex[:12]}@example.com"
    password = "testpassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Asst",
            "last_name": "Host",
            "address": "Oprić 71",
            "city": "Lovran",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    headers = {"X-Session-Token": login.json()["session_token"]}
    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Assistant group", "group_size": 2},
    )
    code = create.json().get("access_code")
    assert code

    r = await async_client.post(
        f"/api/v1/guest-groups/access/{code}/assistant",
        json={"message": "What events are on this week?", "guest_name": "Guest"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()
    assert body.get("success") is True
    assert body.get("message")
    msg = body["message"].lower()
    assert "event" in msg or "događ" in msg or "tab" in msg
