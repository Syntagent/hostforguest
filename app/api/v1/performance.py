"""
Performance optimization API endpoints.

Provides REST API for performance monitoring,
cache management, and query optimization.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_maintenance_job_secret_only
from app.models.performance_api import (
    PerformanceCacheClearResponse,
    PerformanceQueryAnalysisResponse,
    PerformanceRefreshViewsResponse,
)
from app.services.cache_service import get_cache_service
from app.services.query_optimization_service import QueryOptimizationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refresh-views", response_model=PerformanceRefreshViewsResponse)
async def refresh_materialized_views(
    _auth: None = Depends(require_maintenance_job_secret_only),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh materialized views for performance.
    
    Args:
        db: Database session
        
    Returns:
        Success status
    """
    try:
        optimization_service = QueryOptimizationService(db)
        success = await optimization_service.refresh_materialized_views()
        
        if success:
            return PerformanceRefreshViewsResponse(
                success=True,
                message="Materialized views refreshed",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh materialized views"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing views: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh views: {str(e)}"
        )


@router.get("/query-analysis", response_model=PerformanceQueryAnalysisResponse)
async def analyze_query_performance(
    _auth: None = Depends(require_maintenance_job_secret_only),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze query performance and suggest optimizations.
    
    Args:
        db: Database session
        
    Returns:
        Performance analysis data
    """
    try:
        optimization_service = QueryOptimizationService(db)
        analysis = await optimization_service.analyze_query_performance()
        slow = analysis.get("slow_queries") or []
        return PerformanceQueryAnalysisResponse(
            slow_queries=slow,
            suggestions=list(analysis.get("suggestions") or []),
            pg_stat_statements_available=bool(analysis.get("pg_stat_statements_available")),
            raw={
                k: v
                for k, v in analysis.items()
                if k not in {"slow_queries", "suggestions", "pg_stat_statements_available"}
            },
        )
        
    except Exception as e:
        logger.error(f"Error analyzing queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze queries: {str(e)}"
        )


@router.delete("/cache/{pattern}", response_model=PerformanceCacheClearResponse)
async def clear_cache_pattern(
    pattern: str,
    _auth: None = Depends(require_maintenance_job_secret_only),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear cache entries matching a pattern.
    
    Args:
        pattern: Cache key pattern (e.g., "host:*")
        db: Database session
        
    Returns:
        Number of keys deleted
    """
    try:
        cache_service = get_cache_service()
        deleted = await cache_service.delete_pattern(pattern)
        
        return PerformanceCacheClearResponse(
            success=True,
            pattern=pattern,
            deleted_count=deleted,
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

