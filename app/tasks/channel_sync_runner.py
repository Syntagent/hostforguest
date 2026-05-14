"""
Long-running worker: poll reservations and replay failed events.

Run: python -m app.tasks.channel_sync_runner

Environment:
  CHANNEL_SYNC_INTERVAL_SEC (default 300)
  BOOKING_COM_MOCK, USE_POSTGRESQL, database vars — same as API
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    from app.core.database import create_db_and_tables
    from app.tasks.channel_replay_tasks import replay_failed_events_batch
    from app.tasks.channel_sync_tasks import run_reservation_poll_cycle

    await create_db_and_tables()
    interval = int(os.environ.get("CHANNEL_SYNC_INTERVAL_SEC", "300"))
    logger.info("Channel sync worker started (interval=%ss)", interval)
    while True:
        try:
            poll = await run_reservation_poll_cycle()
            logger.info("Poll cycle: %s", poll)
            replay = await replay_failed_events_batch()
            if replay.get("attempted"):
                logger.info("Replay batch: %s", replay)
        except Exception:
            logger.exception("Channel sync cycle error")
        await asyncio.sleep(max(30, interval))


if __name__ == "__main__":
    asyncio.run(main())
