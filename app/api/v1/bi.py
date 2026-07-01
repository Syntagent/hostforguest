"""
Business Intelligence API endpoints.

Provides REST API for advanced analytics including
revenue tracking, LTV analysis, ROI metrics, and seasonal trends.
"""

import logging
import csv
import io
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import Response

from app.models.bi_api import (
    BiDashboardResponse,
    BiExportJsonResponse,
    BiGuestLtvResponse,
    BiRecommendationRoiResponse,
    BiRevenueTrackingResponse,
    BiSeasonalTrendsResponse,
)
from app.core.database import get_db
from app.services.bi_service import BIService
from app.api.v1.hosts import get_current_host
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


def _dashboard_to_csv(dashboard_data: dict) -> str:
    """Flatten BI dashboard dict into a simple CSV for host export."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "value"])

    for section, payload in dashboard_data.items():
        if not isinstance(payload, dict):
            writer.writerow([section, "value", payload])
            continue
        for key, value in payload.items():
            if key == "revenue_by_period" and isinstance(value, dict):
                writer.writerow(["revenue_by_period", "period", "revenue", "commission", "bookings"])
                for period, metrics in sorted(value.items()):
                    if isinstance(metrics, dict):
                        writer.writerow([
                            "revenue_by_period",
                            period,
                            metrics.get("revenue", 0),
                            metrics.get("commission", 0),
                            metrics.get("bookings", 0),
                        ])
            elif not isinstance(value, (dict, list)):
                writer.writerow([section, key, value])

    return buf.getvalue()


@router.get("/revenue", response_model=BiRevenueTrackingResponse)
async def get_revenue_tracking(
    period_days: int = Query(90, ge=1, le=365),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue tracking and trends.
    
    Args:
        period_days: Number of days to analyze
        group_by: Grouping period (day, week, month)
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Revenue tracking data
    """
    try:
        bi_service = BIService(db)
        revenue_data = await bi_service.get_revenue_tracking(
            host_id=current_host.id,
            period_days=period_days,
            group_by=group_by
        )
        
        return BiRevenueTrackingResponse.model_validate(revenue_data)

    except Exception as e:
        logger.error(f"Error getting revenue tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revenue tracking: {str(e)}"
        )


@router.get("/ltv", response_model=BiGuestLtvResponse)
async def get_guest_ltv(
    period_days: int = Query(365, ge=1, le=1095),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate guest lifetime value (LTV).
    
    Args:
        period_days: Period to analyze
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        LTV analysis data
    """
    try:
        bi_service = BIService(db)
        ltv_data = await bi_service.get_guest_ltv(
            host_id=current_host.id,
            period_days=period_days
        )
        
        return BiGuestLtvResponse.model_validate(ltv_data)

    except Exception as e:
        logger.error(f"Error calculating LTV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate LTV: {str(e)}"
        )


@router.get("/roi", response_model=BiRecommendationRoiResponse)
async def get_recommendation_roi(
    period_days: int = Query(90, ge=1, le=365),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate recommendation ROI metrics.
    
    Args:
        period_days: Period to analyze
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ROI analysis data
    """
    try:
        bi_service = BIService(db)
        roi_data = await bi_service.get_recommendation_roi(
            host_id=current_host.id,
            period_days=period_days
        )
        
        return BiRecommendationRoiResponse.model_validate(roi_data)

    except Exception as e:
        logger.error(f"Error calculating ROI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate ROI: {str(e)}"
        )


@router.get("/seasonal-trends", response_model=BiSeasonalTrendsResponse)
async def get_seasonal_trends(
    years: int = Query(2, ge=1, le=5),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze seasonal trends.
    
    Args:
        years: Number of years to analyze
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Seasonal trends data
    """
    try:
        bi_service = BIService(db)
        trends_data = await bi_service.get_seasonal_trends(
            host_id=current_host.id,
            years=years
        )
        
        return BiSeasonalTrendsResponse.model_validate(trends_data)

    except Exception as e:
        logger.error(f"Error analyzing seasonal trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze trends: {str(e)}"
        )


@router.get("/dashboard", response_model=BiDashboardResponse)
async def get_bi_dashboard(
    period_days: int = Query(90, ge=1, le=365),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive BI dashboard data.
    
    Args:
        period_days: Period to analyze
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Complete BI dashboard data
    """
    try:
        bi_service = BIService(db)
        
        # Get all metrics
        revenue = await bi_service.get_revenue_tracking(current_host.id, period_days)
        ltv = await bi_service.get_guest_ltv(current_host.id, period_days)
        roi = await bi_service.get_recommendation_roi(current_host.id, period_days)
        trends = await bi_service.get_seasonal_trends(current_host.id, 2)
        
        return BiDashboardResponse.model_validate(
            {
                "host_id": str(current_host.id),
                "period_days": period_days,
                "revenue": revenue,
                "ltv": ltv,
                "roi": roi,
                "seasonal_trends": trends,
                "summary": {
                    "total_revenue": revenue.get("total_revenue", 0),
                    "average_ltv": ltv.get("average_ltv", 0),
                    "roi_percentage": roi.get("roi_percentage", 0),
                    "peak_season": trends.get("peak_season"),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting BI dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.get("/export")
async def export_bi_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    period_days: int = Query(90, ge=1, le=365),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Export BI data in various formats.
    
    Args:
        format: Export format (json, csv)
        period_days: Period to analyze
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Exported data
    """
    try:
        bi_service = BIService(db)
        
        # Get dashboard data
        dashboard_data = {
            "revenue": await bi_service.get_revenue_tracking(current_host.id, period_days),
            "ltv": await bi_service.get_guest_ltv(current_host.id, period_days),
            "roi": await bi_service.get_recommendation_roi(current_host.id, period_days),
            "trends": await bi_service.get_seasonal_trends(current_host.id, 2)
        }
        
        if format == "csv":
            csv_body = _dashboard_to_csv(dashboard_data)
            return Response(
                content=csv_body,
                media_type="text/csv",
                headers={
                    "Content-Disposition": 'attachment; filename="bi-export.csv"'
                },
            )
        return BiExportJsonResponse.model_validate(dashboard_data)

    except Exception as e:
        logger.error(f"Error exporting BI data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export data: {str(e)}"
        )

