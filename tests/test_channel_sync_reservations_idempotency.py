"""
Channel sync: idempotent reservation ingest, conflict / override, push paths (mock API).
"""

import os
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models.channel_integration  # noqa: F401
import app.models.guest_group  # noqa: F401
import app.models.partner  # noqa: F401
from app.db.postgresql.connection import Base
from app.models.channel_integration import ChannelPropertyMapping, ChannelType
from app.models.host import Host
from app.models.partner import BookingStatus, PartnerBooking
from app.services.channel_integration_service import ChannelIntegrationService
from app.services.channel_sync_service import ChannelSyncService


@pytest_asyncio.fixture
async def channel_db():
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


async def _seed_host_and_account(session: AsyncSession):
    host = Host(
        id=uuid.uuid4(),
        email=f"ch_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        first_name="T",
        last_name="H",
        address="Main 1",
        city="Lovran",
    )
    session.add(host)
    await session.commit()
    await session.refresh(host)
    integ = ChannelIntegrationService(session)
    acc = await integ.connect_booking_com(host.id, "hotel-xyz", "u", "p")
    return host, acc


@pytest.mark.asyncio
async def test_poll_reservations_idempotent_second_poll_skips_dupes(channel_db):
    _, acc = await _seed_host_and_account(channel_db)
    sync = ChannelSyncService(channel_db)
    r1 = await sync.poll_reservations(acc.id)
    assert r1["ok"] is True
    assert r1["processed"] >= 1
    r2 = await sync.poll_reservations(acc.id)
    assert r2["ok"] is True
    assert r2["processed"] == 0


@pytest.mark.asyncio
async def test_local_sync_override_blocks_inbound_update(channel_db):
    host, acc = await _seed_host_and_account(channel_db)
    ext_id = "ext-override-1"
    pb = PartnerBooking(
        id=uuid.uuid4(),
        host_id=host.id,
        guest_group_id=None,
        partner_id=None,
        booking_reference=f"BC-{ext_id}",
        booking_date=datetime.utcnow(),
        booking_amount=100.0,
        currency="EUR",
        commission_rate=0.0,
        commission_amount=0.0,
        status=BookingStatus.CONFIRMED.value,
        source_channel=ChannelType.BOOKING_COM.value,
        external_reservation_id=ext_id,
        external_updated_at=datetime.utcnow() - timedelta(days=1),
        local_sync_override=True,
    )
    channel_db.add(pb)
    await channel_db.commit()

    sync = ChannelSyncService(channel_db)
    norm = {
        "external_reservation_id": ext_id,
        "status": "cancelled",
        "total_price": 100,
        "currency": "EUR",
        "external_updated_at": datetime.utcnow(),
        "raw": {},
    }
    await sync.ingest_inbound_reservation(acc, norm)
    await channel_db.refresh(pb)
    assert pb.status == BookingStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_push_rates_mock_succeeds(channel_db):
    _, acc = await _seed_host_and_account(channel_db)
    m = ChannelPropertyMapping(
        id=uuid.uuid4(),
        channel_account_id=acc.id,
        local_entity_type="host",
        local_entity_id=acc.host_id,
        external_room_id="room-1",
        external_rate_id="rate-1",
    )
    channel_db.add(m)
    await channel_db.commit()
    sync = ChannelSyncService(channel_db)
    ok = await sync.push_rates_for_mapping(
        acc.id, m.id, "2026-07-01", "2026-07-05", 120.0, "EUR"
    )
    assert ok is True


@pytest.mark.asyncio
async def test_push_availability_mock_succeeds(channel_db):
    _, acc = await _seed_host_and_account(channel_db)
    m = ChannelPropertyMapping(
        id=uuid.uuid4(),
        channel_account_id=acc.id,
        local_entity_type="host",
        local_entity_id=acc.host_id,
        external_room_id="room-1",
    )
    channel_db.add(m)
    await channel_db.commit()
    sync = ChannelSyncService(channel_db)
    ok = await sync.push_availability_for_mapping(
        acc.id, m.id, "2026-06-01", "2026-06-10", 1
    )
    assert ok is True
