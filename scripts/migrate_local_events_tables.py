#!/usr/bin/env python3
"""Idempotent migration for local_events and event_source_proposals tables."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> None:
    from app.core.database import create_db_and_tables
    from app.db.postgresql.connection import Base, engine, import_models

    import_models()
    import app.models.local_event  # noqa: F401
    import app.models.event_source_proposal  # noqa: F401

    await create_db_and_tables()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("local_events and event_source_proposals tables ready.")


if __name__ == "__main__":
    asyncio.run(main())
