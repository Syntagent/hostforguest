"""
Guest group tab flows using ``async_client`` (in-memory test DB).
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


def _host_registration(email: str) -> dict:
    return {
        "email": email,
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "Host",
        "phone": "+38551111222",
        "business_name": "Test Biz",
        "business_type": "apartment",
        "address": "Test Address 1",
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "postal_code": "51450",
        "country": "Croatia",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "local_specialties": ["seafood"],
        "languages": ["hr", "en"],
        "max_group_size": 6,
        "description": "Test host",
        "welcome_message": "Welcome",
    }


async def _session_headers(async_client: AsyncClient, email: str) -> dict[str, str]:
    r = await async_client.post("/api/v1/hosts/register", json=_host_registration(email))
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return {"X-Session-Token": login.json()["session_token"]}


def _group_payload(name: str, interests: list[str] | None = None) -> dict:
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(days=4)
    return {
        "group_name": name,
        "group_size": 4,
        "check_in_date": start.isoformat(),
        "check_out_date": end.isoformat(),
        "lead_guest_name": "John Smith",
        "lead_guest_email": "john@example.com",
        "preferred_language": "en",
        "interests": interests or ["culture", "food"],
        "budget_level": "moderate",
    }


@pytest.mark.asyncio
async def test_create_guest_group(async_client: AsyncClient):
    email = f"gg-fn-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    create_response = await async_client.post(
        "/api/v1/guest-groups/",
        json=_group_payload("Test Family Group"),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text

    created = create_response.json()
    assert "id" in created
    assert created["group_name"] == "Test Family Group"
    assert created["group_size"] == 4
    assert "access_code" in created
    assert created["interests"]


@pytest.mark.asyncio
async def test_get_host_guest_groups(async_client: AsyncClient):
    email = f"gg-fn2-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    groups_response = await async_client.get("/api/v1/guest-groups/host", headers=headers)
    assert groups_response.status_code == 200
    assert isinstance(groups_response.json(), list)


@pytest.mark.asyncio
async def test_guest_group_access_code_generation(async_client: AsyncClient):
    email = f"gg-acc-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    access_codes = []
    for i in range(3):
        create_response = await async_client.post(
            "/api/v1/guest-groups/",
            json=_group_payload(f"Access Code Test Group {i + 1}"),
            headers=headers,
        )
        assert create_response.status_code == 201, create_response.text
        code = create_response.json()["access_code"]
        assert code and len(code) >= 6
        assert str(code).replace("-", "").isalnum() or code.isalnum()
        access_codes.append(code)

    assert len(set(access_codes)) == 3


@pytest.mark.asyncio
async def test_guest_group_preferences(async_client: AsyncClient):
    email = f"gg-pref-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    interests = ["history", "architecture", "local_cuisine"]
    create_response = await async_client.post(
        "/api/v1/guest-groups/",
        json=_group_payload("Preferences Test Group", interests=interests),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert "history" in created["interests"]
