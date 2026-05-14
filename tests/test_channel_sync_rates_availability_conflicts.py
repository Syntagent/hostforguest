"""
Rates / availability push outcomes and timestamp-based inbound conflict behavior.
"""

import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models.channel_integration  # noqa: F401
import app.models.partner  # noqa: F401
from app.db.postgresql.connection import Base
from app.models.channel_integration import ChannelPropertyMapping, ChannelType
from app.models.host import Host
from app.models.partner import BookingStatus, PartnerBooking
from app.services.channel_integration_service import ChannelIntegrationService
from app.services.channel_sync_service import ChannelSyncService


@pytest_asyncio.fixture
async def conflict_db():
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


async def _seed(channel_db: AsyncSession):
    host = Host(
        id=uuid.uuid4(),
        email=f"cf_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        first_name="T",
        last_name="H",
        address="Main 1",
        city="Lovran",
    )
    channel_db.add(host)
    await channel_db.commit()
    await channel_db.refresh(host)
    integ = ChannelIntegrationService(channel_db)
    acc = await integ.connect_booking_com(host.id, "hotel-xyz", "u", "p")
    return host, acc


@pytest.mark.asyncio
async def test_stale_inbound_reservation_does_not_overwrite_newer_state(conflict_db):
    """Older external_updated_at must not apply (same rule as conflict service)."""
    host, acc = await _seed(conflict_db)
    ext_id = "ext-stale-ts"
    newer_ts = datetime.utcnow()
    pb = PartnerBooking(
        id=uuid.uuid4(),
        host_id=host.id,
        guest_group_id=None,
        partner_id=None,
        booking_reference=f"BC-{ext_id}",
        booking_date=datetime.utcnow(),
        booking_amount=200.0,
        currency="EUR",
        commission_rate=0.0,
        commission_amount=0.0,
        status=BookingStatus.CONFIRMED.value,
        source_channel=ChannelType.BOOKING_COM.value,
        external_reservation_id=ext_id,
        external_updated_at=newer_ts,
        local_sync_override=False,
    )
    conflict_db.add(pb)
    await conflict_db.commit()

    sync = ChannelSyncService(conflict_db)
    old_ts = newer_ts - timedelta(days=2)
    await sync.ingest_inbound_reservation(
        acc,
        {
            "external_reservation_id": ext_id,
            "status": "cancelled",
            "total_price": 200,
            "currency": "EUR",
            "external_updated_at": old_ts,
            "raw": {},
        },
    )
    await conflict_db.refresh(pb)
    assert pb.status == BookingStatus.CONFIRMED.value


@pytest.mark.asyncio
@patch(
    "app.services.channel_integration_service.BookingComClient.push_rates",
    new_callable=AsyncMock,
)
async def test_push_rates_failure_records_sync_error(mock_push_rates, conflict_db):
    mock_push_rates.return_value = False
    _, acc = await _seed(conflict_db)
    m = ChannelPropertyMapping(
        id=uuid.uuid4(),
        channel_account_id=acc.id,
        local_entity_type="host",
        local_entity_id=acc.host_id,
        external_room_id="room-1",
        external_rate_id="rate-1",
    )
    conflict_db.add(m)
    await conflict_db.commit()

    sync = ChannelSyncService(conflict_db)
    ok = await sync.push_rates_for_mapping(
        acc.id, m.id, "2026-08-01", "2026-08-03", 99.0, "EUR"
    )
    assert ok is False
    st = await sync.integration.get_sync_state(acc.id)
    assert (st.consecutive_errors or 0) >= 1
    assert st.last_error == "rates push failed"


@pytest.mark.asyncio
@patch(
    "app.services.channel_integration_service.BookingComClient.push_availability",
    new_callable=AsyncMock,
)
async def test_push_availability_failure_records_sync_error(mock_push_avail, conflict_db):
    mock_push_avail.return_value = False
    _, acc = await _seed(conflict_db)
    m = ChannelPropertyMapping(
        id=uuid.uuid4(),
        channel_account_id=acc.id,
        local_entity_type="host",
        local_entity_id=acc.host_id,
        external_room_id="room-2",
    )
    conflict_db.add(m)
    await conflict_db.commit()

    sync = ChannelSyncService(conflict_db)
    ok = await sync.push_availability_for_mapping(
        acc.id, m.id, "2026-09-01", "2026-09-05", 0
    )
    assert ok is False
    st = await sync.integration.get_sync_state(acc.id)
    assert (st.consecutive_errors or 0) >= 1
    assert st.last_error == "availability push failed"
