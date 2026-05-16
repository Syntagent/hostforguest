"""
Multi-database manager for TouristGuideLocal.

Handles PostgreSQL (with pgvector) for the Croatian tourist platform.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgresql.connection import (
    init_postgresql,
    close_postgresql,
    get_async_session,
    postgresql_manager,
)

logger = logging.getLogger(__name__)


async def create_db_and_tables() -> None:
    """
    Initialize all databases and create tables/schema.

    Sets up PostgreSQL with pgvector (or SQLite fallback).
    """
    import os

    if (os.environ.get("TOURISTGUIDE_PYTEST") or "").strip().lower() in ("1", "true", "yes"):
        logger.info(
            "Skipping external DB bootstrap (TOURISTGUIDE_PYTEST=1); "
            "tests use in-memory SQLite via FastAPI dependency overrides."
        )
        return

    try:
        await init_postgresql()
        logger.info("PostgreSQL initialized successfully")

        # Development: default host for /login "Dev Login" button
        try:
            from app.core.dev_seed import (
                seed_dev_login_user_if_needed,
                seed_dev_host_profile_shell_if_needed,
                seed_dev_cleaning_partners_if_needed,
                seed_dev_trades_partners_if_needed,
            )

            await seed_dev_login_user_if_needed()
            await seed_dev_host_profile_shell_if_needed()
            await seed_dev_cleaning_partners_if_needed()
            await seed_dev_trades_partners_if_needed()
        except Exception as e:
            logger.warning("Dev login user seed skipped: %s", e)

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_databases() -> None:
    """
    Close all database connections.
    """
    import os

    if (os.environ.get("TOURISTGUIDE_PYTEST") or "").strip().lower() in ("1", "true", "yes"):
        return

    try:
        await close_postgresql()
        logger.info("All database connections closed")
    except Exception as e:
        logger.error(f"Error closing databases: {e}")


# Dependency for FastAPI to get PostgreSQL session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get PostgreSQL database session.

    Yields:
        AsyncSession: PostgreSQL database session
    """
    async for session in get_async_session():
        yield session


async def health_check_databases() -> dict:
    """
    Check health of all databases.

    Returns:
        dict: Health status of all databases
    """
    health_status = {
        "postgresql": False,
        "overall": False,
    }

    try:
        health_status["postgresql"] = await postgresql_manager.health_check()
        health_status["overall"] = health_status["postgresql"]
        logger.info(f"Database health check: {health_status}")

    except Exception as e:
        logger.error(f"Health check failed: {e}")

    return health_status
