"""
Auth CRUD: register, read session, change password, logout, delete (soft).
Uses .env / pytest fixtures where available.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_ux_crud_flow(client: AsyncClient):
    email = f"crud_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    new_password = "NewPass456!"

    reg = await client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "CRUD",
            "last_name": "Tester",
            "address": "Test St 1",
            "city": "Rijeka",
        },
    )
    assert reg.status_code == 201, reg.text

    bad = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "wrong"},
    )
    assert bad.status_code == 401

    login = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    token = body["session_token"]
    headers = {"X-Session-Token": token}

    me = await client.get("/api/v1/hosts/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email

    wrong_pw = await client.post(
        "/api/v1/hosts/me/change-password",
        headers=headers,
        json={"current_password": "nope", "new_password": new_password},
    )
    assert wrong_pw.status_code == 400

    change = await client.post(
        "/api/v1/hosts/me/change-password",
        headers=headers,
        json={"current_password": password, "new_password": new_password},
    )
    assert change.status_code == 200, change.text

    login_new = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": new_password},
    )
    assert login_new.status_code == 200
    token2 = login_new.json()["session_token"]
    headers2 = {"X-Session-Token": token2}

    sessions = await client.get("/api/v1/hosts/sessions", headers=headers2)
    assert sessions.status_code == 200
    assert sessions.json().get("success") is True

    logout = await client.post("/api/v1/hosts/logout", headers=headers2)
    assert logout.status_code == 200

    me_after = await client.get("/api/v1/hosts/me", headers=headers2)
    assert me_after.status_code == 401

    login_again = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": new_password},
    )
    assert login_again.status_code == 200
    headers3 = {"X-Session-Token": login_again.json()["session_token"]}

    delete = await client.delete("/api/v1/hosts/me", headers=headers3)
    assert delete.status_code == 204

    login_deleted = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": new_password},
    )
    assert login_deleted.status_code in (401, 403)
