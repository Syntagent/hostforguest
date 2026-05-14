"""
Scheduled / worker task: poll Booking.com reservations for all connected accounts.
"""

from __future__ import annotations

import logging

from app.db.postgresql.connection import AsyncSessionLocal
from app.services.channel_integration_service import ChannelIntegrationService
from app.services.channel_sync_service import ChannelSyncService

logger = logging.getLogger(__name__)


async def run_reservation_poll_cycle() -> dict:
    """Poll every connected channel account once."""
    summary = {"accounts": 0, "results": []}
    async with AsyncSessionLocal() as db:
        integ = ChannelIntegrationService(db)
        sync = ChannelSyncService(db)
        accounts = await integ.list_connected_accounts()
        summary["accounts"] = len(accounts)
        for acc in accounts:
            try:
                res = await sync.poll_reservations(acc.id)
                summary["results"].append({"account_id": str(acc.id), **res})
            except Exception as e:
                logger.exception("Poll failed for %s: %s", acc.id, e)
                summary["results"].append({"account_id": str(acc.id), "ok": False, "error": str(e)})
    return summary
