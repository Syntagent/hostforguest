"""Health checks for event scrapers."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_, func, select

from app.core.database import get_async_session
from app.models.content_source import ContentSource, ContentType
from app.models.local_event import LocalEvent
from app.scraping.events.sources import load_national_event_sources
from app.services.event_ingestion_service import EventIngestionService

logger = logging.getLogger(__name__)


async def run_event_scraper_health_check() -> Dict[str, Any]:
    """Report sources with zero recent events or consecutive failures."""
    started = datetime.utcnow()
    issues: List[Dict[str, Any]] = []
    async for db in get_async_session():
        cutoff = datetime.utcnow() - timedelta(days=7)
        for defn in load_national_event_sources():
            row = await db.execute(select(ContentSource).where(ContentSource.url == defn["url"]))
            source = row.scalar_one_or_none()
            if not source:
                issues.append({"slug": defn["slug"], "issue": "source_not_registered"})
                continue

            count_stmt = select(func.count(LocalEvent.id)).where(
                and_(
                    LocalEvent.source_id == source.id,
                    LocalEvent.scraped_at >= cutoff,
                )
            )
            count_result = await db.execute(count_stmt)
            events_7d = count_result.scalar() or 0

            if (source.consecutive_failures or 0) >= 3:
                issues.append(
                    {
                        "slug": defn["slug"],
                        "issue": "consecutive_failures",
                        "failures": source.consecutive_failures,
                        "last_error": source.last_error,
                    }
                )
            elif events_7d == 0 and ContentType.EVENTS in (source.content_types or []):
                issues.append({"slug": defn["slug"], "issue": "no_events_7d"})
                if (source.consecutive_failures or 0) < 2:
                    try:
                        await EventIngestionService(db).sync_source(defn["slug"])
                    except Exception as exc:
                        logger.warning("Retry sync failed for %s: %s", defn["slug"], exc)

    return {
        "task": "event_scraper_health",
        "started_at": started.isoformat(),
        "issues": issues,
        "issue_count": len(issues),
    }
