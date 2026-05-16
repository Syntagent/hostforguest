"""Maintenance webhook HMAC behavior."""

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_signature_when_secret_set(async_client: AsyncClient):
    from app.core.config import settings

    prev = settings.maintenance_webhook_secret
    settings.maintenance_webhook_secret = "test-webhook-secret"
    try:
        body = {
            "host_id": str(uuid.uuid4()),
            "title": "Test",
            "category": "other",
        }
        raw = json.dumps(body).encode("utf-8")
        r = await async_client.post(
            "/api/v1/maintenance/webhook",
            content=raw,
            headers={"Content-Type": "application/json", "X-Maintenance-Signature": "deadbeef"},
        )
        assert r.status_code == 401
    finally:
        settings.maintenance_webhook_secret = prev


@pytest.mark.asyncio
async def test_webhook_accepts_valid_hmac(async_client: AsyncClient):
    from app.core.config import settings

    prev = settings.maintenance_webhook_secret
    settings.maintenance_webhook_secret = "signing-key"
    try:
        body = {
            "host_id": str(uuid.uuid4()),
            "title": "OTA signal",
            "category": "plumbing",
        }
        raw = json.dumps(body).encode("utf-8")
        sig = hmac.new(b"signing-key", raw, hashlib.sha256).hexdigest()
        r = await async_client.post(
            "/api/v1/maintenance/webhook",
            content=raw,
            headers={"Content-Type": "application/json", "X-Maintenance-Signature": sig},
        )
        assert r.status_code in (404, 200)
        if r.status_code == 404:
            data = r.json()
            detail = data.get("detail", "")
            assert "host" in str(detail).lower()
    finally:
        settings.maintenance_webhook_secret = prev
