"""
Background tasks for cache refresh and maintenance.

Handles periodic cache invalidation and materialized view refreshes.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_service import get_cache_service
from app.services.query_optimization_service import QueryOptimizationService

logger = logging.getLogger(__name__)


async def refresh_materialized_views_task(db: AsyncSession) -> Dict[str, Any]:
    """
    Refresh materialized views for performance.
    
    Args:
        db: Database session
        
    Returns:
        Task execution results
    """
    try:
        optimization_service = QueryOptimizationService(db)
        success = await optimization_service.refresh_materialized_views()
        
        return {
            "task": "refresh_materialized_views",
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        return {
            "task": "refresh_materialized_views",
            "success": False,
            "error": str(e)
        }


async def clear_expired_cache_task() -> Dict[str, Any]:
    """
    Clear expired cache entries.
    
    Returns:
        Task execution results
    """
    try:
        cache_service = get_cache_service()
        
        # Clear expired entries (handled automatically by Redis)
        # For in-memory cache, cleanup is done on access
        
        return {
            "task": "clear_expired_cache",
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}")
        return {
            "task": "clear_expired_cache",
            "success": False,
            "error": str(e)
        }

