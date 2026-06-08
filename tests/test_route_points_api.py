"""Route TNT points CRUD on itineraries."""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_route_points_create_update_delete_reorder(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.services.itinerary_service import ItineraryService

    async def fake_geocode_address(self, host_id, address):
        return None

    async def fake_calculate_travel_to_activity(self, day_plan_id, activity_data, coords, host_id):
        return {
            "time_minutes": 0,
            "distance_km": 0,
            "cost": 0,
            "instructions": None,
        }

    async def fake_generate_google_maps_url(self, location_name, address, coords, host_id):
        return None

    monkeypatch.setattr(ItineraryService, "_geocode_address", fake_geocode_address)
    monkeypatch.setattr(
        ItineraryService, "_calculate_travel_to_activity", fake_calculate_travel_to_activity
    )
    monkeypatch.setattr(
        ItineraryService, "_generate_google_maps_url", fake_generate_google_maps_url
    )

    email = f"route-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Route",
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

    it = await async_client.post(
        "/api/v1/itineraries/",
        headers=headers,
        json={
            "title": "Coastal walk",
            "base_location": "Lovran, Croatia",
            "is_template": True,
        },
    )
    assert it.status_code == status.HTTP_201_CREATED, it.text
    itinerary_id = it.json()["id"]

    day = await async_client.post(
        f"/api/v1/itineraries/{itinerary_id}/day-plans",
        headers=headers,
        json={
            "day_number": 1,
            "date": "2000-01-01",
            "title": "Day 1",
            "theme": "Walk",
        },
    )
    assert day.status_code == status.HTTP_201_CREATED, day.text
    day_plan_id = day.json()["id"]

    p1 = await async_client.post(
        f"/api/v1/itineraries/{itinerary_id}/route-points",
        headers=headers,
        json={
            "day_plan_id": day_plan_id,
            "name": "Lungomare start",
            "latitude": 45.2739,
            "longitude": 14.2711,
            "estimated_duration": 45,
        },
    )
    assert p1.status_code == status.HTTP_201_CREATED, p1.text
    p2 = await async_client.post(
        f"/api/v1/itineraries/{itinerary_id}/route-points",
        headers=headers,
        json={
            "day_plan_id": day_plan_id,
            "name": "Old town",
            "latitude": 45.2745,
            "longitude": 14.2720,
            "estimated_duration": 60,
        },
    )
    assert p2.status_code == status.HTTP_201_CREATED, p2.text
    p3 = await async_client.post(
        f"/api/v1/itineraries/{itinerary_id}/route-points",
        headers=headers,
        json={
            "day_plan_id": day_plan_id,
            "name": "Hidden viewpoint",
            "latitude": 45.2751,
            "longitude": 14.2734,
            "estimated_duration": 30,
        },
    )
    assert p3.status_code == status.HTTP_201_CREATED, p3.text

    listed = await async_client.get(
        f"/api/v1/itineraries/{itinerary_id}/route-points",
        headers=headers,
    )
    assert listed.status_code == status.HTTP_200_OK, listed.text
    assert len(listed.json()) == 3

    pid = p1.json()["id"]
    upd = await async_client.put(
        f"/api/v1/itineraries/route-points/{pid}",
        headers=headers,
        json={"title": "Lungomare pier", "description": "Sea view"},
    )
    assert upd.status_code == status.HTTP_200_OK, upd.text
    assert upd.json()["name"] == "Lungomare pier"

    reorder = await async_client.put(
        f"/api/v1/itineraries/{itinerary_id}/route-points/reorder",
        headers=headers,
        json={
            "day_plan_id": day_plan_id,
            "ordered_activity_ids": [p2.json()["id"], pid],
        },
    )
    assert reorder.status_code == status.HTTP_200_OK, reorder.text
    reordered = await async_client.get(
        f"/api/v1/itineraries/{itinerary_id}/route-points",
        headers=headers,
    )
    assert reordered.status_code == status.HTTP_200_OK, reordered.text
    order_by_name = {point["name"]: point["order_index"] for point in reordered.json()}
    assert order_by_name == {
        "Old town": 1,
        "Lungomare pier": 2,
        "Hidden viewpoint": 3,
    }

    duplicate_reorder = await async_client.put(
        f"/api/v1/itineraries/{itinerary_id}/route-points/reorder",
        headers=headers,
        json={
            "day_plan_id": day_plan_id,
            "ordered_activity_ids": [p2.json()["id"], p2.json()["id"]],
        },
    )
    assert duplicate_reorder.status_code == status.HTTP_400_BAD_REQUEST

    save = await async_client.put(
        f"/api/v1/itineraries/{itinerary_id}",
        headers=headers,
        json={"title": "Updated coastal route", "base_location": "Oprić 71, Lovran"},
    )
    assert save.status_code == status.HTTP_200_OK, save.text
    assert save.json()["title"] == "Updated coastal route"

    delete = await async_client.delete(
        f"/api/v1/itineraries/route-points/{pid}",
        headers=headers,
    )
    assert delete.status_code == status.HTTP_204_NO_CONTENT, delete.text
