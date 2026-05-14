"""
Webhook HMAC verification and replay recovery for channel event logs.
"""

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models.channel_integration  # noqa: F401
import app.models.partner  # noqa: F401
from app.api.v1 import channel_webhooks
from app.db.postgresql.connection import Base
from app.models.channel_integration import (
    ChannelAccount,
    ChannelAccountStatus,
    ChannelEventLog,
    ChannelEventStatus,
    ChannelType,
)
from app.models.host import Host
from app.services.channel_sync_service import ChannelSyncService


@pytest_asyncio.fixture
async def replay_db():
    os.environ["BOOKING_COM_MOCK"] = "true"
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


def test_webhook_hmac_verification_accepts_valid_signature():
    secret = "test-secret"
    body = b'{"hotel_id":"H1","reservations":[{"id":"r1","status":"confirmed"}]}'
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert channel_webhooks._verify_signature(body, sig, secret) is True
    assert channel_webhooks._verify_signature(body, "bad", secret) is False


@pytest.mark.asyncio
async def test_replay_failed_reservation_event(replay_db):
    host = Host(
        id=uuid.uuid4(),
        email=f"rp_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        first_name="T",
        last_name="H",
        address="A",
        city="Lovran",
    )
    replay_db.add(host)
    await replay_db.commit()
    acc = ChannelAccount(
        id=uuid.uuid4(),
        host_id=host.id,
        channel=ChannelType.BOOKING_COM.value,
        status=ChannelAccountStatus.CONNECTED.value,
        external_hotel_id="H1",
    )
    replay_db.add(acc)
    await replay_db.commit()
    payload = {
        "external_reservation_id": "replay-1",
        "status": "confirmed",
        "total_price": 50,
        "currency": "EUR",
        "external_updated_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "raw": {},
    }
    log = ChannelEventLog(
        id=uuid.uuid4(),
        channel_account_id=acc.id,
        idempotency_key="booking_com:replay-1:failed",
        event_type="reservation_upsert",
        direction="inbound",
        payload=payload,
        status=ChannelEventStatus.FAILED.value,
        error_message="simulated",
    )
    replay_db.add(log)
    await replay_db.commit()

    sync = ChannelSyncService(replay_db)
    res = await sync.replay_event_log(log.id, host.id)
    assert res.get("ok") is True
