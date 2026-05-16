"""Host-scoped partner relationship routes: session required, no cross-host access."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_host_partners_requires_auth(async_client: AsyncClient):
    fake_host = str(uuid.uuid4())
    r = await async_client.get(f"/api/v1/partners/hosts/{fake_host}/partners")
    assert r.status_code == 401

    post = await async_client.post(
        f"/api/v1/partners/hosts/{fake_host}/partners",
        json={"partner_id": str(uuid.uuid4())},
    )
    assert post.status_code == 401


@pytest.mark.asyncio
async def test_host_partners_forbidden_other_host(async_client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]

    async def register_and_login(email_suffix: str):
        email = f"p_{email_suffix}@example.com"
        reg = await async_client.post(
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
        login = await async_client.post(
            "/api/v1/hosts/login",
            json={"email": email, "password": "testpassword123"},
        )
        assert login.status_code == 200, login.text
        return login.json()["session_token"], host_id

    token_a, id_a = await register_and_login(f"a{suffix}")
    _, id_b = await register_and_login(f"b{suffix}")
    assert id_a and id_b
    assert id_a != id_b

    headers = {"X-Session-Token": token_a}
    r = await async_client.get(f"/api/v1/partners/hosts/{id_b}/partners", headers=headers)
    assert r.status_code == 403

    ok = await async_client.get(f"/api/v1/partners/hosts/{id_a}/partners", headers=headers)
    assert ok.status_code == 200
    assert ok.json() == []


@pytest.mark.asyncio
async def test_cleaning_message_context_requires_auth(async_client: AsyncClient):
    r = await async_client.get("/api/v1/cleaning/message-context")
    assert r.status_code == 401
