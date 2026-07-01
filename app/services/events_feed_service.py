"""
Events and real-time tourism feed: source bootstrap, seeding, and queries.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.content_source import (
    CROATIAN_TOURISM_SOURCES,
    ContentSource,
    ContentSourceCreate,
    ContentType,
    ContentUpdate,
    SourceType,
)
from app.models.local_event import LocalEvent
from app.scraping.events.filters import is_site_chrome_title
from app.services.content_scraper_service import ContentScraperService
from app.services.host_offerings_for_guest import guest_safe_realtime_update
from app.services.event_geo_utils import (
    coords_match_stale_centroid,
    resolve_city_coords,
    resolve_event_location_coords,
)

logger = logging.getLogger(__name__)

PUBLIC_UPDATE_STATUSES = ("approved", "pending", "integrated")
SYSTEM_SOURCE_NAME = "HostForGuest Kvarner Events"
DEMO_SEED_ENV = "EVENTS_USE_DEMO_SEED"

LOVRAN_EVENTS_SEED: List[Dict[str, Any]] = [
    {
        "title": "Marunada — Lovran chestnut festival",
        "content": "Autumn celebration of Lovran chestnuts with tastings, music, and stalls in the old town.",
        "url": "https://tz-lovran.hr",
        "relevant_cities": ["Lovran"],
        "relevant_regions": ["Kvarner"],
        "keywords": ["marunada", "festival", "jesen"],
    },
    {
        "title": "Lovran cherry days",
        "content": "Spring cherry season events and local produce along the Lungomare.",
        "url": "https://tz-lovran.hr",
        "relevant_cities": ["Lovran"],
        "relevant_regions": ["Kvarner"],
        "keywords": ["cherry", "season", "food"],
    },
    {
        "title": "Opatija Riviera open-air concerts",
        "content": "Summer concerts and cultural evenings on the Opatija waterfront.",
        "url": "https://www.opatija-tourism.hr",
        "relevant_cities": ["Opatija"],
        "relevant_regions": ["Kvarner"],
        "keywords": ["music", "concert", "summer"],
    },
    {
        "title": "Istria truffle & wine weekends",
        "content": "Weekend tastings and cellar events across Istria — easy day trip from Lovran.",
        "url": "https://www.istra.hr",
        "relevant_cities": ["Lovran", "Opatija"],
        "relevant_regions": ["Istria", "Kvarner"],
        "keywords": ["wine", "truffle", "gastro"],
    },
    {
        "title": "Kvarner regatta & waterfront fairs",
        "content": "Harbour fairs and sailing events along the Kvarner coast.",
        "url": "https://www.kvarner.hr",
        "relevant_cities": ["Lovran", "Rijeka"],
        "relevant_regions": ["Kvarner"],
        "keywords": ["regatta", "sea", "fair"],
    },
]


def _demo_seed_enabled() -> bool:
    return os.getenv(DEMO_SEED_ENV, "").strip().lower() in ("1", "true", "yes")


class EventsFeedService:
    def __init__(self, db):
        self.db = db

    async def ensure_tourism_sources(self) -> Dict[str, Any]:
        """Idempotently register Croatian tourism sources for monitoring."""
        from app.services.event_ingestion_service import EventIngestionService
        from app.scraping.events.sources import load_national_event_sources

        scraper = ContentScraperService(self.db)
        ingestion = EventIngestionService(self.db)
        created = 0
        existing = 0
        for source_config in CROATIAN_TOURISM_SOURCES:
            url = source_config["url"]
            row = await self.db.execute(select(ContentSource).where(ContentSource.url == url))
            if row.scalar_one_or_none():
                existing += 1
                continue
            data = ContentSourceCreate(**source_config)
            source = await scraper.create_content_source(data)
            if source:
                created += 1
        for defn in load_national_event_sources():
            row = await self.db.execute(select(ContentSource).where(ContentSource.url == defn["url"]))
            if not row.scalar_one_or_none():
                await ingestion.ensure_source_for_definition(defn)
                created += 1
            else:
                existing += 1
        return {"created": created, "already_present": existing, "total_configured": len(CROATIAN_TOURISM_SOURCES)}

    async def _get_or_create_system_source(self) -> ContentSource:
        row = await self.db.execute(
            select(ContentSource).where(ContentSource.name == SYSTEM_SOURCE_NAME)
        )
        source = row.scalar_one_or_none()
        if source:
            return source
        scraper = ContentScraperService(self.db)
        source = await scraper.create_content_source(
            ContentSourceCreate(
                name=SYSTEM_SOURCE_NAME,
                url="https://hostforguest.syntagent.com/events-feed",
                source_type=SourceType.EVENT_CALENDAR,
                region="Kvarner",
                city="Lovran",
                content_types=[ContentType.EVENTS],
                scraping_selectors={},
                scraping_enabled=False,
            )
        )
        if not source:
            raise RuntimeError("Could not create system events source")
        return source

    async def seed_regional_events_if_needed(self, min_count: int = 3) -> Dict[str, Any]:
        """Demo seed only when EVENTS_USE_DEMO_SEED=1."""
        if not _demo_seed_enabled():
            return {"seeded": 0, "existing": 0, "skipped": True, "demo_seed": False}

        cutoff = datetime.utcnow() - timedelta(days=30)
        stmt = select(ContentUpdate).where(
            and_(
                ContentUpdate.content_type == ContentType.EVENTS,
                ContentUpdate.created_at >= cutoff,
                ContentUpdate.status.in_(PUBLIC_UPDATE_STATUSES),
            )
        )
        result = await self.db.execute(stmt)
        current = len(result.scalars().all())
        if current >= min_count:
            return {"seeded": 0, "existing": current, "skipped": True, "demo_seed": True}

        source = await self._get_or_create_system_source()
        seeded = 0
        for item in LOVRAN_EVENTS_SEED:
            dup = await self.db.execute(
                select(ContentUpdate).where(
                    and_(
                        ContentUpdate.source_id == source.id,
                        ContentUpdate.title == item["title"],
                    )
                )
            )
            if dup.scalar_one_or_none():
                continue
            update = ContentUpdate(
                source_id=source.id,
                content_type=ContentType.EVENTS,
                title=item["title"],
                content=item["content"],
                url=item.get("url"),
                relevant_cities=item.get("relevant_cities", []),
                relevant_regions=item.get("relevant_regions", []),
                keywords=item.get("keywords", []),
                quality_score=0.92,
                relevance_score=0.9,
                status="approved",
            )
            self.db.add(update)
            seeded += 1
        await self.db.commit()
        return {"seeded": seeded, "existing": current, "skipped": False, "demo_seed": True}

    @staticmethod
    def _utc_start(d: date) -> datetime:
        return datetime.combine(d, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _utc_end(d: date) -> datetime:
        return datetime.combine(d, time.max, tzinfo=timezone.utc)

    def _local_event_to_dict(
        self,
        ev: LocalEvent,
        *,
        omit_internal_scores: bool = True,
    ) -> Dict[str, Any]:
        start = ev.start_at
        end = ev.end_at
        lat, lng = ev.lat, ev.lng
        if lat is None or lng is None:
            clat, clng = resolve_event_location_coords(
                ev.city,
                venue_name=ev.venue_name,
                title=ev.title,
                allow_geocode=False,
            )
            if clat is not None and clng is not None:
                lat, lng = clat, clng
        return guest_safe_realtime_update(
            {
                "id": str(ev.id),
                "title": ev.title,
                "content": ev.description,
                "description": ev.description,
                "content_type": ev.event_type or ContentType.EVENTS,
                "event_type": ev.event_type,
                "age_group": ev.age_group,
                "price": ev.price,
                "address": ev.address,
                "url": ev.url,
                "language": ev.language,
                "start_at": start.isoformat() if start else None,
                "end_at": end.isoformat() if end else None,
                "publication_date": start.isoformat() if start else None,
                "venue_name": ev.venue_name,
                "lat": lat,
                "lng": lng,
                "relevant_cities": [ev.city] if ev.city else [],
                "relevant_regions": [ev.region] if ev.region else [],
                "keywords": ev.tags or [],
                "tags": ev.tags or [],
                "is_recurring": bool(ev.is_recurring),
                "recurrence": ev.recurrence,
                "quality_score": ev.confidence or 0.75,
                "relevance_score": min(0.95, (ev.confidence or 0.75) + 0.05),
                "scraped_at": (ev.scraped_at or ev.created_at).isoformat(),
                "created_at": (ev.scraped_at or ev.created_at).isoformat(),
                "source": ev.source.name if ev.source else None,
                "source_name": ev.source.name if ev.source else None,
                "city": ev.city,
                "region": ev.region,
                "is_demo_seed": False,
            },
            omit_internal_scores=omit_internal_scores,
        )

    async def count_active_local_events(
        self,
        *,
        cities: Optional[Sequence[str]] = None,
        region: Optional[str] = None,
        hours: int = 720,
    ) -> int:
        """Fast count for bootstrap skip decisions."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(func.count()).select_from(LocalEvent).where(
            LocalEvent.status == "active",
            or_(
                LocalEvent.scraped_at >= cutoff,
                LocalEvent.start_at >= cutoff,
                LocalEvent.created_at >= cutoff,
            ),
        )
        city_filters = []
        for city in cities or []:
            c = str(city).strip()
            if not c:
                continue
            like = f"%{c}%"
            city_filters.append(
                or_(
                    LocalEvent.city.ilike(like),
                    LocalEvent.region.ilike(like),
                )
            )
        if region and str(region).strip():
            city_filters.append(LocalEvent.region.ilike(f"%{region.strip()}%"))
        if city_filters:
            stmt = stmt.where(or_(*city_filters))
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_local_events_batch(
        self,
        *,
        cities: Optional[Sequence[str]] = None,
        region: Optional[str] = None,
        hours: int = 720,
        limit: int = 120,
        stay_start: Optional[date] = None,
        stay_end: Optional[date] = None,
        active_only: bool = True,
        omit_internal_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """Single query for guest recommendations across stay cities / region."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(LocalEvent)
            .options(selectinload(LocalEvent.source))
            .where(
                or_(
                    LocalEvent.scraped_at >= cutoff,
                    LocalEvent.start_at >= cutoff,
                    LocalEvent.created_at >= cutoff,
                )
            )
        )
        if active_only:
            stmt = stmt.where(LocalEvent.status == "active")

        geo_filters = []
        for city in cities or []:
            c = str(city).strip()
            if not c:
                continue
            like = f"%{c}%"
            geo_filters.append(
                or_(
                    LocalEvent.city.ilike(like),
                    LocalEvent.region.ilike(like),
                    LocalEvent.title.ilike(like),
                    LocalEvent.description.ilike(like),
                )
            )
        if region and str(region).strip():
            geo_filters.append(LocalEvent.region.ilike(f"%{region.strip()}%"))
        if geo_filters:
            stmt = stmt.where(or_(*geo_filters))

        if stay_start and stay_end:
            window_start = self._utc_start(stay_start - timedelta(days=7))
            window_end = self._utc_end(stay_end + timedelta(days=21))
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=21)
            today_start = self._utc_start(date.today())
            stmt = stmt.where(
                or_(
                    LocalEvent.end_at.is_(None),
                    LocalEvent.end_at >= today_start - timedelta(days=1),
                )
            )
            stmt = stmt.where(
                or_(
                    and_(
                        LocalEvent.start_at.isnot(None),
                        LocalEvent.start_at <= window_end,
                        or_(LocalEvent.end_at.is_(None), LocalEvent.end_at >= window_start),
                    ),
                    and_(
                        LocalEvent.start_at.is_(None),
                        LocalEvent.scraped_at >= recent_cutoff,
                    ),
                )
            )

        stmt = stmt.order_by(
            LocalEvent.start_at.asc().nullslast(),
            LocalEvent.scraped_at.desc(),
        ).limit(limit)
        result = await self.db.execute(stmt)
        out: List[Dict[str, Any]] = []
        for ev in result.scalars().all():
            if is_site_chrome_title(ev.title or ""):
                continue
            out.append(self._local_event_to_dict(ev, omit_internal_scores=omit_internal_scores))
        return out

    async def get_local_events(
        self,
        *,
        city: Optional[str] = None,
        hours: int = 720,
        limit: int = 50,
        active_only: bool = True,
        omit_internal_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query normalized local_events (primary feed for insights/guests)."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(LocalEvent)
            .options(selectinload(LocalEvent.source))
            .where(
                or_(
                    LocalEvent.scraped_at >= cutoff,
                    LocalEvent.start_at >= cutoff,
                    LocalEvent.created_at >= cutoff,
                )
            )
        )
        if active_only:
            stmt = stmt.where(LocalEvent.status == "active")
        if city:
            city_like = f"%{city.strip()}%"
            stmt = stmt.where(
                or_(
                    LocalEvent.city.ilike(city_like),
                    LocalEvent.region.ilike(city_like),
                    LocalEvent.title.ilike(city_like),
                    LocalEvent.description.ilike(city_like),
                )
            )
        stmt = stmt.order_by(
            LocalEvent.start_at.desc().nullslast(),
            LocalEvent.scraped_at.desc(),
        ).limit(limit)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        out: List[Dict[str, Any]] = []
        for ev in rows:
            if is_site_chrome_title(ev.title or ""):
                continue
            out.append(self._local_event_to_dict(ev, omit_internal_scores=omit_internal_scores))
        return out

    async def get_updates(
        self,
        *,
        city: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        hours: int = 168,
        limit: int = 50,
        omit_internal_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return events: prefer local_events, fallback to content_updates."""
        if content_types and ContentType.EVENTS not in content_types:
            return await self._get_content_updates(
                city=city,
                content_types=content_types,
                hours=hours,
                limit=limit,
                omit_internal_scores=omit_internal_scores,
            )

        local = await self.get_local_events(
            city=city,
            hours=max(hours, 168),
            limit=limit,
            omit_internal_scores=omit_internal_scores,
        )
        if local:
            return local
        return await self._get_content_updates(
            city=city,
            content_types=[ContentType.EVENTS],
            hours=hours,
            limit=limit,
            omit_internal_scores=omit_internal_scores,
        )

    async def _get_content_updates(
        self,
        *,
        city: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        hours: int = 168,
        limit: int = 50,
        omit_internal_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(ContentUpdate)
            .options(selectinload(ContentUpdate.source))
            .join(ContentSource, ContentUpdate.source_id == ContentSource.id)
            .where(
                and_(
                    ContentUpdate.created_at >= cutoff,
                    ContentUpdate.status.in_(PUBLIC_UPDATE_STATUSES),
                )
            )
        )
        if city:
            city_like = f"%{city.strip()}%"
            stmt = stmt.where(
                or_(
                    ContentSource.city.ilike(city_like),
                    ContentSource.region.ilike(city_like),
                    ContentUpdate.title.ilike(city_like),
                    ContentUpdate.content.ilike(city_like),
                    cast(ContentUpdate.relevant_cities, String).ilike(f"%{city.strip()}%"),
                )
            )
        if content_types:
            stmt = stmt.where(ContentUpdate.content_type.in_(content_types))

        stmt = stmt.order_by(
            ContentUpdate.relevance_score.desc().nullslast(),
            ContentUpdate.created_at.desc(),
        ).limit(limit)
        result = await self.db.execute(stmt)
        updates = result.scalars().all()

        out: List[Dict[str, Any]] = []
        for update in updates:
            is_demo = update.source and update.source.name == SYSTEM_SOURCE_NAME
            out.append(
                guest_safe_realtime_update(
                    {
                        "id": str(update.id),
                        "title": update.title,
                        "content": update.content,
                        "description": update.content,
                        "content_type": update.content_type,
                        "url": update.url,
                        "start_at": update.effective_date.isoformat() if update.effective_date else None,
                        "end_at": update.expiry_date.isoformat() if update.expiry_date else None,
                        "publication_date": update.publication_date.isoformat()
                        if update.publication_date
                        else None,
                        "relevant_cities": update.relevant_cities or [],
                        "relevant_regions": update.relevant_regions or [],
                        "keywords": update.keywords or [],
                        "quality_score": update.quality_score or 0.0,
                        "relevance_score": update.relevance_score or 0.0,
                        "created_at": update.created_at.isoformat(),
                        "source": update.source.name if update.source else None,
                        "source_name": update.source.name if update.source else None,
                        "is_demo_seed": bool(is_demo),
                    },
                    omit_internal_scores=omit_internal_scores,
                )
            )
        return out

    async def get_source_health(self) -> List[Dict[str, Any]]:
        """Per-source scrape health for Insights panel."""
        stmt = select(ContentSource).where(ContentSource.scraping_enabled == True)
        result = await self.db.execute(stmt)
        sources = result.scalars().all()
        health: List[Dict[str, Any]] = []
        for s in sources:
            if ContentType.EVENTS not in (s.content_types or []):
                continue
            failures = s.consecutive_failures or 0
            hint = None
            if failures >= 3:
                hint = f"Last sync failed for {s.name} — we're reviewing the scraper."
            elif failures > 0:
                hint = f"Recent scrape issues for {s.name}; retry Sync sources."
            health.append(
                {
                    "source_id": str(s.id),
                    "name": s.name,
                    "url": s.url,
                    "status": s.status,
                    "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
                    "consecutive_failures": failures,
                    "last_error": (s.last_error or "")[:200] or None,
                    "total_scrapes": s.total_scrapes or 0,
                    "successful_scrapes": s.successful_scrapes or 0,
                    "maintenance_hint": hint,
                }
            )
        return health

    async def backfill_missing_coordinates(
        self,
        *,
        limit: int = 500,
        dry_run: bool = False,
        refresh_stale: bool = True,
        geocode_venues: bool = False,
        geocode_venue_limit: int = 25,
    ) -> Dict[str, Any]:
        """Persist coordinates on local_events (city centroids + optional venue geocode)."""
        stmt = select(LocalEvent).order_by(LocalEvent.updated_at.asc())
        if limit > 0:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        updated = 0
        unresolved = 0
        skipped = 0
        geocoded = 0
        for ev in rows:
            missing = ev.lat is None or ev.lng is None
            stale = refresh_stale and coords_match_stale_centroid(ev.city, ev.lat, ev.lng)
            if not missing and not stale:
                skipped += 1
                continue

            allow_geocode = (
                geocode_venues
                and geocoded < geocode_venue_limit
                and bool((ev.venue_name or "").strip())
            )
            clat, clng = resolve_event_location_coords(
                ev.city,
                venue_name=ev.venue_name if allow_geocode else None,
                title=ev.title if allow_geocode else None,
                allow_geocode=allow_geocode,
            )
            if allow_geocode and clat is not None:
                geocoded += 1
            if clat is None or clng is None:
                clat, clng = resolve_city_coords(ev.city)
            if clat is None or clng is None:
                unresolved += 1
                continue
            if (
                not missing
                and not stale
                and ev.lat == clat
                and ev.lng == clng
            ):
                skipped += 1
                continue

            if dry_run:
                updated += 1
                continue
            ev.lat = clat
            ev.lng = clng
            ev.updated_at = datetime.now(timezone.utc)
            updated += 1

        if not dry_run and updated:
            await self.db.commit()

        summary = {
            "processed": len(rows),
            "updated": updated,
            "skipped": skipped,
            "unresolved": unresolved,
            "dry_run": dry_run,
            "refresh_stale": refresh_stale,
            "geocode_venues": geocode_venues,
            "geocoded_venues": geocoded,
        }
        logger.info("Local event coordinate backfill: %s", summary)
        return summary

    async def backfill_missing_event_dates(
        self,
        *,
        limit: int = 500,
        dry_run: bool = False,
        only_missing: bool = True,
        refresh_times: bool = False,
        expire_past: bool = True,
        city: Optional[str] = None,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        """Infer start_at/end_at from title/description for local_events."""
        from app.models.content_source import ContentUpdate
        from app.services.event_timing_utils import infer_dates_from_blob, is_event_past, text_suggests_past_event

        stmt = select(LocalEvent).order_by(LocalEvent.updated_at.asc())
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
        skipped = 0
        unresolved = 0
        expired = 0
        now = datetime.now(timezone.utc)

        def _utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        def _is_noon_placeholder(dt: Optional[datetime]) -> bool:
            if not dt:
                return True
            return dt.hour == 12 and dt.minute == 0

        for ev in rows:
            missing_start = ev.start_at is None
            missing_end = ev.end_at is None
            existing_start = _utc(ev.start_at) if ev.start_at else None
            existing_end = _utc(ev.end_at) if ev.end_at else None
            can_refresh_time = (
                refresh_times
                and existing_start is not None
                and _is_noon_placeholder(existing_start)
            )

            if only_missing and not missing_start and not missing_end and not can_refresh_time:
                skipped += 1
                continue

            inferred_start, inferred_end = infer_dates_from_blob(ev.title or "", ev.description or "")
            if not inferred_start:
                if missing_start:
                    unresolved += 1
                else:
                    skipped += 1
                continue

            new_start = _utc(inferred_start)
            new_end = _utc(inferred_end or inferred_start)

            if existing_start is not None:
                if existing_start.date() == new_start.date():
                    if can_refresh_time and (new_start.hour != 12 or new_start.minute != 0):
                        pass
                    else:
                        new_start = existing_start
                elif only_missing:
                    skipped += 1
                    continue

            if existing_end is not None and not missing_end:
                if existing_end.date() >= new_start.date() and not can_refresh_time:
                    new_end = existing_end
                elif can_refresh_time and existing_end.date() == new_end.date():
                    new_end = new_end.replace(
                        year=existing_end.year,
                        month=existing_end.month,
                        day=existing_end.day,
                    )

            unchanged = (
                existing_start == new_start
                and existing_end == new_end
                and not missing_start
                and not missing_end
            )
            if unchanged:
                skipped += 1
                continue

            should_expire = expire_past and (
                text_suggests_past_event(ev.title or "", ev.description or "")
                or is_event_past(end_date=new_end.date(), end_at=new_end)
            )

            if dry_run:
                if should_expire:
                    expired += 1
                else:
                    updated += 1
                continue

            if should_expire:
                ev.status = "expired"
                ev.updated_at = now
                expired += 1
            else:
                ev.start_at = new_start
                ev.end_at = new_end
                ev.confidence = max(float(ev.confidence or 0.0), 0.72)
                ev.updated_at = now
                updated += 1

            if ev.content_update_id:
                cu = await self.db.get(ContentUpdate, ev.content_update_id)
                if cu:
                    cu.publication_date = new_start.replace(tzinfo=None)
                    if should_expire:
                        cu.expiry_date = new_end.replace(tzinfo=None)
                    cu.updated_at = now.replace(tzinfo=None)

        if not dry_run and (updated or expired):
            await self.db.commit()

        summary = {
            "processed": len(rows),
            "updated": updated,
            "expired": expired,
            "skipped": skipped,
            "unresolved": unresolved,
            "dry_run": dry_run,
            "only_missing": only_missing,
            "refresh_times": refresh_times,
            "city_filter": city,
        }
        logger.info("Local event date backfill: %s", summary)
        return summary

    async def bootstrap_feed(
        self,
        city: Optional[str] = None,
        *,
        sync_mode: Optional[str] = None,
        slugs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Init sources, optional demo seed, sync national scrapers, return summary."""
        import os

        from app.services.event_ingestion_service import EventIngestionService

        if sync_mode:
            os.environ["EVENTS_SYNC_MODE"] = sync_mode

        ingestion = EventIngestionService(self.db)
        sources = await self.ensure_tourism_sources()
        seed = await self.seed_regional_events_if_needed()
        purge = await ingestion.purge_site_chrome_events()
        expired = await ingestion.expire_past_local_events()
        sync = await ingestion.sync_all_enabled(slugs=slugs)
        coords = await self.backfill_missing_coordinates(
            limit=500,
            dry_run=False,
            refresh_stale=True,
            geocode_venues=True,
            geocode_venue_limit=15,
        )
        events = await self.get_updates(city=city, content_types=[ContentType.EVENTS], limit=20)
        return {
            "sources": sources,
            "seed": seed,
            "purge": purge,
            "expired_past": expired,
            "sync": sync,
            "coordinates": coords,
            "events_available": len(events),
        }
