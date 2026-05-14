"""
Analytics API endpoints for business intelligence.

Provides REST API for comprehensive analytics including
guest satisfaction, recommendation effectiveness, partner performance, and revenue tracking.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_host_session
from app.services.analytics_service import AnalyticsService
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/satisfaction-trends")
async def get_satisfaction_trends(
    current_host: Host = Depends(require_host_session),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get guest satisfaction trends over time.
    
    Args:
        host_id: Optional host ID to filter by
        days: Number of days to analyze (1-365)
        db: Database session
        
    Returns:
        Satisfaction trends data
    """
    try:
        service = AnalyticsService(db)
        trends = await service.get_guest_satisfaction_trends(
            host_id=str(current_host.id),
            days=days
        )
        return trends
        
    except Exception as e:
        logger.error(f"Error getting satisfaction trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get satisfaction trends: {str(e)}"
        )


@router.get("/recommendation-effectiveness")
async def get_recommendation_effectiveness(
    current_host: Host = Depends(require_host_session),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendation effectiveness metrics.
    
    Args:
        host_id: Optional host ID to filter by
        days: Number of days to analyze
        db: Database session
        
    Returns:
        Recommendation effectiveness data
    """
    try:
        service = AnalyticsService(db)
        effectiveness = await service.get_recommendation_effectiveness(
            host_id=str(current_host.id),
            days=days
        )
        return effectiveness
        
    except Exception as e:
        logger.error(f"Error getting recommendation effectiveness: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation effectiveness: {str(e)}"
        )


@router.get("/partner-performance")
async def get_partner_performance(
    current_host: Host = Depends(require_host_session),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get partner performance analytics.
    
    Args:
        host_id: Optional host ID to filter by
        days: Number of days to analyze
        db: Database session
        
    Returns:
        Partner performance data
    """
    try:
        service = AnalyticsService(db)
        performance = await service.get_partner_performance(
            host_id=str(current_host.id),
            days=days
        )
        return performance
        
    except Exception as e:
        logger.error(f"Error getting partner performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get partner performance: {str(e)}"
        )


@router.get("/revenue-tracking")
async def get_revenue_tracking(
    current_host: Host = Depends(require_host_session),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue tracking metrics.
    
    Args:
        host_id: Optional host ID to filter by
        days: Number of days to analyze
        db: Database session
        
    Returns:
        Revenue tracking data
    """
    try:
        service = AnalyticsService(db)
        revenue = await service.get_revenue_tracking(
            host_id=str(current_host.id),
            days=days
        )
        return revenue
        
    except Exception as e:
        logger.error(f"Error getting revenue tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revenue tracking: {str(e)}"
        )


@router.get("/export")
async def export_analytics_report(
    current_host: Host = Depends(require_host_session),
    report_type: str = Query("comprehensive", pattern="^(comprehensive|revenue|satisfaction|partners|recommendations)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Export comprehensive analytics report.
    
    Args:
        current_host: Current authenticated host
        report_type: Type of report (comprehensive, revenue, satisfaction, partners, recommendations)
        format: Export format (json, csv)
        db: Database session
        
    Returns:
        Report data in requested format
    """
    try:
        service = AnalyticsService(db)
        report = await service.export_analytics_report(
            host_id=str(current_host.id),
            report_type=report_type,
            format=format
        )
        return report
        
    except Exception as e:
        logger.error(f"Error exporting analytics report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {str(e)}"
        )

