#!/usr/bin/env python3
"""
Run preventive maintenance for all hosts (open issues from due schedules).

Usage (from repo root, with .env loaded via app settings):

    python scripts/run_maintenance_preventive.py

Cron example (daily 06:00):

    0 6 * * * cd /path/to/TouristGuideLocal && python scripts/run_maintenance_preventive.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

# Repo root on path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    from app.core.database import create_db_and_tables
    from app.tasks.maintenance_tasks import run_preventive_maintenance_for_all_hosts

    await create_db_and_tables()
    result = await run_preventive_maintenance_for_all_hosts()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
