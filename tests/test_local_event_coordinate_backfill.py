"""Persist city-centroid coordinates on local_events."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import ContentSource, ContentType, SourceType
from app.models.local_event import LocalEvent
from app.services.events_feed_service import EventsFeedService


@pytest.mark.asyncio
async def test_backfill_missing_coordinates_sets_lat_lng(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="TZ Test",
        url="https://example.com/events",
        source_type=SourceType.EVENT_CALENDAR,
        city="Lovran",
        region="Kvarner",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    ev = LocalEvent(
        source_id=source.id,
        external_id="coords-backfill-1",
        title="Opatija jazz night",
        description="Concert",
        city="Opatija",
        region="Kvarner",
        start_at=now + timedelta(days=10),
        content_hash="hash-coords-1",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    summary = await feed.backfill_missing_coordinates(limit=50, dry_run=False)
    assert summary["updated"] >= 1

    row = await db_session.execute(select(LocalEvent).where(LocalEvent.id == ev.id))
    updated = row.scalar_one()
    assert updated.lat is not None
    assert updated.lng is not None


@pytest.mark.asyncio
async def test_local_event_to_dict_includes_backfilled_coords(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="TZ Test 2",
        url="https://example.com/events2",
        source_type=SourceType.EVENT_CALENDAR,
        city="Lovran",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    ev = LocalEvent(
        source_id=source.id,
        external_id="coords-dict-1",
        title="Rijeka concert",
        description="Music",
        city="Rijeka",
        start_at=datetime.now(timezone.utc) + timedelta(days=5),
        content_hash="hash-coords-2",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    payload = feed._local_event_to_dict(ev)
    assert payload["lat"] is not None
    assert payload["lng"] is not None
