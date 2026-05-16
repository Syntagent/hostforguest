"""
Scheduled maintenance tasks (preventive issues from maintenance_schedules).

Call from cron or the secured HTTP job endpoint.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.db.postgresql.connection import get_async_session
from app.services.maintenance_service import MaintenanceService

logger = logging.getLogger(__name__)


async def run_preventive_maintenance_for_all_hosts() -> Dict[str, Any]:
    """
    Open due preventive maintenance issues for every host with a past-due schedule.

    Returns:
        Summary dict with ``created_count`` and ``issue_ids``.
    """
    async for db in get_async_session():
        svc = MaintenanceService(db)
        created = await svc.run_all_due_schedules_for_all_hosts()
        logger.info("preventive maintenance job: created %s issue(s)", len(created))
        return {
            "created_count": len(created),
            "issue_ids": [str(i.id) for i in created],
        }
    return {"created_count": 0, "issue_ids": []}
