"""Host guest-group list/detail include access_code when an active code exists."""

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, suffix: str) -> tuple[str, str]:
    email = f"ac_{suffix}@example.com"
    reg = await client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": "testpassword123",
            "first_name": "A",
            "last_name": "B",
            "address": "1 St",
            "city": "Lovran",
        },
    )
    assert reg.status_code == 201, reg.text
    host_id = str(reg.json()["id"])
    login = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return login.json()["session_token"], host_id


@pytest.mark.asyncio
async def test_host_list_and_detail_include_access_code_after_regenerate(async_client: AsyncClient):
    token, _ = await _register_and_login(async_client, uuid.uuid4().hex[:12])
    headers = {"X-Session-Token": token}
    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Copy Test Group", "group_size": 2},
    )
    assert create.status_code == 201, create.text
    group_id = create.json()["id"]
    assert create.json().get("access_code"), "create_guest_group should issue an initial access code"

    regen = await async_client.post(
        f"/api/v1/guest-groups/{group_id}/regenerate-code",
        headers=headers,
    )
    assert regen.status_code == 200, regen.text
    code = regen.json()["code"]
    assert code

    lst = await async_client.get("/api/v1/guest-groups/host", headers=headers)
    assert lst.status_code == 200, lst.text
    rows = lst.json()
    match = next((g for g in rows if g["id"] == group_id), None)
    assert match is not None
    assert match.get("access_code") == code

    one = await async_client.get(f"/api/v1/guest-groups/{group_id}", headers=headers)
    assert one.status_code == 200, one.text
    assert one.json().get("access_code") == code
