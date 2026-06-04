"""Scheduled tasks for national local event ingestion."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict

from app.core.database import get_async_session
from app.services.event_ingestion_service import EventIngestionService
from app.services.event_llm_date_enrichment import EventLlmDateEnrichmentService
from app.services.events_feed_service import EventsFeedService

logger = logging.getLogger(__name__)


async def run_daily_event_sync() -> Dict[str, Any]:
    """Sync all enabled national event sources into local_events."""
    started = datetime.utcnow()
    result: Dict[str, Any] = {
        "task": "daily_event_sync",
        "started_at": started.isoformat(),
        "success": False,
    }
    try:
        async for db in get_async_session():
            ingestion = EventIngestionService(db)
            feed = EventsFeedService(db)
            purge = await ingestion.purge_site_chrome_events()
            expired = await ingestion.expire_past_local_events()
            sync = await ingestion.sync_all_enabled()
            dates = await feed.backfill_missing_event_dates(
                limit=500,
                dry_run=False,
                only_missing=True,
                refresh_times=True,
                expire_past=True,
            )
            llm_service = EventLlmDateEnrichmentService(db)
            try:
                llm_dates = await llm_service.enrich_undated_events(
                    limit=int(os.getenv("EVENTS_DETAIL_ENRICH_LIMIT", "25")),
                    dry_run=False,
                )
            finally:
                await llm_service.close()
            coords = await feed.backfill_missing_coordinates(
                limit=500,
                dry_run=False,
                refresh_stale=True,
                geocode_venues=True,
                geocode_venue_limit=20,
            )
            result["purge"] = purge
            result["expired_past"] = expired
            result["date_backfill"] = dates
            result["llm_date_enrichment"] = llm_dates
            result["sync"] = sync
            result["coordinates"] = coords
            result["success"] = sync.get("successful", 0) > 0
            logger.info("Daily event sync: %s/%s sources ok", sync.get("successful"), sync.get("sources"))
    except Exception as exc:
        logger.error("Daily event sync failed: %s", exc)
        result["error"] = str(exc)
    result["completed_at"] = datetime.utcnow().isoformat()
    return result
