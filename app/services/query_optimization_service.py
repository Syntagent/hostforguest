"""
Query optimization service.

Provides utilities for optimizing database queries
and managing materialized views.
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class QueryOptimizationService:
    """
    Service for query optimization and materialized view management.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize query optimization service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def refresh_materialized_views(self) -> bool:
        """
        Refresh all materialized views.
        
        Returns:
            True if refreshed successfully, False otherwise
        """
        try:
            stmt = text("SELECT refresh_materialized_views()")
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info("Materialized views refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing materialized views: {e}")
            await self.db.rollback()
            return False
    
    async def get_host_statistics(
        self,
        host_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get host statistics from materialized view.
        
        Args:
            host_id: Optional host ID filter
            
        Returns:
            List of host statistics
        """
        try:
            if host_id:
                stmt = text("""
                    SELECT * FROM host_statistics
                    WHERE host_id = :host_id
                """)
                result = await self.db.execute(stmt, {"host_id": host_id})
            else:
                stmt = text("SELECT * FROM host_statistics")
                result = await self.db.execute(stmt)
            
            rows = result.fetchall()
            
            return [
                {
                    "host_id": str(row.host_id),
                    "city": row.city,
                    "region": row.region,
                    "total_guest_groups": row.total_guest_groups or 0,
                    "total_attractions": row.total_attractions or 0,
                    "total_recommendation_sets": row.total_recommendation_sets or 0,
                    "avg_satisfaction": float(row.avg_satisfaction) if row.avg_satisfaction else None,
                    "total_revenue": float(row.total_revenue) if row.total_revenue else 0,
                    "total_commission": float(row.total_commission) if row.total_commission else 0
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting host statistics: {e}")
            return []
    
    async def get_attraction_popularity(
        self,
        city: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get attraction popularity from materialized view.
        
        Args:
            city: Optional city filter
            limit: Maximum number of results
            
        Returns:
            List of attraction popularity data
        """
        try:
            if city:
                stmt = text("""
                    SELECT * FROM attraction_popularity
                    WHERE city = :city
                    ORDER BY total_recommendations DESC, avg_rating DESC
                    LIMIT :limit
                """)
                result = await self.db.execute(stmt, {"city": city, "limit": limit})
            else:
                stmt = text("""
                    SELECT * FROM attraction_popularity
                    ORDER BY total_recommendations DESC, avg_rating DESC
                    LIMIT :limit
                """)
                result = await self.db.execute(stmt, {"limit": limit})
            
            rows = result.fetchall()
            
            return [
                {
                    "attraction_id": str(row.attraction_id),
                    "name": row.name,
                    "city": row.city,
                    "attraction_type": row.attraction_type,
                    "total_recommendations": row.total_recommendations or 0,
                    "total_reviews": row.total_reviews or 0,
                    "avg_rating": float(row.avg_rating) if row.avg_rating else None,
                    "accepted_recommendations": row.accepted_recommendations or 0
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting attraction popularity: {e}")
            return []
    
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """
        Analyze query performance and suggest optimizations.
        
        Returns:
            Performance analysis data
        """
        try:
            # Get slow queries from pg_stat_statements (if available)
            stmt = text("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """)
            
            try:
                result = await self.db.execute(stmt)
                slow_queries = result.fetchall()
                
                return {
                    "slow_queries": [
                        {
                            "query": row.query[:200] if row.query else "",
                            "calls": row.calls,
                            "mean_exec_time_ms": float(row.mean_exec_time) if row.mean_exec_time else 0,
                            "max_exec_time_ms": float(row.max_exec_time) if row.max_exec_time else 0
                        }
                        for row in slow_queries
                    ],
                    "recommendations": self._generate_optimization_recommendations(slow_queries)
                }
            except Exception:
                # pg_stat_statements not available
                return {
                    "message": "Query performance analysis requires pg_stat_statements extension",
                    "slow_queries": [],
                    "recommendations": []
                }
            
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return {"error": str(e)}
    
    def _generate_optimization_recommendations(
        self,
        slow_queries: List
    ) -> List[str]:
        """Generate optimization recommendations based on slow queries."""
        recommendations = []
        
        if not slow_queries:
            return ["No slow queries detected"]
        
        # Check for missing indexes
        recommendations.append("Consider adding indexes on frequently queried columns")
        
        # Check for N+1 queries
        if len(slow_queries) > 5:
            recommendations.append("Consider using eager loading to reduce query count")
        
        # Check for full table scans
        recommendations.append("Review queries for potential full table scans")
        
        return recommendations

