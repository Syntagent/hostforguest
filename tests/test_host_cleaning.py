"""Host cleaning API: auth, providers, bookings, feedback."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cleaning_endpoints_require_session(async_client: AsyncClient):
    r = await async_client.get("/api/v1/cleaning/providers")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cleaning_happy_path(async_client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    email = f"host_{suffix}@example.com"
    password = "testpassword123"

    reg = await async_client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": password,
            "first_name": "T",
            "last_name": "H",
            "address": "A",
            "city": "Lovran",
        },
    )
    assert reg.status_code == 201, reg.text

    partner_body = {
        "name": f"Test Cleaner {suffix}",
        "partner_type": "cleaning",
        "category": "cleaning",
        "city": "Lovran",
        "email": f"cleaner_{suffix}@example.com",
        "phone": "+385991234567",
        "price_range": "moderate",
        "rate_card": {"studio": 40, "currency": "EUR"},
        "commission_rate": 0.0,
    }
    pr = await async_client.post("/api/v1/partners/", json=partner_body)
    assert pr.status_code == 201, pr.text
    partner_id = pr.json()["id"]
    up = await async_client.put(f"/api/v1/partners/{partner_id}", json={"status": "active"})
    assert up.status_code == 200, up.text

    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["session_token"]
    headers = {"X-Session-Token": token}

    prov = await async_client.get("/api/v1/cleaning/providers", headers=headers)
    assert prov.status_code == 200
    plist = prov.json()["providers"]
    assert any(p["id"] == partner_id for p in plist)

    link = await async_client.post(
        "/api/v1/cleaning/my-cleaners",
        headers=headers,
        json={"partner_id": partner_id},
    )
    assert link.status_code == 201

    mine = await async_client.get("/api/v1/cleaning/my-cleaners", headers=headers)
    assert mine.status_code == 200
    assert len(mine.json()["cleaners"]) >= 1

    book = await async_client.post(
        "/api/v1/cleaning/bookings",
        headers=headers,
        json={"partner_id": partner_id, "intent": "turnover", "notes": "test"},
    )
    assert book.status_code == 201, book.text
    bid = book.json()["id"]

    done = await async_client.patch(
        f"/api/v1/cleaning/bookings/{bid}/status",
        headers=headers,
        json={"status": "completed"},
    )
    assert done.status_code == 200

    fb = await async_client.post(
        f"/api/v1/cleaning/bookings/{bid}/feedback",
        headers=headers,
        json={"rating": 5, "comment": "great"},
    )
    assert fb.status_code == 200

    bad_fb = await async_client.post(
        f"/api/v1/cleaning/bookings/{bid}/feedback",
        headers=headers,
        json={"rating": 4},
    )
    assert bad_fb.status_code == 400
