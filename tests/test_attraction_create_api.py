"""
POST /api/v1/attractions/ must work without redirect (trailing slash).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_attraction_no_redirect(client):
    email = f"at_{uuid.uuid4().hex[:8]}@example.com"
    pw = "TestPass123!"
    await client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": pw,
            "first_name": "T",
            "last_name": "U",
            "address": "Rijeka",
            "city": "Rijeka",
        },
    )
    login = await client.post("/api/v1/hosts/login", json={"email": email, "password": pw})
    assert login.status_code == 200
    token = login.json()["session_token"]
    headers = {"X-Session-Token": token}

    r = await client.post(
        "/api/v1/attractions/",
        headers=headers,
        json={
            "name": "Slash Test",
            "description": "Created with trailing slash path.",
            "attraction_type": "cultural",
            "city": "Lovran",
            "latitude": 45.27,
            "longitude": 14.27,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Slash Test"
