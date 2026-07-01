"""Itinerary AI suggestions and activity datetime fixes."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models.guest_group import GuestGroup, GuestGroupResponse
from app.services.itinerary_service import _naive_utc


def test_naive_utc_strips_timezone():
    aware = datetime(2000, 1, 1, 8, 0, tzinfo=timezone.utc)
    assert _naive_utc(aware) == datetime(2000, 1, 1, 8, 0)


def test_guest_group_response_coerces_null_json_lists():
    group = GuestGroup(
        host_id=uuid.uuid4(),
        group_size=2,
        age_groups=None,
        interests=None,
        mobility_requirements=None,
        dietary_restrictions=None,
    )
    resp = GuestGroupResponse.model_validate(group)
    assert resp.age_groups == []
    assert resp.interests == []


@pytest.mark.asyncio
async def test_generate_itinerary_suggestions_template_without_guest_group(
    async_client: AsyncClient,
):
    email = f"route-ai-{uuid.uuid4().hex[:12]}@example.com"
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
    assert login.status_code == status.HTTP_200_OK, login.text
    headers = {"X-Session-Token": login.json()["session_token"]}

    res = await async_client.post(
        "/api/v1/itineraries/suggestions",
        headers=headers,
        json={
            "duration_days": 2,
            "theme_prompt": "Coastal walk",
            "interests": ["culture", "food"],
            "pace": "moderate",
            "budget_level": "moderate",
        },
    )
    assert res.status_code == status.HTTP_200_OK, res.text
    body = res.json()
    assert body.get("suggested_itinerary")
    assert body.get("day_plans")
