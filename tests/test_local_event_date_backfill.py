"""Backfill start_at/end_at on local_events from Croatian copy."""

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
async def test_backfill_missing_event_dates_from_title(db_session: AsyncSession):
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

    ev = LocalEvent(
        source_id=source.id,
        external_id="date-backfill-1",
        title="Koncert u Lovranu 15.6.2026 u 19:00",
        description="Glazbena večer na trgu.",
        city="Lovran",
        region="Kvarner",
        content_hash="hash-date-1",
        status="active",
        confidence=0.55,
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    summary = await feed.backfill_missing_event_dates(limit=50, dry_run=False)
    assert summary["updated"] >= 1

    row = await db_session.execute(select(LocalEvent).where(LocalEvent.id == ev.id))
    updated = row.scalar_one()
    assert updated.start_at is not None
    assert updated.start_at.year == 2026
    assert updated.start_at.month == 6
    assert updated.start_at.day == 15
    assert updated.start_at.hour == 19
    assert updated.end_at is not None
    assert updated.confidence >= 0.72


@pytest.mark.asyncio
async def test_backfill_skips_when_dates_already_set(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="TZ Test 2",
        url="https://example.com/events2",
        source_type=SourceType.EVENT_CALENDAR,
        city="Opatija",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    start = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    ev = LocalEvent(
        source_id=source.id,
        external_id="date-backfill-2",
        title="Festival 1.8.2026",
        description="Already dated",
        city="Opatija",
        start_at=start,
        end_at=start,
        content_hash="hash-date-2",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    summary = await feed.backfill_missing_event_dates(limit=50, dry_run=False, only_missing=True)
    assert summary["skipped"] >= 1
    assert summary["updated"] == 0


@pytest.mark.asyncio
async def test_backfill_expires_inferred_past_event(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="TZ Test 3",
        url="https://example.com/events3",
        source_type=SourceType.EVENT_CALENDAR,
        city="Rijeka",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    ev = LocalEvent(
        source_id=source.id,
        external_id="date-backfill-3",
        title="Stari koncert 10.1.2024",
        description="Prošla godina",
        city="Rijeka",
        content_hash="hash-date-3",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    summary = await feed.backfill_missing_event_dates(limit=50, dry_run=False, expire_past=True)
    assert summary["expired"] >= 1

    row = await db_session.execute(select(LocalEvent).where(LocalEvent.id == ev.id))
    updated = row.scalar_one()
    assert updated.status == "expired"


@pytest.mark.asyncio
async def test_backfill_refresh_times_on_noon_placeholder(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="TZ Test 4",
        url="https://example.com/events4",
        source_type=SourceType.EVENT_CALENDAR,
        city="Lovran",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    future = datetime.now(timezone.utc) + timedelta(days=30)
    noon = future.replace(hour=12, minute=0, second=0, microsecond=0)
    day = noon.day
    month = noon.month
    year = noon.year
    ev = LocalEvent(
        source_id=source.id,
        external_id="date-backfill-4",
        title=f"Večer u 20:00 {day}.{month}.{year}",
        description="Sat u naslovu",
        city="Lovran",
        start_at=noon,
        end_at=noon,
        content_hash="hash-date-4",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    summary = await feed.backfill_missing_event_dates(
        limit=50,
        dry_run=False,
        only_missing=False,
        refresh_times=True,
    )
    assert summary["updated"] >= 1

    row = await db_session.execute(select(LocalEvent).where(LocalEvent.id == ev.id))
    updated = row.scalar_one()
    assert updated.start_at is not None
    assert updated.start_at.hour == 20
