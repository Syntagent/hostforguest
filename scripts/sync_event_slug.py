#!/usr/bin/env python3
"""Sync one national event source slug into local_events (dev/ops)."""

from __future__ import annotations

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from app.core.database import get_async_session
from app.services.event_ingestion_service import EventIngestionService


async def main() -> int:
    slug = (sys.argv[1] if len(sys.argv) > 1 else "tz-lovran").strip()
    async for db in get_async_session():
        result = await EventIngestionService(db).sync_source(slug)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("success") else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
