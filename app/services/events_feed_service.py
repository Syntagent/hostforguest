"""
Events and real-time tourism feed: source bootstrap, seeding, and queries.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import String, and_, cast, or_, select
from sqlalchemy.orm import selectinload

from app.models.content_source import (
    CROATIAN_TOURISM_SOURCES,
    ContentSource,
    ContentSourceCreate,
    ContentType,
    ContentUpdate,
    SourceStatus,
    SourceType,
)
from app.services.content_scraper_service import ContentScraperService

logger = logging.getLogger(__name__)

PUBLIC_UPDATE_STATUSES = ("approved", "pending", "integrated")
SYSTEM_SOURCE_NAME = "HostForGuest Kvarner Events"

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


class EventsFeedService:
    def __init__(self, db):
        self.db = db

    async def ensure_tourism_sources(self) -> Dict[str, Any]:
        """Idempotently register Croatian tourism sources for monitoring."""
        scraper = ContentScraperService(self.db)
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
        """Ensure curated Kvarner/Lovran events exist for hosts and guests."""
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
            return {"seeded": 0, "existing": current, "skipped": True}

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
        return {"seeded": seeded, "existing": current, "skipped": False}

    async def get_updates(
        self,
        *,
        city: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        hours: int = 168,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return tourism updates for the dashboard (events-first)."""
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
            out.append(
                {
                    "id": str(update.id),
                    "title": update.title,
                    "content": update.content,
                    "description": update.content,
                    "content_type": update.content_type,
                    "url": update.url,
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
                }
            )
        return out

    async def bootstrap_feed(self, city: Optional[str] = None) -> Dict[str, Any]:
        """Init sources, seed events, return summary + sample count for city."""
        sources = await self.ensure_tourism_sources()
        seed = await self.seed_regional_events_if_needed()
        events = await self.get_updates(city=city, content_types=[ContentType.EVENTS], limit=20)
        return {"sources": sources, "seed": seed, "events_available": len(events)}
