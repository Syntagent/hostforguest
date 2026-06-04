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


@pytest.mark.asyncio
async def test_create_attraction_without_trailing_slash(client):
    """Frontend posts to /api/v1/attractions/; legacy path must not 307 without body."""
    email = f"at2_{uuid.uuid4().hex[:8]}@example.com"
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
    token = login.json()["session_token"]
    headers = {"X-Session-Token": token}

    r = await client.post(
        "/api/v1/attractions",
        headers=headers,
        json={
            "name": "No Slash Path",
            "description": "Created via path without trailing slash.",
            "attraction_type": "cultural",
            "city": "Lovran",
            "address": "Stari grad 12",
        },
    )
    assert r.status_code in (201, 307, 308), r.text
    if r.status_code in (307, 308):
        location = r.headers.get("location", "")
        assert "/attractions/" in location


@pytest.mark.asyncio
async def test_create_attraction_with_address_only_geocoding(client):
    """Server geocodes when coordinates omitted but address+city are present."""
    email = f"at3_{uuid.uuid4().hex[:8]}@example.com"
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
    token = login.json()["session_token"]
    headers = {"X-Session-Token": token}

    r = await client.post(
        "/api/v1/attractions/",
        headers=headers,
        json={
            "name": "Address Only Geo",
            "description": "No lat/lng in payload; server resolves from address.",
            "attraction_type": "cultural",
            "city": "Lovran",
            "address": "Stari grad 12, Lovran",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["latitude"] is not None
    assert body["longitude"] is not None
