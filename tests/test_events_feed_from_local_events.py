"""EventsFeedService prefers local_events when present."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import ContentSource, ContentType, SourceType
from app.models.local_event import LocalEvent
from app.services.events_feed_service import EventsFeedService


@pytest.mark.asyncio
async def test_get_local_events_returns_dated_rows(db_session: AsyncSession):
    source = ContentSource(
        id=uuid.uuid4(),
        name="Test TZ",
        url="https://test-tz.example/events",
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
        external_id="marunada-2026",
        title="Marunada 2026",
        description="Chestnut festival",
        url="https://test-tz.example/marunada",
        start_at=now + timedelta(days=30),
        end_at=now + timedelta(days=32),
        city="Lovran",
        region="Kvarner",
        tags=["festival"],
        content_hash="abc123",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    feed = EventsFeedService(db_session)
    rows = await feed.get_local_events(city="Lovran", limit=10)
    assert len(rows) >= 1
    assert rows[0].get("start_at")
    assert rows[0]["title"] == "Marunada 2026"
