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
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_HEARTBEAT_PATH = os.environ.get("CHANNEL_SYNC_HEARTBEAT_PATH", "/tmp/channel_sync_heartbeat")


def _touch_heartbeat() -> None:
    try:
        with open(_HEARTBEAT_PATH, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
    except OSError as exc:
        logger.warning("Could not write channel sync heartbeat: %s", exc)


async def main() -> None:
    from app.core.database import create_db_and_tables
    from app.tasks.channel_replay_tasks import replay_failed_events_batch
    from app.tasks.channel_sync_tasks import run_reservation_poll_cycle

    await create_db_and_tables()
    interval = int(os.environ.get("CHANNEL_SYNC_INTERVAL_SEC", "300"))
    logger.info("Channel sync worker started (interval=%ss)", interval)
    _touch_heartbeat()
    while True:
        try:
            poll = await run_reservation_poll_cycle()
            logger.info("Poll cycle: %s", poll)
            replay = await replay_failed_events_batch()
            if replay.get("attempted"):
                logger.info("Replay batch: %s", replay)
        except Exception:
            logger.exception("Channel sync cycle error")
        _touch_heartbeat()
        await asyncio.sleep(max(30, interval))


if __name__ == "__main__":
    asyncio.run(main())
