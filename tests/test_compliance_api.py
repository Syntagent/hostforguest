"""Compliance API — scenarios, items, tenant isolation."""

import uuid

import pytest
from httpx import AsyncClient

from app.services.compliance_service import get_catalog


@pytest.mark.asyncio
async def test_compliance_catalog_public(async_client: AsyncClient):
    r = await async_client.get("/api/v1/compliance/catalog")
    assert r.status_code == 200
    data = r.json()
    assert data["version"]
    assert any(c["id"] == "tax_vat" for c in data["categories"])


@pytest.mark.asyncio
async def test_compliance_me_crud(async_client: AsyncClient, host_token_headers: dict):
    headers = host_token_headers
    r = await async_client.get("/api/v1/compliance/me", headers=headers)
    assert r.status_code == 200
    me = r.json()
    assert "progress" in me
    assert me["catalog_version"] == get_catalog().version

    r2 = await async_client.put(
        "/api/v1/compliance/me/scenarios",
        headers=headers,
        json={"scenarios": {"in_pdv": True, "uses_ota": True}},
    )
    assert r2.status_code == 200
    assert r2.json()["scenarios"]["in_pdv"] is True
    assert len(r2.json()["pdv_regime_rules"]) >= 1

    r_nova = await async_client.put(
        "/api/v1/compliance/me/scenarios",
        headers=headers,
        json={"scenarios": {"novasol": True}},
    )
    assert r_nova.status_code == 200
    assert r_nova.json()["scenarios"]["novasol"] is True
    assert len(r_nova.json()["novasol_regime_rules"]) >= 1

    catalog = get_catalog()
    item_id = catalog.categories[0].items[0].id
    r3 = await async_client.patch(
        f"/api/v1/compliance/me/items/{item_id}",
        headers=headers,
        json={"status": "done"},
    )
    assert r3.status_code == 200
    statuses = {
        i["id"]: i["status"]
        for cat in r3.json()["categories"]
        for i in cat["items"]
    }
    assert statuses[item_id] == "done"


@pytest.mark.asyncio
async def test_compliance_tenant_isolation(async_client: AsyncClient):
    email_a = f"a-{uuid.uuid4().hex[:12]}@example.com"
    email_b = f"b-{uuid.uuid4().hex[:12]}@example.com"
    reg_body = {
        "password": "securepassword123",
        "first_name": "A",
        "last_name": "B",
        "business_name": "Biz",
        "business_type": "apartment",
        "address": "1 St",
        "city": "Lovran",
        "country": "Croatia",
    }

    async def login_token(email: str) -> str:
        await async_client.post("/api/v1/hosts/register", json={**reg_body, "email": email})
        login = await async_client.post(
            "/api/v1/hosts/login",
            json={"email": email, "password": reg_body["password"]},
        )
        assert login.status_code == 200, login.text
        return login.json()["session_token"]

    token_a = await login_token(email_a)
    token_b = await login_token(email_b)
    ha = {"X-Session-Token": token_a}
    hb = {"X-Session-Token": token_b}

    catalog = get_catalog()
    item_id = catalog.categories[0].items[0].id
    await async_client.patch(
        f"/api/v1/compliance/me/items/{item_id}",
        headers=ha,
        json={"status": "done"},
    )

    me_b = await async_client.get("/api/v1/compliance/me", headers=hb)
    assert me_b.status_code == 200
    statuses_b = {
        i["id"]: i["status"]
        for cat in me_b.json()["categories"]
        for i in cat["items"]
    }
    assert statuses_b.get(item_id) in (None, "missing")
