"""Accommodation tab save must work when host has no host_profiles row yet."""

import uuid

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models.host import HostCreate, HostProfileUpdate
from app.services.host_service import HostService


@pytest.mark.asyncio
async def test_update_host_profile_creates_missing_row(db_session):
    email = f"upsert-profile-{uuid.uuid4().hex[:12]}@example.com"
    svc = HostService(db_session)
    created = await svc.create_host(
        HostCreate(
            email=email,
            password="testpassword123",
            first_name="Ana",
            last_name="Mestrovic",
            address="Test 1",
            city="Lovran",
            country="Croatia",
        )
    )
    assert created is not None

    result = await svc.update_host_profile(
        created.id,
        HostProfileUpdate(
            property_name="Villa Ana",
            property_type="apartment",
            max_guests=4,
            city="Lovran",
            location_story="Cozy stay near the sea.",
        ),
    )
    assert result is not None
    assert result.property_name == "Villa Ana"
    assert result.max_guests == 4

    stored = await svc.get_host_profile(created.id)
    assert stored is not None
    assert stored.property_name == "Villa Ana"


@pytest.mark.asyncio
async def test_put_profile_without_existing_row_via_api(
    async_client: AsyncClient,
):
    email = f"upsert-api-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "Ana",
        "last_name": "Mestrovic",
        "phone": "+385 51 234 567",
        "business_name": "Apartment Lovran",
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
        "description": "Cozy apartment",
        "welcome_message": "Welcome!",
    }
    reg = await async_client.post("/api/v1/hosts/register", json=register_payload)
    assert reg.status_code == status.HTTP_201_CREATED, reg.text

    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == status.HTTP_200_OK, login.text
    headers = {"X-Session-Token": login.json()["session_token"]}

    update = await async_client.put(
        "/api/v1/hosts/me/profile",
        headers=headers,
        json={
            "property_name": "Sunset Apartment",
            "property_type": "apartment",
            "max_guests": 5,
            "city": "Lovran",
            "location_story": "Updated from accommodation tab.",
        },
    )
    assert update.status_code == status.HTTP_200_OK, update.text
    body = update.json()
    assert body["property_name"] == "Sunset Apartment"
    assert body["max_guests"] == 5
