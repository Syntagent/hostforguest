"""Guest group create API keeps host-chosen group_size (not tied to preferences count)."""

import uuid

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_create_guest_group_respects_group_size(async_client: AsyncClient):
    email = f"group-size-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    payload = {
        "email": email,
        "password": password,
        "first_name": "Host",
        "last_name": "Tester",
        "phone": "+385 51 234 567",
        "business_name": "Test Stay",
        "business_type": "apartment",
        "address": "Oprić 71",
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
        "welcome_message": "Welcome",
    }
    reg = await async_client.post("/api/v1/hosts/register", json=payload)
    assert reg.status_code == status.HTTP_201_CREATED, reg.text

    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == status.HTTP_200_OK, login.text
    headers = {"X-Session-Token": login.json()["session_token"]}

    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Family visit", "group_size": 5},
    )
    assert create.status_code == status.HTTP_201_CREATED, create.text
    body = create.json()
    assert body["group_size"] == 5
    assert body["group_name"] == "Family visit"
