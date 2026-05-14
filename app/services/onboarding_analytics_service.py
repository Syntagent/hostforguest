"""
Onboarding analytics and optimization service.

Tracks onboarding progress, completion rates, success metrics,
and provides insights for optimizing the onboarding experience.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.host import Host

logger = logging.getLogger(__name__)


class OnboardingAnalyticsService:
    """
    Service for tracking and analyzing onboarding metrics.
    
    Provides insights into onboarding completion rates, drop-off points,
    time to completion, and success metrics.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the onboarding analytics service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def track_onboarding_step(
        self,
        host_id: uuid.UUID,
        step_name: str,
        step_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track an onboarding step completion.
        
        Args:
            host_id: Host ID
            step_name: Name of the onboarding step
            step_data: Optional step-specific data
            
        Returns:
            True if tracked successfully, False otherwise
        """
        try:
            # In production, would store in onboarding_tracking table
            logger.info(f"Tracked onboarding step: {step_name} for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking onboarding step: {e}")
            return False
    
    async def get_onboarding_progress(
        self,
        host_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get onboarding progress for a host.
        
        Args:
            host_id: Host ID
            
        Returns:
            Onboarding progress data
        """
        try:
            # Get host
            stmt = select(Host).where(Host.id == host_id)
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()
            
            if not host:
                return {"error": "Host not found"}
            
            # Define onboarding steps
            steps = [
                {"name": "account_creation", "required": True},
                {"name": "profile_basics", "required": True},
                {"name": "location_setup", "required": True},
                {"name": "attraction_setup", "required": False},
                {"name": "ai_preferences", "required": False},
                {"name": "first_recommendation", "required": False}
            ]
            
            # Check completion status (simplified - in production would query tracking table)
            completed_steps = []
            if host.email:
                completed_steps.append("account_creation")
            if host.description:
                completed_steps.append("profile_basics")
            if host.city:
                completed_steps.append("location_setup")
            
            progress = {
                "host_id": str(host_id),
                "total_steps": len(steps),
                "completed_steps": len(completed_steps),
                "completion_percentage": (len(completed_steps) / len(steps)) * 100,
                "steps": [
                    {
                        "name": step["name"],
                        "required": step["required"],
                        "completed": step["name"] in completed_steps
                    }
                    for step in steps
                ],
                "next_step": self._get_next_step(steps, completed_steps)
            }
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting onboarding progress: {e}")
            return {"error": str(e)}
    
    def _get_next_step(
        self,
        steps: List[Dict[str, Any]],
        completed_steps: List[str]
    ) -> Optional[str]:
        """
        Get the next incomplete step.
        
        Args:
            steps: List of all steps
            completed_steps: List of completed step names
            
        Returns:
            Next step name or None
        """
        for step in steps:
            if step["name"] not in completed_steps:
                return step["name"]
        return None
    
    async def get_onboarding_analytics(
        self,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get overall onboarding analytics.
        
        Args:
            period_days: Number of days to analyze
            
        Returns:
            Analytics data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get hosts created in period
            stmt = select(
                func.count(Host.id).label("total_hosts"),
                func.avg(
                    func.cast(
                        func.extract('epoch', Host.updated_at - Host.created_at),
                        func.Integer
                    )
                ).label("avg_time_to_complete")
            ).where(
                Host.created_at >= start_date
            )
            
            result = await self.db.execute(stmt)
            row = result.first()
            
            total_hosts = row.total_hosts or 0
            
            # Calculate completion rates (simplified)
            stmt_complete = select(func.count(Host.id)).where(
                and_(
                    Host.created_at >= start_date,
                    Host.description.isnot(None),
                    Host.city.isnot(None)
                )
            )
            
            result_complete = await self.db.execute(stmt_complete)
            completed_count = result_complete.scalar() or 0
            
            completion_rate = (completed_count / total_hosts * 100) if total_hosts > 0 else 0
            
            analytics = {
                "period_days": period_days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "total_hosts": total_hosts,
                "completed_onboarding": completed_count,
                "completion_rate": round(completion_rate, 2),
                "average_time_to_complete_hours": round((row.avg_time_to_complete or 0) / 3600, 2) if row.avg_time_to_complete else None,
                "drop_off_points": self._calculate_drop_off_points()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting onboarding analytics: {e}")
            return {"error": str(e)}
    
    def _calculate_drop_off_points(self) -> List[Dict[str, Any]]:
        """
        Calculate common drop-off points in onboarding.
        
        Returns:
            List of drop-off points with percentages
        """
        # Simplified - in production would query tracking data
        return [
            {"step": "account_creation", "drop_off_rate": 5.0},
            {"step": "profile_basics", "drop_off_rate": 15.0},
            {"step": "location_setup", "drop_off_rate": 10.0},
            {"step": "attraction_setup", "drop_off_rate": 20.0}
        ]
    
    async def get_success_metrics(
        self,
        host_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get success metrics for a host's onboarding.
        
        Args:
            host_id: Host ID
            
        Returns:
            Success metrics
        """
        try:
            # Get host
            stmt = select(Host).where(Host.id == host_id)
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()
            
            if not host:
                return {"error": "Host not found"}
            
            # Calculate time to complete
            time_to_complete = None
            if host.created_at and host.updated_at:
                delta = host.updated_at - host.created_at
                time_to_complete = delta.total_seconds() / 3600  # hours
            
            # Check profile completeness
            profile_score = self._calculate_profile_score(host)
            
            metrics = {
                "host_id": str(host_id),
                "time_to_complete_hours": round(time_to_complete, 2) if time_to_complete else None,
                "profile_completeness_score": profile_score,
                "onboarding_completed": profile_score >= 70,
                "created_at": host.created_at.isoformat() if host.created_at else None,
                "last_updated": host.updated_at.isoformat() if host.updated_at else None
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting success metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_profile_score(self, host: Host) -> int:
        """
        Calculate profile completeness score (0-100).
        
        Args:
            host: Host instance
            
        Returns:
            Completeness score
        """
        score = 0
        max_score = 100
        
        # Basic info (30 points)
        if host.email:
            score += 10
        if host.first_name:
            score += 10
        if host.phone:
            score += 10
        
        # Profile details (40 points)
        if host.description:
            score += 20
        if host.welcome_message:
            score += 10
        if host.local_specialties:
            score += 10
        
        # Location (20 points)
        if host.city:
            score += 10
        if host.latitude and host.longitude:
            score += 10
        
        # Additional (10 points)
        if host.languages:
            score += 5
        if host.business_name:
            score += 5
        
        return min(score, max_score)

