"""Guest stay enrichment: host offerings payload and guest APIs."""

import uuid

import pytest
from httpx import AsyncClient


async def _register_host(client: AsyncClient, suffix: str) -> str:
    email = f"gse_{suffix}@example.com"
    reg = await client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": "testpassword123",
            "first_name": "Stay",
            "last_name": "Host",
            "address": "71 Oprić",
            "city": "Lovran",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return login.json()["session_token"]


@pytest.mark.asyncio
async def test_host_offerings_includes_stay_extras(async_client: AsyncClient):
    token = await _register_host(async_client, uuid.uuid4().hex[:10])
    headers = {"X-Session-Token": token}

    profile = await async_client.put(
        "/api/v1/hosts/me/profile",
        headers=headers,
        json={
            "property_name": "Sea View Apartment",
            "property_type": "apartment",
            "number_of_rooms": 2,
            "services_offered": ["airport_pickup", "local_recommendations"],
            "gallery_images": ["https://example.com/photo.jpg"],
            "property_rules": {
                "checkInTime": "15:00",
                "checkOutTime": "10:00",
                "houseRules": ["No smoking"],
                "wifiName": "GuestWiFi",
                "wifiPassword": "welcome123",
            },
            "special_offers": ["10% off boat tour"],
            "trusted_partners": ["Local winery"],
        },
    )
    assert profile.status_code == 200, profile.text

    group = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Stay Testers", "group_size": 2},
    )
    assert group.status_code == 201, group.text
    access_code = group.json()["access_code"]

    offerings = await async_client.get(
        f"/api/v1/guest-groups/access/{access_code}/host-offerings"
    )
    assert offerings.status_code == 200, offerings.text
    data = offerings.json()
    stay = data["host_offerings"]["stay_info"]
    assert stay["property_name"] == "Sea View Apartment"
    assert stay["property_type"] == "apartment"
    assert stay["number_of_rooms"] == 2
    assert "airport_pickup" in stay["services_offered"]
    assert stay["property_rules"]["wifiName"] == "GuestWiFi"
    assert data["host_offerings"]["special_offers"] == ["10% off boat tour"]
    assert data["host_offerings"]["trusted_partners"] == ["Local winery"]


@pytest.mark.asyncio
async def test_guest_assistant_endpoint(async_client: AsyncClient):
    token = await _register_host(async_client, uuid.uuid4().hex[:10])
    headers = {"X-Session-Token": token}
    group = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "AI Group", "group_size": 2},
    )
    assert group.status_code == 201, group.text
    access_code = group.json()["access_code"]

    res = await async_client.post(
        f"/api/v1/guest-groups/access/{access_code}/assistant",
        json={"message": "What should we do today?", "guest_name": "Alex"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["message"]
    assert isinstance(body.get("suggestions"), list)


@pytest.mark.asyncio
async def test_guest_maintenance_reports_list(async_client: AsyncClient):
    token = await _register_host(async_client, uuid.uuid4().hex[:10])
    headers = {"X-Session-Token": token}
    group = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Maint Group", "group_size": 2},
    )
    assert group.status_code == 201, group.text
    access_code = group.json()["access_code"]

    created = await async_client.post(
        "/api/v1/maintenance/guest-reports",
        json={
            "access_code": access_code,
            "category": "plumbing",
            "title": "No hot water",
            "description": "Shower runs cold",
        },
    )
    assert created.status_code == 201, created.text

    listed = await async_client.get(f"/api/v1/maintenance/guest-reports/{access_code}")
    assert listed.status_code == 200, listed.text
    issues = listed.json()["issues"]
    assert len(issues) >= 1
    assert any(i["title"] == "No hot water" for i in issues)
