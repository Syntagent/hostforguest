"""
Sync national event scrapers into local_events and content_updates.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import (
    ContentSource,
    ContentSourceCreate,
    ContentType,
    ContentUpdate,
    SourceStatus,
    SourceType,
)
from app.models.local_event import LocalEvent
from app.scraping.events import sites  # noqa: F401 — register scrapers
from app.scraping.events.dedupe import hash_draft
from app.scraping.events.filters import filter_event_drafts, is_site_chrome_title
from app.scraping.events.registry import get_event_scraper
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.scraping.events.sources import EventSourceDefinition, load_national_event_sources
from app.services.content_scraper_service import ContentScraperService

logger = logging.getLogger(__name__)


class EventIngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_source_for_definition(self, defn: EventSourceDefinition) -> ContentSource:
        row = await self.db.execute(
            select(ContentSource)
            .where(
                or_(
                    ContentSource.url == defn["url"],
                    ContentSource.name == defn["name"],
                )
            )
            .order_by(ContentSource.last_scraped.desc().nullslast())
            .limit(1)
        )
        existing = row.scalars().first()
        if existing:
            if existing.url != defn["url"]:
                existing.url = defn["url"]
            selectors = dict(existing.scraping_selectors or {})
            if selectors.get("slug") != defn["slug"]:
                selectors["slug"] = defn["slug"]
                existing.scraping_selectors = selectors
            return existing

        scraper_svc = ContentScraperService(self.db)
        created = await scraper_svc.create_content_source(
            ContentSourceCreate(
                name=defn["name"],
                url=defn["url"],
                source_type=SourceType.EVENT_CALENDAR,
                region=defn.get("region"),
                city=defn.get("city"),
                content_types=[ContentType.EVENTS],
                scraping_selectors={"slug": defn["slug"]},
                scraping_enabled=True,
                scraping_frequency="daily",
            )
        )
        if not created:
            raise RuntimeError(f"Could not create content source for {defn['slug']}")
        return created

    async def sync_source(self, slug: str) -> Dict[str, Any]:
        sources = {s["slug"]: s for s in load_national_event_sources()}
        defn = sources.get(slug)
        if not defn:
            return {"slug": slug, "success": False, "error": "unknown_slug"}

        content_source = await self.ensure_source_for_definition(defn)
        scraper = get_event_scraper(defn["scraper_class"], defn)

        try:
            async with scraper.policy:
                drafts = await scraper.run()
        except Exception as exc:
            content_source.failed_scrapes = (content_source.failed_scrapes or 0) + 1
            content_source.consecutive_failures = (content_source.consecutive_failures or 0) + 1
            content_source.last_error = str(exc)
            content_source.last_error_at = datetime.utcnow()
            await self.db.commit()
            logger.error("Event scrape failed for %s: %s", slug, exc)
            return {"slug": slug, "success": False, "error": str(exc), "events_upserted": 0}

        upserted = await self._upsert_drafts(content_source, drafts)
        content_source.total_scrapes = (content_source.total_scrapes or 0) + 1
        content_source.successful_scrapes = (content_source.successful_scrapes or 0) + 1
        content_source.consecutive_failures = 0
        content_source.last_scraped = datetime.utcnow()
        content_source.last_error = None
        content_source.content_updates_found = (content_source.content_updates_found or 0) + upserted
        await self.db.commit()

        return {
            "slug": slug,
            "success": True,
            "events_found": len(drafts),
            "events_upserted": upserted,
            "source_id": str(content_source.id),
        }

    def _definitions_to_sync(self, slugs: Optional[List[str]] = None) -> List[EventSourceDefinition]:
        """Choose sources to sync (avoids Gemini 429 bursts in dev)."""
        all_defs = load_national_event_sources()
        if slugs:
            wanted = {s.strip() for s in slugs if s.strip()}
            return [d for d in all_defs if d["slug"] in wanted]
        explicit = os.getenv("EVENTS_SYNC_SLUGS", "").strip()
        if explicit:
            wanted = {s.strip() for s in explicit.split(",") if s.strip()}
            return [d for d in all_defs if d["slug"] in wanted]
        mode = os.getenv("EVENTS_SYNC_MODE", "regional").strip().lower()
        if mode == "all":
            return all_defs
        if mode == "none":
            return []
        # regional default — Kvarner pilot (fewer LLM calls, fewer 429s)
        regional = os.getenv("EVENTS_SYNC_REGION", "Kvarner").strip()
        picked = [d for d in all_defs if (d.get("region") or "").strip() == regional]
        return picked or all_defs[:4]

    async def sync_all_enabled(self, slugs: Optional[List[str]] = None) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        definitions = self._definitions_to_sync(slugs)
        for defn in definitions:
            try:
                results.append(await self.sync_source(defn["slug"]))
            except Exception as exc:
                logger.exception("Event sync crashed for %s", defn["slug"])
                results.append(
                    {"slug": defn["slug"], "success": False, "error": str(exc), "events_upserted": 0}
                )
            delay = float(os.getenv("EVENTS_SYNC_DELAY_SECONDS", "4"))
            if delay > 0:
                await asyncio.sleep(delay)
        ok = sum(1 for r in results if r.get("success"))
        return {
            "sources": len(results),
            "successful": ok,
            "results": results,
            "sync_mode": os.getenv("EVENTS_SYNC_MODE", "regional"),
        }

    async def _upsert_drafts(
        self, source: ContentSource, drafts: List[LocalEventDraft]
    ) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        drafts = filter_event_drafts(drafts)
        seen_external_ids: set[str] = set()

        from app.services.event_llm_date_enrichment import enrich_drafts_for_ingestion

        drafts = await enrich_drafts_for_ingestion(drafts)

        for draft in drafts:
            if not draft.title or len(draft.title) < 3:
                continue
            external_id = draft.external_id or hash_draft(draft)[:40]
            seen_external_ids.add(external_id)
            chash = hash_draft(draft)

            stmt = select(LocalEvent).where(
                and_(
                    LocalEvent.source_id == source.id,
                    LocalEvent.external_id == external_id,
                )
            )
            row = await self.db.execute(stmt)
            existing = row.scalar_one_or_none()

            if existing and existing.content_hash == chash:
                existing.scraped_at = now
                existing.status = "active"
                continue

            content_update = await self._upsert_content_update(source, draft, chash)

            if existing:
                existing.title = draft.title
                existing.description = draft.description or draft.title
                existing.url = draft.url
                existing.start_at = draft.start_at
                existing.end_at = draft.end_at or draft.start_at
                existing.city = draft.city or source.city
                existing.region = draft.region or source.region
                existing.venue_name = draft.venue_name
                existing.tags = draft.tags
                existing.content_hash = chash
                existing.confidence = draft.confidence
                existing.content_update_id = content_update.id if content_update else existing.content_update_id
                existing.scraped_at = now
                existing.updated_at = now
                existing.status = "active"
            else:
                self.db.add(
                    LocalEvent(
                        source_id=source.id,
                        content_update_id=content_update.id if content_update else None,
                        external_id=external_id,
                        title=draft.title[:500],
                        description=(draft.description or draft.title)[:8000],
                        url=draft.url,
                        language=draft.language,
                        start_at=draft.start_at,
                        end_at=draft.end_at or draft.start_at,
                        city=draft.city or source.city,
                        region=draft.region or source.region,
                        venue_name=draft.venue_name,
                        lat=draft.lat,
                        lng=draft.lng,
                        tags=draft.tags,
                        content_hash=chash,
                        confidence=draft.confidence,
                        status="active",
                        scraped_at=now,
                    )
                )
            count += 1

        active = await self.db.execute(
            select(LocalEvent).where(
                and_(
                    LocalEvent.source_id == source.id,
                    LocalEvent.status == "active",
                )
            )
        )
        for ev in active.scalars().all():
            if is_site_chrome_title(ev.title or ""):
                ev.status = "expired"
                ev.updated_at = now
                continue
            if seen_external_ids and ev.external_id not in seen_external_ids:
                ev.status = "expired"
                ev.updated_at = now

        return count

    async def expire_past_local_events(self) -> Dict[str, Any]:
        """Mark active events whose end datetime is clearly in the past."""
        now = datetime.now(timezone.utc)
        expired = 0
        grace = now - timedelta(days=1)
        result = await self.db.execute(
            select(LocalEvent).where(
                and_(
                    LocalEvent.status == "active",
                    LocalEvent.end_at.isnot(None),
                    LocalEvent.end_at < grace,
                )
            )
        )
        for ev in result.scalars().all():
            ev.status = "expired"
            ev.updated_at = now
            expired += 1
        await self.db.commit()
        return {"expired": expired}

    async def purge_site_chrome_events(self) -> Dict[str, Any]:
        """Expire active local_events whose titles are known site navigation chrome."""
        now = datetime.now(timezone.utc)
        expired = 0
        result = await self.db.execute(
            select(LocalEvent).where(LocalEvent.status == "active")
        )
        for ev in result.scalars().all():
            if is_site_chrome_title(ev.title or ""):
                ev.status = "expired"
                ev.updated_at = now
                expired += 1
        await self.db.commit()
        return {"expired": expired}

    async def _upsert_content_update(
        self, source: ContentSource, draft: LocalEventDraft, chash: str
    ) -> Optional[ContentUpdate]:
        stmt = select(ContentUpdate).where(
            and_(
                ContentUpdate.source_id == source.id,
                ContentUpdate.content_hash == chash,
            )
        )
        row = await self.db.execute(stmt)
        existing = row.scalar_one_or_none()
        if existing:
            return existing

        effective = draft.start_at.replace(tzinfo=None) if draft.start_at else None
        expiry = None
        if draft.end_at:
            expiry = draft.end_at.replace(tzinfo=None)
        elif draft.start_at:
            expiry = draft.start_at.replace(tzinfo=None)

        update = ContentUpdate(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.EVENTS,
            title=draft.title[:500],
            content=(draft.description or draft.title)[:8000],
            url=draft.url,
            language=draft.language,
            publication_date=effective,
            effective_date=effective,
            expiry_date=expiry,
            relevant_cities=[draft.city] if draft.city else [],
            relevant_regions=[draft.region] if draft.region else [],
            keywords=draft.tags,
            quality_score=draft.confidence,
            relevance_score=min(0.95, draft.confidence + 0.1),
            status="approved",
            content_hash=chash,
            change_type="new",
        )
        self.db.add(update)
        await self.db.flush()
        return update
