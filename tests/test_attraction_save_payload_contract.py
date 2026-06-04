"""
Contract: attraction create must accept address+city without client coordinates.

Mirrors EnhancedAttractionModal submit → host dashboard handler → POST /attractions/.
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


async def _host_headers(client: AsyncClient) -> dict[str, str]:
    email = f"save_{uuid.uuid4().hex[:8]}@example.com"
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
    return {"X-Session-Token": login.json()["session_token"]}


@pytest.mark.asyncio
async def test_modal_style_payload_without_coordinates_persists(client):
    """Submit payload with null coords but address/city — same as modal after client geocode miss."""
    headers = await _host_headers(client)
    name = f"Modal Payload {uuid.uuid4().hex[:6]}"

    r = await client.post(
        "/api/v1/attractions/",
        headers=headers,
        json={
            "name": name,
            "description": "Host tip and story for guests.",
            "attraction_type": "cultural",
            "city": "Lovran",
            "address": "Lungomare 1",
            "latitude": None,
            "longitude": None,
            "category_tags": [],
            "host_personal_tip": "Visit early morning.",
            "opening_hours": {},
            "contact_info": {},
            "difficulty_level": "easy",
            "seasonal_availability": "year_round",
            "best_months": [],
            "image_gallery": [],
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == name
    assert created["latitude"] is not None
    assert created["longitude"] is not None

    listed = await client.get("/api/v1/attractions/host", headers=headers)
    assert listed.status_code == 200
    names = [a["name"] for a in listed.json()]
    assert name in names
