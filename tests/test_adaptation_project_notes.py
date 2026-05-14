"""PATCH documentation_notes merges into assumptions_json without dropping bom_lines."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_patch_documentation_notes_preserves_bom_lines_in_assumptions_json():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:10]
        email = f"adn_{suffix}@example.com"
        password = "testpassword123"
        reg = await client.post(
            "/api/v1/hosts/register",
            json={
                "email": email,
                "password": password,
                "first_name": "A",
                "last_name": "B",
                "address": "1 St",
                "city": "Lovran",
            },
        )
        assert reg.status_code == 201, reg.text
        login = await client.post(
            "/api/v1/hosts/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["session_token"]
        headers = {"X-Session-Token": token}

        cr = await client.post(
            "/api/v1/adaptation/projects",
            headers=headers,
            json={"title": f"Notes test {suffix}", "brief": "Kitchen"},
        )
        assert cr.status_code == 201, cr.text
        pid = cr.json()["id"]

        bom_stub = {"lines": [{"description": "tiles", "cost_min_eur": 100}]}
        p1 = await client.patch(
            f"/api/v1/adaptation/projects/{pid}",
            headers=headers,
            json={"assumptions_json": {"bom_lines": bom_stub, "other": 1}},
        )
        assert p1.status_code == 200, p1.text
        assert p1.json()["assumptions_json"]["bom_lines"] == bom_stub

        p2 = await client.patch(
            f"/api/v1/adaptation/projects/{pid}",
            headers=headers,
            json={"documentation_notes": "Access via side gate. Call Mario."},
        )
        assert p2.status_code == 200, p2.text
        aj = p2.json()["assumptions_json"]
        assert aj["project_documentation"] == "Access via side gate. Call Mario."
        assert aj["bom_lines"] == bom_stub
        assert aj["other"] == 1


@pytest.mark.asyncio
async def test_suggest_suppliers_includes_discovery():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:10]
        email = f"ads_{suffix}@example.com"
        password = "testpassword123"
        reg = await client.post(
            "/api/v1/hosts/register",
            json={
                "email": email,
                "password": password,
                "first_name": "A",
                "last_name": "B",
                "address": "1 St",
                "city": "Lovran",
            },
        )
        assert reg.status_code == 201, reg.text
        login = await client.post(
            "/api/v1/hosts/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["session_token"]
        headers = {"X-Session-Token": token}

        cr = await client.post(
            "/api/v1/adaptation/projects",
            headers=headers,
            json={"title": f"Sup {suffix}"},
        )
        assert cr.status_code == 201, cr.text
        pid = cr.json()["id"]

        r = await client.post(
            f"/api/v1/adaptation/projects/{pid}/suggest-suppliers",
            headers=headers,
            json={"bom_category": "tiles"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "partners" in data
        assert "discovery" in data
        assert "host_has_coordinates" in data["discovery"]
        assert "sort_explanation" in data["discovery"]
        assert isinstance(data["discovery"]["any_distance_unknown"], bool)
