"""
Attractions tab flows against the async test client (shared in-memory DB).
"""

import uuid

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


@pytest.mark.asyncio
async def test_create_attraction(async_client: AsyncClient):
    email = f"attr-fn-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    attraction_data = {
        "name": "Test Croatian Restaurant",
        "description": "A wonderful local restaurant serving authentic Istrian cuisine",
        "attraction_type": "culinary",
        "city": "Lovran",
        "admission_fee": "€20-35 per person",
    }

    create_response = await async_client.post(
        "/api/v1/attractions/", json=attraction_data, headers=headers
    )
    assert create_response.status_code == 201, create_response.text

    created = create_response.json()
    assert "id" in created
    assert created["name"] == "Test Croatian Restaurant"
    assert created["attraction_type"] == "culinary"
    assert created["city"] == "Lovran"


@pytest.mark.asyncio
async def test_get_host_attractions(async_client: AsyncClient):
    email = f"attr-fn2-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    attractions_response = await async_client.get(
        "/api/v1/attractions/host", headers=headers
    )
    assert attractions_response.status_code == 200
    assert isinstance(attractions_response.json(), list)


@pytest.mark.asyncio
async def test_update_attraction(async_client: AsyncClient):
    email = f"attr-fn-up-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    create_response = await async_client.post(
        "/api/v1/attractions/",
        json={
            "name": "Original Name",
            "description": "Original description",
            "attraction_type": "culinary",
            "city": "Lovran",
        },
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    attraction_id = create_response.json()["id"]

    update_response = await async_client.put(
        f"/api/v1/attractions/{attraction_id}",
        json={
            "name": "Updated Croatian Restaurant",
            "description": "Updated description with more details",
        },
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["name"] == "Updated Croatian Restaurant"
    assert updated["description"] == "Updated description with more details"


@pytest.mark.asyncio
async def test_attraction_validation(async_client: AsyncClient):
    email = f"attr-fn-val-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _session_headers(async_client, email)

    invalid_data = {"name": "Test Attraction"}

    create_response = await async_client.post(
        "/api/v1/attractions/", json=invalid_data, headers=headers
    )
    assert create_response.status_code in (400, 422)
