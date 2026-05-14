"""Adaptation studio AI assistant: auth and response shape."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_adaptation_assistant_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake = str(uuid.uuid4())
        r = await client.post(
            f"/api/v1/adaptation/projects/{fake}/assistant",
            json={"message": "What order should I plan trades?"},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_adaptation_assistant_not_found_wrong_host():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:10]
        email = f"ada_{suffix}@example.com"
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

        r = await client.post(
            f"/api/v1/adaptation/projects/{uuid.uuid4()}/assistant",
            headers=headers,
            json={"message": "Hello"},
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_adaptation_assistant_returns_structured_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:10]
        email = f"adb_{suffix}@example.com"
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
            json={"title": f"Test proj {suffix}", "brief": "Refresh bathroom", "style_tags": ["modern"]},
        )
        assert cr.status_code == 201, cr.text
        pid = cr.json()["id"]

        r = await client.post(
            f"/api/v1/adaptation/projects/{pid}/assistant",
            headers=headers,
            json={
                "message": "What phases should I plan for a small bathroom refresh?",
                "history": [],
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data
        assert "phases" in data and isinstance(data["phases"], list)
        assert "cost_orientation" in data
        assert "timeline_overview" in data
        assert "communication_tips" in data
        assert "follow_up_questions" in data
        assert "disclaimer" in data
        assert "ai_used" in data
        assert len(data["reply"]) > 0
