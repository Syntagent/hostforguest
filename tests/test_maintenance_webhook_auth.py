"""Maintenance webhook HMAC behavior."""

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_signature_when_secret_set():
    from app.core.config import settings
    from app.main import app

    prev = settings.maintenance_webhook_secret
    settings.maintenance_webhook_secret = "test-webhook-secret"
    try:
        body = {
            "host_id": str(uuid.uuid4()),
            "title": "Test",
            "category": "other",
        }
        raw = json.dumps(body).encode("utf-8")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/maintenance/webhook",
                content=raw,
                headers={"Content-Type": "application/json", "X-Maintenance-Signature": "deadbeef"},
            )
        assert r.status_code == 401
    finally:
        settings.maintenance_webhook_secret = prev


@pytest.mark.asyncio
async def test_webhook_accepts_valid_hmac():
    from app.core.config import settings
    from app.main import app

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
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
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
