"""
Multi-database manager for TouristGuideLocal.

Handles PostgreSQL (with pgvector) and Neo4j database connections for the Croatian tourist platform.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgresql.connection import (
    init_postgresql, 
    close_postgresql, 
    get_async_session,
    postgresql_manager
)
from app.db.neo4j.connection import (
    init_neo4j, 
    close_neo4j,
    neo4j_manager
)

logger = logging.getLogger(__name__)


async def create_db_and_tables() -> None:
    """
    Initialize all databases and create tables/schema.
    
    Sets up PostgreSQL with pgvector and Neo4j with graph schema.
    """
    try:
        # Initialize PostgreSQL with pgvector
        await init_postgresql()
        logger.info("PostgreSQL initialized successfully")
        
        # Initialize Neo4j (only if available)
        try:
            await init_neo4j()
            logger.info("Neo4j initialized successfully")
        except Exception as e:
            logger.warning(f"Neo4j initialization failed (optional): {e}")

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
    try:
        await close_postgresql()
        await close_neo4j()
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
        "neo4j": False,
        "overall": False
    }
    
    try:
        # Check PostgreSQL
        health_status["postgresql"] = await postgresql_manager.health_check()
        
        # Check Neo4j
        try:
            health_status["neo4j"] = await neo4j_manager.health_check()
        except Exception:
            health_status["neo4j"] = False
        
        # Overall health (PostgreSQL is required, Neo4j is optional)
        health_status["overall"] = health_status["postgresql"]
        
        logger.info(f"Database health check: {health_status}")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return health_status 