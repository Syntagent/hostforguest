"""
Bot-triggered event discovery: freshness checks and async re-scrape pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.local_event import LocalEvent
from app.services.event_ingestion_service import EventIngestionService
from app.services.event_source_discovery_agent import EventSourceDiscoveryAgent
from app.services.events_feed_service import EventsFeedService

logger = logging.getLogger(__name__)

FRESHNESS_HOURS = int(os.getenv("EVENTS_FRESHNESS_HOURS", "24"))
_discovery_tasks: set[asyncio.Task] = set()


class EventDiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.feed = EventsFeedService(db)
        self.ingestion = EventIngestionService(db)
        self.discovery_agent = EventSourceDiscoveryAgent(db)

    async def count_fresh_events(
        self,
        *,
        cities: Optional[Sequence[str]] = None,
        region: Optional[str] = None,
        hours: Optional[int] = None,
    ) -> int:
        """Count active events scraped within freshness window."""
        window = hours if hours is not None else FRESHNESS_HOURS
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window)
        stmt = select(func.count()).select_from(LocalEvent).where(
            and_(
                LocalEvent.status == "active",
                LocalEvent.scraped_at >= cutoff,
            )
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

    async def is_stale_or_empty(
        self,
        *,
        cities: Optional[Sequence[str]] = None,
        region: Optional[str] = None,
    ) -> bool:
        fresh = await self.count_fresh_events(cities=cities, region=region)
        return fresh == 0

    async def discover_and_ingest(
        self,
        city: str,
        *,
        region: Optional[str] = None,
        host_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run discovery agent + ingest sources for a location."""
        from app.models.host import Host, HostProfile

        host = None
        profile = None
        if host_id:
            try:
                import uuid

                hid = uuid.UUID(str(host_id))
                host = await self.db.get(Host, hid)
                if host:
                    row = await self.db.execute(
                        select(HostProfile).where(HostProfile.host_id == hid).limit(1)
                    )
                    profile = row.scalar_one_or_none()
            except (ValueError, TypeError):
                pass

        discovery = await self.discovery_agent.discover_for_location(
            city,
            region=region,
            host=host,
            profile=profile,
        )
        ingest = await self.ingestion.ingest_for_city(city, region=region)
        bootstrap = await self.feed.bootstrap_feed(city=city, sync_mode="regional")
        return {
            "city": city,
            "discovery": discovery,
            "ingest": ingest,
            "bootstrap": bootstrap,
        }

    def trigger_discovery_async(
        self,
        city: str,
        *,
        region: Optional[str] = None,
        host_id: Optional[str] = None,
    ) -> None:
        """Fire-and-forget discovery pipeline (non-blocking for bot responses)."""

        async def _run() -> None:
            from app.core.database import get_async_session
            from app.services.rls_service import RLSService

            try:
                async for db in get_async_session():
                    async with RLSService(db).worker_bypass():
                        svc = EventDiscoveryService(db)
                        result = await svc.discover_and_ingest(
                            city, region=region, host_id=host_id
                        )
                    logger.info(
                        "Async event discovery for %s: ingest_ok=%s",
                        city,
                        result.get("ingest", {}).get("successful"),
                    )
                    break
            except Exception as exc:
                logger.error("Async event discovery failed for %s: %s", city, exc)

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_run())
            _discovery_tasks.add(task)
            task.add_done_callback(_discovery_tasks.discard)
        except RuntimeError:
            logger.warning("No event loop for async discovery; skipping background trigger")

    async def ensure_fresh_events(
        self,
        city: str,
        *,
        region: Optional[str] = None,
        host_id: Optional[str] = None,
        trigger_if_stale: bool = True,
    ) -> Dict[str, Any]:
        """Check freshness; optionally trigger async discovery."""
        cities = [city]
        fresh_count = await self.count_fresh_events(cities=cities, region=region)
        stale = fresh_count == 0
        triggered = False
        if stale and trigger_if_stale:
            self.trigger_discovery_async(city, region=region, host_id=host_id)
            triggered = True
        return {
            "city": city,
            "fresh_count": fresh_count,
            "stale": stale,
            "discovery_triggered": triggered,
            "freshness_hours": FRESHNESS_HOURS,
        }
