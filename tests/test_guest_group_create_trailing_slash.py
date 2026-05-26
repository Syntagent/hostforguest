"""Guest group create must use trailing slash (FastAPI route is POST /guest-groups/)."""

import uuid

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_create_guest_group_requires_trailing_slash_for_direct_201(
    async_client: AsyncClient,
):
    email = f"slash-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Slash",
            "last_name": "Test",
            "address": "1 St",
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

    no_slash = await async_client.post(
        "/api/v1/guest-groups",
        headers=headers,
        json={"group_name": "No slash", "group_size": 2},
    )
    assert no_slash.status_code == status.HTTP_201_CREATED, no_slash.text
    assert no_slash.json()["group_name"] == "No slash"
    assert no_slash.json()["group_size"] == 2

    with_slash = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "With slash", "group_size": 3},
    )
    assert with_slash.status_code == status.HTTP_201_CREATED, with_slash.text
    assert with_slash.json()["group_name"] == "With slash"
    assert with_slash.json()["group_size"] == 3
