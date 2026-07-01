"""
Replay failed channel event logs (dead-letter recovery).
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.postgresql.connection import AsyncSessionLocal
from app.models.channel_integration import ChannelAccount, ChannelEventLog, ChannelEventStatus
from app.services.channel_sync_service import ChannelSyncService
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)


async def replay_failed_events_batch(limit: int = 50) -> dict:
    """Re-process FAILED inbound reservation events."""
    out = {"attempted": 0, "results": []}
    async with AsyncSessionLocal() as db:
        async with RLSService(db).worker_bypass():
            stmt = (
                select(ChannelEventLog)
                .where(ChannelEventLog.status == ChannelEventStatus.FAILED.value)
                .where(ChannelEventLog.event_type == "reservation_upsert")
                .limit(limit)
            )
            r = await db.execute(stmt)
            logs = list(r.scalars().all())
            sync = ChannelSyncService(db)
            for log in logs:
                acc = await db.get(ChannelAccount, log.channel_account_id)
                if not acc:
                    continue
                out["attempted"] += 1
                try:
                    res = await sync.replay_event_log(log.id, acc.host_id)
                    out["results"].append({"event_id": str(log.id), **res})
                except Exception as e:
                    logger.exception("Replay failed for %s", log.id)
                    out["results"].append({"event_id": str(log.id), "ok": False, "error": str(e)})
    return out
