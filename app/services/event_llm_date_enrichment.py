"""
LLM detail-page enrichment for local events missing schedule metadata.

Fetches event detail URLs (when available) and re-extracts dates/times/venues via Gemini.
Used during ingestion and by the undated backfill job.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import ContentUpdate
from app.models.local_event import LocalEvent
from app.scraping.events.policies import PoliteCrawler
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.services.event_extraction_refiner import EventExtractionRefiner
from app.services.event_timing_utils import is_event_past, text_suggests_past_event

logger = logging.getLogger(__name__)


def _detail_enrichment_enabled() -> bool:
    return os.getenv("EVENTS_DETAIL_LLM_ENRICHMENT", "1").strip().lower() not in ("0", "false", "no")


def _text_fallback_enabled() -> bool:
    return os.getenv("EVENTS_LLM_TEXT_FALLBACK", "1").strip().lower() not in ("0", "false", "no")


def _enrich_limit(default: int = 25) -> int:
    try:
        return max(0, int(os.getenv("EVENTS_DETAIL_ENRICH_LIMIT", str(default))))
    except ValueError:
        return default


def _enrich_delay_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("EVENTS_DETAIL_ENRICH_DELAY", "1.5")))
    except ValueError:
        return 1.5


def _accept_enriched(draft: LocalEventDraft) -> bool:
    if not draft.start_at:
        return False
    end = draft.end_at or draft.start_at
    if text_suggests_past_event(draft.title, draft.description):
        return False
    if is_event_past(end_date=end.date(), end_at=end):
        return False
    return True


def merge_event_draft(base: LocalEventDraft, enriched: LocalEventDraft) -> LocalEventDraft:
    """Apply enriched schedule/venue fields onto a listing draft."""
    updates: Dict[str, Any] = {}
    if enriched.start_at:
        updates["start_at"] = enriched.start_at
    if enriched.end_at:
        updates["end_at"] = enriched.end_at
    if enriched.venue_name:
        updates["venue_name"] = enriched.venue_name
    if enriched.city:
        updates["city"] = enriched.city
    if enriched.region:
        updates["region"] = enriched.region
    if enriched.description and len(enriched.description) > len(base.description or ""):
        updates["description"] = enriched.description
    if enriched.tags:
        updates["tags"] = enriched.tags
    if enriched.start_at:
        updates["confidence"] = max(base.confidence, enriched.confidence, 0.82)
    return base.model_copy(update=updates)


class EventLlmDateEnrichmentService:
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        refiner: Optional[EventExtractionRefiner] = None,
        crawler: Optional[PoliteCrawler] = None,
    ):
        self.db = db
        self.refiner = refiner or EventExtractionRefiner()
        self._crawler = crawler
        self._owns_crawler = crawler is None

    async def _get_crawler(self) -> PoliteCrawler:
        if self._crawler is None:
            self._crawler = PoliteCrawler()
        return self._crawler

    async def close(self) -> None:
        if self._owns_crawler and self._crawler is not None:
            await self._crawler.close()
            self._crawler = None

    async def enrich_draft(
        self,
        draft: LocalEventDraft,
        *,
        fetch_detail: bool = True,
        allow_text_fallback: bool = True,
    ) -> LocalEventDraft:
        if draft.start_at or not _detail_enrichment_enabled():
            return draft

        enriched: Optional[LocalEventDraft] = None
        if fetch_detail and draft.url:
            enriched = await self._enrich_from_detail_url(
                url=draft.url,
                title=draft.title,
                city=draft.city,
                region=draft.region,
            )
        if not enriched and allow_text_fallback and _text_fallback_enabled():
            enriched = await self.refiner.extract_metadata_from_text(
                title=draft.title,
                description=draft.description,
                city=draft.city,
                region=draft.region,
            )

        if enriched and enriched.start_at and _accept_enriched(enriched):
            merged = merge_event_draft(draft, enriched)
            if merged.url is None and draft.url:
                merged = merged.model_copy(update={"url": draft.url})
            return merged
        return draft

    async def resolve_enrichment(
        self,
        draft: LocalEventDraft,
    ) -> tuple[LocalEventDraft, str]:
        """Return merged draft and outcome: updated | expired | unresolved."""
        if draft.start_at or not _detail_enrichment_enabled():
            return draft, "unchanged"

        enriched: Optional[LocalEventDraft] = None
        if draft.url:
            enriched = await self._enrich_from_detail_url(
                url=draft.url,
                title=draft.title,
                city=draft.city,
                region=draft.region,
            )
        if not enriched and _text_fallback_enabled():
            enriched = await self.refiner.extract_metadata_from_text(
                title=draft.title,
                description=draft.description,
                city=draft.city,
                region=draft.region,
            )

        if not enriched or not enriched.start_at:
            return draft, "unresolved"
        if not _accept_enriched(enriched):
            return merge_event_draft(draft, enriched), "expired"
        merged = merge_event_draft(draft, enriched)
        if merged.url is None and draft.url:
            merged = merged.model_copy(update={"url": draft.url})
        return merged, "updated"

    async def enrich_drafts(
        self,
        drafts: List[LocalEventDraft],
        *,
        limit: Optional[int] = None,
    ) -> List[LocalEventDraft]:
        if not _detail_enrichment_enabled():
            return drafts
        cap = limit if limit is not None else _enrich_limit()
        if cap <= 0:
            return drafts

        out: List[LocalEventDraft] = []
        enriched_count = 0
        delay = _enrich_delay_seconds()
        for draft in drafts:
            needs = draft.start_at is None
            if needs and enriched_count < cap:
                updated = await self.enrich_draft(draft)
                if updated.start_at and not draft.start_at:
                    enriched_count += 1
                out.append(updated)
                if delay > 0 and enriched_count < cap:
                    await asyncio.sleep(delay)
            else:
                out.append(draft)
        return out

    async def _enrich_from_detail_url(
        self,
        *,
        url: str,
        title: str,
        city: Optional[str],
        region: Optional[str],
    ) -> Optional[LocalEventDraft]:
        crawler = await self._get_crawler()
        try:
            response = await crawler.fetch(url)
            html = response.text
        except Exception as exc:
            logger.warning("Detail fetch failed for %s: %s", url, exc)
            return None

        draft = await self.refiner.extract_detail_from_html(
            html,
            page_url=url,
            hint_title=title,
            city=city,
            region=region,
        )
        return draft

    async def enrich_undated_events(
        self,
        *,
        limit: int = 50,
        dry_run: bool = False,
        city: Optional[str] = None,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        if not self.db:
            raise RuntimeError("Database session required for enrich_undated_events")

        stmt = (
            select(LocalEvent)
            .where(LocalEvent.start_at.is_(None))
            .order_by(LocalEvent.scraped_at.desc())
        )
        if active_only:
            stmt = stmt.where(LocalEvent.status == "active")
        if city and city.strip():
            like = f"%{city.strip()}%"
            stmt = stmt.where(
                or_(
                    LocalEvent.city.ilike(like),
                    LocalEvent.region.ilike(like),
                    LocalEvent.title.ilike(like),
                )
            )
        if limit > 0:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        updated = 0
        expired = 0
        unresolved = 0
        now = datetime.now(timezone.utc)
        delay = _enrich_delay_seconds()

        for ev in rows:
            draft = LocalEventDraft(
                title=ev.title,
                description=ev.description or ev.title,
                url=ev.url,
                city=ev.city,
                region=ev.region,
                venue_name=ev.venue_name,
                tags=list(ev.tags or []),
                confidence=float(ev.confidence or 0.65),
            )
            enriched_draft, outcome = await self.resolve_enrichment(draft)
            if delay > 0:
                await asyncio.sleep(delay)

            if outcome == "unresolved":
                unresolved += 1
                continue

            if outcome == "expired":
                if dry_run:
                    expired += 1
                    continue
                ev.status = "expired"
                ev.updated_at = now
                expired += 1
                continue

            if outcome != "updated" or not enriched_draft.start_at:
                unresolved += 1
                continue

            end = enriched_draft.end_at or enriched_draft.start_at

            if dry_run:
                updated += 1
                continue

            ev.start_at = enriched_draft.start_at
            ev.end_at = end
            ev.venue_name = enriched_draft.venue_name or ev.venue_name
            ev.city = enriched_draft.city or ev.city
            ev.region = enriched_draft.region or ev.region
            if enriched_draft.description and len(enriched_draft.description) > len(ev.description or ""):
                ev.description = enriched_draft.description[:8000]
            ev.confidence = max(float(ev.confidence or 0.0), 0.82)
            ev.updated_at = now
            updated += 1

            if ev.content_update_id:
                cu = await self.db.get(ContentUpdate, ev.content_update_id)
                if cu and enriched_draft.start_at:
                    cu.publication_date = enriched_draft.start_at.replace(tzinfo=None)
                    cu.expiry_date = end.replace(tzinfo=None)
                    cu.updated_at = now.replace(tzinfo=None)

        if not dry_run and (updated or expired):
            await self.db.commit()

        summary = {
            "processed": len(rows),
            "updated": updated,
            "expired": expired,
            "unresolved": unresolved,
            "dry_run": dry_run,
            "city_filter": city,
        }
        logger.info("LLM event date enrichment: %s", summary)
        return summary


async def enrich_drafts_for_ingestion(drafts: List[LocalEventDraft]) -> List[LocalEventDraft]:
    """Convenience wrapper for ingestion pipeline."""
    service = EventLlmDateEnrichmentService()
    try:
        return await service.enrich_drafts(drafts, limit=_enrich_limit(15))
    finally:
        await service.close()
