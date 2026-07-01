"""
Long-running worker: sync national event sources and refresh coordinates.

Run: python -m app.tasks.event_sync_runner

Environment:
  EVENT_SYNC_INTERVAL_SEC (default 86400 — daily)
  EVENT_COORD_BACKFILL_INTERVAL_SEC (default 604800 — weekly)
  EVENT_SYNC_HEARTBEAT_PATH (default /tmp/event_sync_heartbeat)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_HEARTBEAT_PATH = os.environ.get("EVENT_SYNC_HEARTBEAT_PATH", "/tmp/event_sync_heartbeat")
_LAST_BACKFILL_PATH = os.environ.get(
    "EVENT_SYNC_LAST_BACKFILL_PATH", "/tmp/event_sync_last_backfill"
)


def _touch_heartbeat() -> None:
    try:
        with open(_HEARTBEAT_PATH, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
    except OSError as exc:
        logger.warning("Could not write event sync heartbeat: %s", exc)


def _should_run_backfill(interval_sec: int) -> bool:
    try:
        if not os.path.isfile(_LAST_BACKFILL_PATH):
            return True
        with open(_LAST_BACKFILL_PATH, encoding="utf-8") as fh:
            last = float(fh.read().strip() or "0")
        return (time.time() - last) >= interval_sec
    except (OSError, ValueError):
        return True


def _mark_backfill_done() -> None:
    try:
        with open(_LAST_BACKFILL_PATH, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
    except OSError as exc:
        logger.warning("Could not write backfill marker: %s", exc)


async def main() -> None:
    from app.core.database import create_db_and_tables
    from app.tasks.event_scraper_tasks import run_daily_event_sync

    await create_db_and_tables()
    interval = int(os.environ.get("EVENT_SYNC_INTERVAL_SEC", "86400"))
    backfill_interval = int(os.environ.get("EVENT_COORD_BACKFILL_INTERVAL_SEC", "604800"))
    logger.info(
        "Event sync worker started (sync=%ss, backfill=%ss)",
        interval,
        backfill_interval,
    )
    _touch_heartbeat()

    while True:
        try:
            result = await run_daily_event_sync()
            logger.info("Event sync cycle: success=%s sync=%s", result.get("success"), result.get("sync"))
            if _should_run_backfill(backfill_interval):
                from app.core.database import get_async_session
                from app.services.event_llm_date_enrichment import EventLlmDateEnrichmentService
                from app.services.events_feed_service import EventsFeedService
                from app.services.rls_service import RLSService

                async for db in get_async_session():
                    async with RLSService(db).worker_bypass():
                        feed = EventsFeedService(db)
                        coords = await feed.backfill_missing_coordinates(
                            limit=500,
                            dry_run=False,
                            refresh_stale=True,
                            geocode_venues=True,
                            geocode_venue_limit=25,
                        )
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
                                limit=int(os.getenv("EVENTS_DETAIL_ENRICH_LIMIT", "40")),
                                dry_run=False,
                            )
                        finally:
                            await llm_service.close()
                        logger.info("Weekly coordinate backfill: %s", coords)
                        logger.info("Weekly date backfill: %s", dates)
                        logger.info("Weekly LLM date enrichment: %s", llm_dates)
                _mark_backfill_done()
        except Exception:
            logger.exception("Event sync cycle error")
        _touch_heartbeat()
        await asyncio.sleep(max(300, interval))


if __name__ == "__main__":
    asyncio.run(main())
