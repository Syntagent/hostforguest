"""Host profile geocode refresh and guest group update fixes."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models.host import HostProfile
from app.services.host_service import _apply_geocode_if_needed


def test_apply_geocode_refreshes_stale_coordinates():
    profile = HostProfile(
        host_id=uuid.uuid4(),
        address="71 Oprić",
        city="Lovran",
        county="Primorsko-goranska",
        latitude=45.168,
        longitude=14.274,
    )
    _apply_geocode_if_needed(profile)
    assert profile.latitude is not None
    assert profile.longitude is not None
    assert profile.latitude > 45.2


@pytest.mark.asyncio
async def test_guest_group_update_persists_stay_dates(async_client: AsyncClient):
    email = f"gg-update-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Stay",
            "last_name": "Update",
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
        json={"group_name": "Date test group", "group_size": 2},
    )
    assert create.status_code == status.HTTP_201_CREATED, create.text
    group_id = create.json()["id"]

    check_in = datetime(2026, 7, 1, 15, 0, tzinfo=timezone.utc).isoformat()
    check_out = datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc).isoformat()
    update = await async_client.put(
        f"/api/v1/guest-groups/{group_id}",
        headers=headers,
        json={"check_in_date": check_in, "check_out_date": check_out},
    )
    assert update.status_code == status.HTTP_200_OK, update.text
    body = update.json()
    assert body.get("check_in_date")
    assert body.get("check_out_date")

    listed = await async_client.get("/api/v1/guest-groups/host", headers=headers)
    match = next(g for g in listed.json() if g["id"] == group_id)
    assert match.get("check_in_date")
    assert match.get("check_out_date")
