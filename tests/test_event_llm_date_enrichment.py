"""LLM detail-page date enrichment for local events."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import ContentSource, ContentType, SourceType
from app.models.local_event import LocalEvent
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.services.event_extraction_refiner import EventExtractionRefiner
from app.services.event_llm_date_enrichment import (
    EventLlmDateEnrichmentService,
    merge_event_draft,
)


def test_merge_event_draft_applies_schedule():
    base = LocalEventDraft(title="Koncert", description="short", confidence=0.6)
    enriched = LocalEventDraft(
        title="Koncert",
        description="Longer detail copy",
        start_at=datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 15, 22, 0, tzinfo=timezone.utc),
        venue_name="Ljetna pozornica",
        confidence=0.88,
    )
    merged = merge_event_draft(base, enriched)
    assert merged.start_at is not None
    assert merged.start_at.hour == 20
    assert merged.venue_name == "Ljetna pozornica"
    assert merged.confidence >= 0.82


@pytest.mark.asyncio
async def test_enrich_draft_from_detail_html_mocked(monkeypatch):
    service = EventLlmDateEnrichmentService()

    async def fake_fetch(url):
        class Resp:
            text = "<html><body><h1>Kralj Lear</h1><p>15.6.2026 u 20:00</p></body></html>"

        return Resp()

    async def fake_detail(**kwargs):
        return LocalEventDraft(
            title=kwargs.get("title") or "Kralj Lear – predstava",
            description="Predstava",
            url=kwargs.get("url"),
            start_at=datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 6, 15, 22, 0, tzinfo=timezone.utc),
            city="Rijeka",
            venue_name="HNK",
            confidence=0.9,
        )

    monkeypatch.setattr(service, "_enrich_from_detail_url", fake_detail)

    draft = LocalEventDraft(
        title="Kralj Lear – predstava",
        description="Drama",
        url="https://visitrijeka.hr/event/kralj-lear/",
        city="Rijeka",
    )
    out = await service.enrich_draft(draft)
    assert out.start_at is not None
    assert out.venue_name == "HNK"
    await service.close()


@pytest.mark.asyncio
async def test_enrich_undated_local_event_row(db_session: AsyncSession, monkeypatch):
    source = ContentSource(
        id=uuid.uuid4(),
        name="Visit Rijeka",
        url="https://visitrijeka.hr/dogadanja/",
        source_type=SourceType.EVENT_CALENDAR,
        city="Rijeka",
        region="Kvarner",
        content_types=[ContentType.EVENTS],
        scraping_enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    ev = LocalEvent(
        source_id=source.id,
        external_id="llm-enrich-1",
        title="Kralj Lear – predstava",
        description="Shakespeare",
        url="https://visitrijeka.hr/event/kralj-lear-predstava/",
        city="Rijeka",
        content_hash="hash-llm-1",
        status="active",
    )
    db_session.add(ev)
    await db_session.commit()

    service = EventLlmDateEnrichmentService(db_session)

    async def fake_resolve(draft):
        return draft.model_copy(
            update={
                "start_at": datetime(2026, 9, 12, 20, 0, tzinfo=timezone.utc),
                "end_at": datetime(2026, 9, 12, 22, 0, tzinfo=timezone.utc),
                "venue_name": "HNK Rijeka",
                "confidence": 0.9,
            }
        ), "updated"

    monkeypatch.setattr(service, "resolve_enrichment", fake_resolve)
    monkeypatch.setattr("app.services.event_llm_date_enrichment._enrich_delay_seconds", lambda: 0.0)

    summary = await service.enrich_undated_events(limit=10, dry_run=False)
    assert summary["updated"] >= 1

    row = await db_session.execute(select(LocalEvent).where(LocalEvent.id == ev.id))
    updated = row.scalar_one()
    assert updated.start_at is not None
    assert updated.venue_name == "HNK Rijeka"
    await service.close()


@pytest.mark.asyncio
async def test_enrich_drafts_for_ingestion_mocked(monkeypatch):
    from app.services.event_llm_date_enrichment import enrich_drafts_for_ingestion

    async def fake_enrich_drafts(self, drafts, *, limit=None):
        out = []
        for d in drafts:
            if d.start_at:
                out.append(d)
                continue
            out.append(
                d.model_copy(
                    update={
                        "start_at": datetime.now(timezone.utc) + timedelta(days=14),
                        "end_at": datetime.now(timezone.utc) + timedelta(days=14),
                    }
                )
            )
        return out

    monkeypatch.setattr(EventLlmDateEnrichmentService, "enrich_drafts", fake_enrich_drafts)

    async def fake_close(self):
        return None

    monkeypatch.setattr(EventLlmDateEnrichmentService, "close", fake_close)

    drafts = [
        LocalEventDraft(title="Undated fest", description="Fun"),
        LocalEventDraft(
            title="Dated fest",
            description="Ok",
            start_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        ),
    ]
    enriched = await enrich_drafts_for_ingestion(drafts)
    assert len(enriched) == 2
    assert enriched[0].start_at is not None
    assert enriched[1].start_at is not None


def test_parse_llm_single_event_object():
    refiner = EventExtractionRefiner()
    raw = """{"title": "Jazz večer", "start_date": "2026-08-20", "start_time": "21:00", "venue_name": "Ljetna"}"""
    draft = refiner._parse_llm_single_event(
        raw,
        page_url="https://visitrijeka.hr/event/jazz/",
        city="Rijeka",
        region="Kvarner",
        fallback_title="Jazz večer",
    )
    assert draft is not None
    assert draft.start_at is not None
    assert draft.start_at.hour == 21
    assert draft.venue_name == "Ljetna"
