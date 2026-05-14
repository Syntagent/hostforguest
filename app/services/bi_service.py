"""
Business Intelligence service for advanced analytics and reporting.

Provides comprehensive BI features including:
- Revenue tracking and forecasting
- Guest lifetime value (LTV) analysis
- Recommendation ROI metrics
- Seasonal trends analysis
- Predictive analytics
- Export capabilities
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, extract, case
from sqlalchemy.sql import label

from app.models.host import Host
from app.models.guest_group import GuestGroup
from app.models.recommendation import RecommendationSet
from app.models.partner import PartnerBooking
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class BIService:
    """
    Business Intelligence service for advanced analytics.
    
    Provides revenue tracking, LTV analysis, ROI metrics,
    seasonal trends, and predictive analytics.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the BI service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.analytics_service = AnalyticsService(db)
    
    async def get_revenue_tracking(
        self,
        host_id: uuid.UUID,
        period_days: int = 90,
        group_by: str = "day"  # day, week, month
    ) -> Dict[str, Any]:
        """
        Get revenue tracking and trends.
        
        Args:
            host_id: Host ID
            period_days: Number of days to analyze
            group_by: Grouping period (day, week, month)
            
        Returns:
            Revenue tracking data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get bookings revenue
            stmt_bookings = select(
                func.sum(PartnerBooking.booking_amount).label("total_revenue"),
                func.sum(PartnerBooking.commission_amount).label("total_commission"),
                func.count(PartnerBooking.id).label("total_bookings"),
                self._get_group_by_date(PartnerBooking.booking_date, group_by).label("period")
            ).where(
                and_(
                    PartnerBooking.host_id == host_id,
                    PartnerBooking.status == "confirmed",
                    PartnerBooking.booking_date >= start_date
                )
            ).group_by("period")
            
            result_bookings = await self.db.execute(stmt_bookings)
            booking_data = result_bookings.all()
            
            # Calculate revenue trends
            revenue_by_period = {}
            for row in booking_data:
                period_key = row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period)
                revenue_by_period[period_key] = {
                    "revenue": float(row.total_revenue or 0),
                    "commission": float(row.total_commission or 0),
                    "bookings": row.total_bookings or 0
                }
            
            # Calculate totals
            total_revenue = sum(r["revenue"] for r in revenue_by_period.values())
            total_commission = sum(r["commission"] for r in revenue_by_period.values())
            total_bookings = sum(r["bookings"] for r in revenue_by_period.values())
            
            # Calculate growth rate
            periods = sorted(revenue_by_period.keys())
            growth_rate = 0.0
            if len(periods) >= 2:
                recent_revenue = revenue_by_period[periods[-1]]["revenue"]
                previous_revenue = revenue_by_period[periods[-2]]["revenue"]
                if previous_revenue > 0:
                    growth_rate = ((recent_revenue - previous_revenue) / previous_revenue) * 100
            
            return {
                "host_id": str(host_id),
                "period_days": period_days,
                "group_by": group_by,
                "total_revenue": total_revenue,
                "total_commission": total_commission,
                "total_bookings": total_bookings,
                "average_booking_value": total_revenue / total_bookings if total_bookings > 0 else 0,
                "growth_rate": round(growth_rate, 2),
                "revenue_by_period": revenue_by_period,
                "forecast": self._forecast_revenue(revenue_by_period, group_by)
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue tracking: {e}")
            return {
                "host_id": str(host_id),
                "error": str(e)
            }
    
    async def get_guest_ltv(
        self,
        host_id: uuid.UUID,
        period_days: int = 365
    ) -> Dict[str, Any]:
        """
        Calculate guest lifetime value (LTV).
        
        Args:
            host_id: Host ID
            period_days: Period to analyze
            
        Returns:
            LTV analysis data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get guest groups with bookings
            stmt = select(
                GuestGroup.id,
                GuestGroup.group_name,
                func.sum(PartnerBooking.booking_amount).label("total_spent"),
                func.count(PartnerBooking.id).label("booking_count"),
                func.max(PartnerBooking.booking_date).label("last_booking")
            ).join(
                PartnerBooking, PartnerBooking.guest_group_id == GuestGroup.id
            ).where(
                and_(
                    GuestGroup.host_id == host_id,
                    PartnerBooking.booking_date >= start_date,
                    PartnerBooking.status == "confirmed"
                )
            ).group_by(GuestGroup.id, GuestGroup.group_name)
            
            result = await self.db.execute(stmt)
            guest_data = result.all()
            
            if not guest_data:
                return {
                    "host_id": str(host_id),
                    "average_ltv": 0,
                    "total_guests": 0,
                    "total_revenue": 0
                }
            
            # Calculate LTV metrics
            ltv_values = [float(row.total_spent or 0) for row in guest_data]
            total_revenue = sum(ltv_values)
            average_ltv = total_revenue / len(ltv_values) if ltv_values else 0
            
            # Segment by LTV
            high_value = sum(1 for ltv in ltv_values if ltv >= average_ltv * 1.5)
            medium_value = sum(1 for ltv in ltv_values if average_ltv * 0.5 <= ltv < average_ltv * 1.5)
            low_value = sum(1 for ltv in ltv_values if ltv < average_ltv * 0.5)
            
            return {
                "host_id": str(host_id),
                "period_days": period_days,
                "total_guests": len(guest_data),
                "total_revenue": total_revenue,
                "average_ltv": round(average_ltv, 2),
                "median_ltv": round(sorted(ltv_values)[len(ltv_values) // 2] if ltv_values else 0, 2),
                "max_ltv": round(max(ltv_values) if ltv_values else 0, 2),
                "min_ltv": round(min(ltv_values) if ltv_values else 0, 2),
                "segmentation": {
                    "high_value": high_value,
                    "medium_value": medium_value,
                    "low_value": low_value
                },
                "ltv_distribution": self._calculate_ltv_distribution(ltv_values)
            }
            
        except Exception as e:
            logger.error(f"Error calculating guest LTV: {e}")
            return {
                "host_id": str(host_id),
                "error": str(e)
            }
    
    async def get_recommendation_roi(
        self,
        host_id: uuid.UUID,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """
        Calculate recommendation ROI metrics.
        
        Args:
            host_id: Host ID
            period_days: Period to analyze
            
        Returns:
            ROI analysis data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get recommendation sets
            stmt_recs = select(
                RecommendationSet.id,
                RecommendationSet.total_recommendations,
                RecommendationSet.recommendations_accepted,
                RecommendationSet.overall_satisfaction
            ).where(
                and_(
                    RecommendationSet.host_id == host_id,
                    RecommendationSet.delivered_at >= start_date
                )
            )
            
            result_recs = await self.db.execute(stmt_recs)
            rec_sets = result_recs.all()
            
            # Get bookings from recommendations
            # (In production, would link recommendations to bookings)
            total_recommendations = sum(rs.total_recommendations or 0 for rs in rec_sets)
            total_accepted = sum(rs.recommendations_accepted or 0 for rs in rec_sets)
            avg_satisfaction = sum(rs.overall_satisfaction or 0 for rs in rec_sets) / len(rec_sets) if rec_sets else 0
            
            # Calculate conversion metrics
            acceptance_rate = (total_accepted / total_recommendations * 100) if total_recommendations > 0 else 0
            
            # Estimate revenue from recommendations (simplified)
            # In production, would track actual bookings from recommendations
            estimated_revenue = total_accepted * 50  # Placeholder: 50 EUR per accepted recommendation
            
            return {
                "host_id": str(host_id),
                "period_days": period_days,
                "total_recommendations": total_recommendations,
                "total_accepted": total_accepted,
                "acceptance_rate": round(acceptance_rate, 2),
                "average_satisfaction": round(avg_satisfaction, 2),
                "estimated_revenue": estimated_revenue,
                "roi_percentage": round((estimated_revenue / (total_recommendations * 0.1)) * 100, 2) if total_recommendations > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating recommendation ROI: {e}")
            return {
                "host_id": str(host_id),
                "error": str(e)
            }
    
    async def get_seasonal_trends(
        self,
        host_id: uuid.UUID,
        years: int = 2
    ) -> Dict[str, Any]:
        """
        Analyze seasonal trends.
        
        Args:
            host_id: Host ID
            years: Number of years to analyze
            
        Returns:
            Seasonal trends data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=years * 365)
            
            # Get bookings by month
            stmt = select(
                extract('month', PartnerBooking.booking_date).label("month"),
                extract('year', PartnerBooking.booking_date).label("year"),
                func.sum(PartnerBooking.booking_amount).label("revenue"),
                func.count(PartnerBooking.id).label("bookings")
            ).where(
                and_(
                    PartnerBooking.host_id == host_id,
                    PartnerBooking.status == "confirmed",
                    PartnerBooking.booking_date >= start_date
                )
            ).group_by("month", "year")
            
            result = await self.db.execute(stmt)
            monthly_data = result.all()
            
            # Organize by season
            seasons = {
                "spring": [3, 4, 5],
                "summer": [6, 7, 8],
                "autumn": [9, 10, 11],
                "winter": [12, 1, 2]
            }
            
            seasonal_revenue = {season: 0 for season in seasons.keys()}
            seasonal_bookings = {season: 0 for season in seasons.keys()}
            
            for row in monthly_data:
                month = int(row.month)
                revenue = float(row.revenue or 0)
                bookings = row.bookings or 0
                
                for season, months in seasons.items():
                    if month in months:
                        seasonal_revenue[season] += revenue
                        seasonal_bookings[season] += bookings
                        break
            
            # Find peak season
            peak_season = max(seasonal_revenue.items(), key=lambda x: x[1])[0] if seasonal_revenue else None
            
            return {
                "host_id": str(host_id),
                "years": years,
                "seasonal_revenue": seasonal_revenue,
                "seasonal_bookings": seasonal_bookings,
                "peak_season": peak_season,
                "monthly_breakdown": [
                    {
                        "month": int(row.month),
                        "year": int(row.year),
                        "revenue": float(row.revenue or 0),
                        "bookings": row.bookings or 0
                    }
                    for row in monthly_data
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing seasonal trends: {e}")
            return {
                "host_id": str(host_id),
                "error": str(e)
            }
    
    def _get_group_by_date(self, date_column, group_by: str):
        """Get SQL expression for grouping by date."""
        if group_by == "day":
            return func.date(date_column)
        elif group_by == "week":
            return func.date_trunc('week', date_column)
        elif group_by == "month":
            return func.date_trunc('month', date_column)
        else:
            return func.date(date_column)
    
    def _forecast_revenue(
        self,
        revenue_by_period: Dict[str, Dict[str, Any]],
        group_by: str
    ) -> Dict[str, Any]:
        """
        Simple revenue forecasting.
        
        Args:
            revenue_by_period: Historical revenue data
            group_by: Grouping period
            
        Returns:
            Forecast data
        """
        if not revenue_by_period:
            return {"next_period": 0, "trend": "stable"}
        
        periods = sorted(revenue_by_period.keys())
        if len(periods) < 2:
            return {"next_period": 0, "trend": "stable"}
        
        # Simple linear trend
        recent_revenues = [revenue_by_period[p]["revenue"] for p in periods[-3:]]
        if len(recent_revenues) >= 2:
            trend = recent_revenues[-1] - recent_revenues[-2]
            forecast = recent_revenues[-1] + trend
        else:
            forecast = recent_revenues[-1] if recent_revenues else 0
            trend = 0
        
        return {
            "next_period": round(max(0, forecast), 2),
            "trend": "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
            "confidence": "medium"
        }
    
    def _calculate_ltv_distribution(self, ltv_values: List[float]) -> Dict[str, int]:
        """Calculate LTV distribution buckets."""
        if not ltv_values:
            return {}
        
        max_ltv = max(ltv_values)
        buckets = {
            "0-50": 0,
            "50-100": 0,
            "100-200": 0,
            "200-500": 0,
            "500+": 0
        }
        
        for ltv in ltv_values:
            if ltv < 50:
                buckets["0-50"] += 1
            elif ltv < 100:
                buckets["50-100"] += 1
            elif ltv < 200:
                buckets["100-200"] += 1
            elif ltv < 500:
                buckets["200-500"] += 1
            else:
                buckets["500+"] += 1
        
        return buckets

