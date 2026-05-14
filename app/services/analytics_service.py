"""
Enhanced analytics service for business intelligence.

Provides comprehensive analytics including:
- Guest satisfaction trends
- Recommendation effectiveness metrics
- Partner performance analytics
- Revenue tracking
- Export capabilities
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.guest_group import GuestGroup
from app.models.recommendation import RecommendationSet, Recommendation
from app.models.attraction import Attraction
from app.models.partner import Partner, HostPartner

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for comprehensive analytics and business intelligence.
    
    Provides insights into guest satisfaction, recommendation effectiveness,
    partner performance, and revenue metrics.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the analytics service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_guest_satisfaction_trends(
        self,
        host_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get guest satisfaction trends over time.
        
        Args:
            host_id: Optional host ID to filter by
            days: Number of days to analyze
            
        Returns:
            Satisfaction trends data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(
                func.date(GuestGroup.created_at).label('date'),
                func.avg(GuestGroup.satisfaction_rating).label('avg_rating'),
                func.count(GuestGroup.id).label('guest_count')
            ).where(
                and_(
                    GuestGroup.created_at >= cutoff_date,
                    GuestGroup.satisfaction_rating.isnot(None)
                )
            )
            
            if host_id:
                stmt = stmt.where(GuestGroup.host_id == host_id)
            
            stmt = stmt.group_by(func.date(GuestGroup.created_at))
            stmt = stmt.order_by(desc('date'))
            
            result = await self.db.execute(stmt)
            rows = result.all()
            
            trends = {
                "daily_ratings": [
                    {
                        "date": str(row.date),
                        "average_rating": float(row.avg_rating) if row.avg_rating else 0.0,
                        "guest_count": row.guest_count
                    }
                    for row in rows
                ],
                "overall_average": 0.0,
                "total_guests": 0
            }
            
            if trends["daily_ratings"]:
                total_rating = sum(r["average_rating"] * r["guest_count"] for r in trends["daily_ratings"])
                total_guests = sum(r["guest_count"] for r in trends["daily_ratings"])
                trends["overall_average"] = total_rating / total_guests if total_guests > 0 else 0.0
                trends["total_guests"] = total_guests
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting satisfaction trends: {e}")
            return {"daily_ratings": [], "overall_average": 0.0, "total_guests": 0}
    
    async def get_recommendation_effectiveness(
        self,
        host_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get recommendation effectiveness metrics.
        
        Args:
            host_id: Optional host ID to filter by
            days: Number of days to analyze
            
        Returns:
            Recommendation effectiveness data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(
                RecommendationSet
            ).where(
                RecommendationSet.created_at >= cutoff_date
            )
            
            if host_id:
                stmt = stmt.where(RecommendationSet.host_id == host_id)
            
            result = await self.db.execute(stmt)
            sets = result.scalars().all()
            
            total_sets = len(sets)
            total_recommendations = sum(s.total_recommendations for s in sets)
            total_accepted = sum(s.recommendations_accepted for s in sets)
            
            acceptance_rate = (total_accepted / total_recommendations * 100) if total_recommendations > 0 else 0.0
            
            # Calculate average satisfaction for recommendations
            satisfaction_sum = sum(s.satisfaction_rating for s in sets if s.satisfaction_rating)
            satisfaction_count = sum(1 for s in sets if s.satisfaction_rating)
            avg_satisfaction = satisfaction_sum / satisfaction_count if satisfaction_count > 0 else 0.0
            
            return {
                "total_recommendation_sets": total_sets,
                "total_recommendations": total_recommendations,
                "total_accepted": total_accepted,
                "acceptance_rate": acceptance_rate,
                "average_satisfaction": avg_satisfaction,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation effectiveness: {e}")
            return {
                "total_recommendation_sets": 0,
                "total_recommendations": 0,
                "total_accepted": 0,
                "acceptance_rate": 0.0,
                "average_satisfaction": 0.0,
                "period_days": days
            }
    
    async def get_partner_performance(
        self,
        host_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get partner performance analytics.
        
        Args:
            host_id: Optional host ID to filter by
            days: Number of days to analyze
            
        Returns:
            List of partner performance data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(
                HostPartner,
                Partner
            ).join(
                Partner, HostPartner.partner_id == Partner.id
            ).where(
                HostPartner.created_at >= cutoff_date
            )
            
            if host_id:
                stmt = stmt.where(HostPartner.host_id == host_id)
            
            result = await self.db.execute(stmt)
            rows = result.all()
            
            performance = []
            for host_partner, partner in rows:
                performance.append({
                    "partner_id": str(partner.id),
                    "partner_name": partner.name,
                    "partner_type": partner.partner_type,
                    "bookings_count": host_partner.bookings_count,
                    "revenue_generated": float(host_partner.revenue_generated),
                    "commission_earned": float(host_partner.commission_earned),
                    "average_rating": float(partner.average_rating) if partner.average_rating else None,
                    "status": host_partner.status
                })
            
            # Sort by revenue generated
            performance.sort(key=lambda x: x["revenue_generated"], reverse=True)
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting partner performance: {e}")
            return []
    
    async def get_revenue_tracking(
        self,
        host_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get revenue tracking metrics.
        
        Args:
            host_id: Optional host ID to filter by
            days: Number of days to analyze
            
        Returns:
            Revenue tracking data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get partner commission revenue
            stmt = select(
                func.sum(HostPartner.commission_earned).label('total_commission')
            ).where(
                HostPartner.created_at >= cutoff_date
            )
            
            if host_id:
                stmt = stmt.where(HostPartner.host_id == host_id)
            
            result = await self.db.execute(stmt)
            commission_revenue = result.scalar() or 0.0
            
            # Calculate daily revenue breakdown
            daily_stmt = select(
                func.date(HostPartner.created_at).label('date'),
                func.sum(HostPartner.commission_earned).label('daily_revenue')
            ).where(
                HostPartner.created_at >= cutoff_date
            )
            
            if host_id:
                daily_stmt = daily_stmt.where(HostPartner.host_id == host_id)
            
            daily_stmt = daily_stmt.group_by(func.date(HostPartner.created_at))
            daily_stmt = daily_stmt.order_by(desc('date'))
            
            daily_result = await self.db.execute(daily_stmt)
            daily_rows = daily_result.all()
            
            return {
                "total_commission_revenue": float(commission_revenue),
                "period_days": days,
                "daily_revenue": [
                    {
                        "date": str(row.date),
                        "revenue": float(row.daily_revenue) if row.daily_revenue else 0.0
                    }
                    for row in daily_rows
                ],
                "average_daily_revenue": float(commission_revenue) / days if days > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue tracking: {e}")
            return {
                "total_commission_revenue": 0.0,
                "period_days": days,
                "daily_revenue": [],
                "average_daily_revenue": 0.0
            }
    
    async def export_analytics_report(
        self,
        host_id: Optional[str] = None,
        report_type: str = "comprehensive",
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export comprehensive analytics report.
        
        Args:
            host_id: Optional host ID to filter by
            report_type: Type of report (comprehensive, revenue, satisfaction, partners)
            format: Export format (json, csv)
            
        Returns:
            Report data in requested format
        """
        try:
            report_data = {}
            
            if report_type in ["comprehensive", "satisfaction"]:
                report_data["satisfaction_trends"] = await self.get_guest_satisfaction_trends(host_id)
            
            if report_type in ["comprehensive", "recommendations"]:
                report_data["recommendation_effectiveness"] = await self.get_recommendation_effectiveness(host_id)
            
            if report_type in ["comprehensive", "partners"]:
                report_data["partner_performance"] = await self.get_partner_performance(host_id)
            
            if report_type in ["comprehensive", "revenue"]:
                report_data["revenue_tracking"] = await self.get_revenue_tracking(host_id)
            
            report_data["generated_at"] = datetime.utcnow().isoformat()
            report_data["report_type"] = report_type
            report_data["host_id"] = host_id
            
            if format == "csv":
                # Convert to CSV format (simplified)
                csv_data = self._convert_to_csv(report_data)
                return {"format": "csv", "data": csv_data}
            
            return {"format": "json", "data": report_data}
            
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            return {"format": format, "data": {}, "error": str(e)}
    
    def _convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert report data to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers and data (simplified CSV conversion)
        # In production, this would be more comprehensive
        writer.writerow(["Metric", "Value"])
        
        if "satisfaction_trends" in data:
            writer.writerow(["Overall Average Rating", data["satisfaction_trends"].get("overall_average", 0.0)])
            writer.writerow(["Total Guests", data["satisfaction_trends"].get("total_guests", 0)])
        
        if "revenue_tracking" in data:
            writer.writerow(["Total Commission Revenue", data["revenue_tracking"].get("total_commission_revenue", 0.0)])
        
        return output.getvalue()

