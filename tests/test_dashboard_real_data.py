"""
Dashboard-style HTTP checks using ``async_client`` (in-memory test DB).
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


def _host_body(email: str) -> dict:
    return {
        "email": email,
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "Host",
        "phone": "+38551111222",
        "business_name": "Dash Real Biz",
        "business_type": "apartment",
        "address": "Dash Real St 1",
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "postal_code": "51450",
        "country": "Croatia",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "local_specialties": ["seafood"],
        "languages": ["hr", "en"],
        "max_group_size": 6,
        "description": "Host",
        "welcome_message": "Welcome",
    }


async def _register_and_token(async_client: AsyncClient, email: str) -> dict[str, str]:
    r = await async_client.post("/api/v1/hosts/register", json=_host_body(email))
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return {"X-Session-Token": login.json()["session_token"]}


@pytest.mark.asyncio
async def test_dashboard_analytics_real_data(async_client: AsyncClient):
    email = f"dash-real-an-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _register_and_token(async_client, email)

    analytics_response = await async_client.get(
        "/api/v1/hosts/analytics", headers=headers
    )
    assert analytics_response.status_code == 200

    analytics_data = analytics_response.json()
    assert "guest_groups" in analytics_data
    assert "attractions" in analytics_data
    assert "recommendations" in analytics_data
    assert "satisfaction" in analytics_data

    guest_groups = analytics_data["guest_groups"]
    assert "total" in guest_groups
    assert "active" in guest_groups
    assert "inactive" in guest_groups

    attractions = analytics_data["attractions"]
    assert "total" in attractions
    assert "categories" in attractions

    recommendations = analytics_data["recommendations"]
    assert "total_given" in recommendations
    assert "this_month" in recommendations

    satisfaction = analytics_data["satisfaction"]
    assert "average_rating" in satisfaction
    assert "total_reviews" in satisfaction


@pytest.mark.asyncio
async def test_guest_groups_real_data(async_client: AsyncClient):
    email = f"dash-real-gg-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _register_and_token(async_client, email)

    groups_response = await async_client.get(
        "/api/v1/guest-groups/host", headers=headers
    )
    assert groups_response.status_code == 200
    groups_data = groups_response.json()
    assert isinstance(groups_data, list)

    if groups_data:
        group = groups_data[0]
        assert "id" in group
        assert "group_size" in group
        assert "status" in group
        assert "created_at" in group


@pytest.mark.asyncio
async def test_attractions_real_data(async_client: AsyncClient):
    email = f"dash-real-at-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _register_and_token(async_client, email)

    attractions_response = await async_client.get(
        "/api/v1/attractions/host", headers=headers
    )
    assert attractions_response.status_code == 200
    attractions_data = attractions_response.json()
    assert isinstance(attractions_data, list)

    if attractions_data:
        attraction = attractions_data[0]
        assert "id" in attraction
        assert "name" in attraction
        assert "description" in attraction
        assert "attraction_type" in attraction
        assert "city" in attraction


@pytest.mark.asyncio
async def test_realtime_updates_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/realtime/updates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_data_consistency(async_client: AsyncClient):
    email = f"dash-real-cs-{uuid.uuid4().hex[:12]}@example.com"
    headers = await _register_and_token(async_client, email)

    analytics_response = await async_client.get(
        "/api/v1/hosts/analytics", headers=headers
    )
    assert analytics_response.status_code == 200
    analytics_data = analytics_response.json()

    groups_response = await async_client.get(
        "/api/v1/guest-groups/host", headers=headers
    )
    assert groups_response.status_code == 200
    groups_data = groups_response.json()

    attractions_response = await async_client.get(
        "/api/v1/attractions/host", headers=headers
    )
    assert attractions_response.status_code == 200
    attractions_data = attractions_response.json()

    assert analytics_data["guest_groups"]["total"] == len(groups_data)
    assert analytics_data["attractions"]["total"] == len(attractions_data)

    from app.services.guest_group_stay import is_in_stay

    class _G:
        def __init__(self, d):
            self.check_in_date = d.get("check_in_date")
            self.check_out_date = d.get("check_out_date")

    in_stay = len([g for g in groups_data if is_in_stay(_G(g))])
    assert analytics_data["guest_groups"]["active"] == in_stay
