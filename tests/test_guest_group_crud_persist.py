"""Guest group create persists and is returned after list refresh."""

import uuid

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_guest_group_create_persists_after_list(async_client: AsyncClient):
    email = f"gg-persist-{uuid.uuid4().hex[:12]}@example.com"
    password = "securepassword123"
    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Group",
            "last_name": "Persist",
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
    name = f"Persist {uuid.uuid4().hex[:6]}"

    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": name, "group_size": 4},
    )
    assert create.status_code == status.HTTP_201_CREATED, create.text
    created_id = create.json()["id"]

    listed = await async_client.get("/api/v1/guest-groups/host", headers=headers)
    assert listed.status_code == status.HTTP_200_OK, listed.text
    ids = [g["id"] for g in listed.json()]
    assert created_id in ids
    match = next(g for g in listed.json() if g["id"] == created_id)
    assert match["group_name"] == name
    assert match["group_size"] == 4
