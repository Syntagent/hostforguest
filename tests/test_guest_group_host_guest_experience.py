"""Host guest-experience endpoint: session auth, ownership, payload shape."""

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, suffix: str) -> tuple[str, str]:
    email = f"ge_{suffix}@example.com"
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
async def test_guest_experience_requires_auth(async_client: AsyncClient):
    gid = str(uuid.uuid4())
    r = await async_client.get(f"/api/v1/guest-groups/{gid}/guest-experience")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_guest_experience_not_found_for_random_uuid(async_client: AsyncClient):
    token, _ = await _register_and_login(async_client, uuid.uuid4().hex[:12])
    headers = {"X-Session-Token": token}
    r = await async_client.get(
        f"/api/v1/guest-groups/{uuid.uuid4()}/guest-experience",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_guest_experience_forbidden_other_host(async_client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    token_a, _ = await _register_and_login(async_client, f"a{suffix}")
    token_b, _ = await _register_and_login(async_client, f"b{suffix}")

    headers_a = {"X-Session-Token": token_a}
    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers_a,
        json={"group_name": "G1", "group_size": 2},
    )
    assert create.status_code == 201, create.text
    group_id = create.json()["id"]

    r = await async_client.get(
        f"/api/v1/guest-groups/{group_id}/guest-experience",
        headers={"X-Session-Token": token_b},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_guest_experience_ok_shape_with_auto_access_code(async_client: AsyncClient):
    token, _ = await _register_and_login(async_client, uuid.uuid4().hex[:12])
    headers = {"X-Session-Token": token}
    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Preview Group", "group_size": 3},
    )
    assert create.status_code == 201, create.text
    body = create.json()
    group_id = body["id"]
    assert body.get("access_code"), "create_guest_group should issue an access code"

    r = await async_client.get(
        f"/api/v1/guest-groups/{group_id}/guest-experience",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["guest_group"]["id"] == group_id
    assert data["guest_group"]["group_name"] == "Preview Group"
    assert data["access_code"]
    assert data["guest_app_path"] == f"/guest/{data['access_code']}"
    assert data["guest_join_path"] == "/guest/join"


@pytest.mark.asyncio
async def test_regenerate_access_code_returns_new_code(async_client: AsyncClient):
    token, _ = await _register_and_login(async_client, uuid.uuid4().hex[:12])
    headers = {"X-Session-Token": token}
    create = await async_client.post(
        "/api/v1/guest-groups/",
        headers=headers,
        json={"group_name": "Regen Group", "group_size": 2},
    )
    assert create.status_code == 201, create.text
    old_code = create.json()["access_code"]
    group_id = create.json()["id"]

    regen = await async_client.post(
        f"/api/v1/guest-groups/{group_id}/regenerate-code",
        headers=headers,
    )
    assert regen.status_code == 200, regen.text
    new_code = regen.json()["code"]
    assert new_code != old_code

    old_access = await async_client.get(f"/api/v1/guest-groups/access/{old_code}")
    assert old_access.status_code == 404

    new_access = await async_client.get(f"/api/v1/guest-groups/access/{new_code}")
    assert new_access.status_code == 200
