"""
Connection pooling configuration for PostgreSQL.

Optimizes database connection management for better performance.
"""

import logging
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def create_optimized_engine(
    database_url: str,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600
):
    """
    Create optimized async engine with connection pooling.
    
    Args:
        database_url: Database connection URL
        pool_size: Number of connections to maintain
        max_overflow: Maximum overflow connections
        pool_pre_ping: Enable connection health checks
        pool_recycle: Recycle connections after this many seconds
        
    Returns:
        Async engine instance
    """
    return create_async_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        echo=False,
        future=True
    )

