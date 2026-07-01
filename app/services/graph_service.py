"""
Graph service for Neo4j relationship queries and operations.

Provides high-level graph operations for:
- Host-partner relationships
- Attraction-category-interest relationships
- Geographic proximity queries
- Recommendation path queries
"""

import logging
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j.connection import neo4j_manager
from app.db.neo4j.schema import GraphQueries, NodeLabel, RelationshipType

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for Neo4j graph operations.
    
    Provides high-level methods for relationship queries,
    graph-based recommendations, and network analysis.
    """
    
    def __init__(self):
        """Initialize the graph service."""
        self.manager = neo4j_manager
    
    async def get_host_partners(self, host_id: str) -> List[Dict[str, Any]]:
        """
        Get all partners for a host.
        
        Args:
            host_id: Host identifier
            
        Returns:
            List of partner data with relationship info
        """
        try:
            query = GraphQueries.get_host_partners(host_id)
            results = await self.manager.execute_query(query, {"host_id": host_id})
            
            partners = []
            for record in results:
                partner_data = dict(record.get("p", {}))
                relationship_data = dict(record.get("r", {}))
                partners.append({
                    **partner_data,
                    "relationship": relationship_data
                })
            
            return partners
            
        except Exception as e:
            logger.error(f"Error getting host partners: {e}")
            return []
    
    async def get_attractions_by_category(
        self,
        category: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get attractions in a specific category.
        
        Args:
            category: Category name
            limit: Maximum number of results
            
        Returns:
            List of attractions with relevance scores
        """
        try:
            query = GraphQueries.get_attractions_by_category(category, limit)
            results = await self.manager.execute_query(query, {"category": category})
            
            attractions = []
            for record in results:
                attraction_data = dict(record.get("a", {}))
                relevance = record.get("relevance", 1.0)
                attractions.append({
                    **attraction_data,
                    "relevance_score": relevance
                })
            
            return attractions
            
        except Exception as e:
            logger.error(f"Error getting attractions by category: {e}")
            return []
    
    async def get_attractions_by_interest(
        self,
        interest: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get attractions that appeal to a specific interest.
        
        Args:
            interest: Interest name
            limit: Maximum number of results
            
        Returns:
            List of attractions with appeal scores
        """
        try:
            query = GraphQueries.get_attractions_by_interest(interest, limit)
            results = await self.manager.execute_query(query, {"interest": interest})
            
            attractions = []
            for record in results:
                attraction_data = dict(record.get("a", {}))
                appeal = record.get("appeal", 1.0)
                attractions.append({
                    **attraction_data,
                    "appeal_score": appeal
                })
            
            return attractions
            
        except Exception as e:
            logger.error(f"Error getting attractions by interest: {e}")
            return []
    
    async def get_nearby_attractions(
        self,
        attraction_id: str,
        max_distance_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Get attractions near a specific attraction.
        
        Args:
            attraction_id: Source attraction ID
            max_distance_km: Maximum distance in kilometers
            
        Returns:
            List of nearby attractions with distance info
        """
        try:
            query = GraphQueries.get_nearby_attractions(attraction_id, max_distance_km)
            results = await self.manager.execute_query(query, {
                "attraction_id": attraction_id,
                "max_distance_km": max_distance_km
            })
            
            nearby = []
            for record in results:
                attraction_data = dict(record.get("a2", {}))
                distance = record.get("distance", 0.0)
                travel_time = record.get("travel_time", None)
                nearby.append({
                    **attraction_data,
                    "distance_km": distance,
                    "travel_time_minutes": travel_time
                })
            
            return nearby
            
        except Exception as e:
            logger.error(f"Error getting nearby attractions: {e}")
            return []
    
    async def get_recommendation_path(
        self,
        guest_group_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on guest preferences via graph path.
        
        Args:
            guest_group_id: Guest group identifier
            limit: Maximum number of results
            
        Returns:
            List of recommended attractions with matching interests count
        """
        try:
            query = GraphQueries.get_recommendation_path(guest_group_id, limit)
            results = await self.manager.execute_query(query, {
                "guest_group_id": guest_group_id
            })
            
            recommendations = []
            for record in results:
                attraction_data = dict(record.get("a", {}))
                matching_interests = record.get("matching_interests", 0)
                recommendations.append({
                    **attraction_data,
                    "matching_interests": matching_interests
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendation path: {e}")
            return []
    
    async def get_seasonal_attractions(
        self,
        season: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get attractions available in a specific season.
        
        Args:
            season: Season name (spring, summer, autumn, winter)
            limit: Maximum number of results
            
        Returns:
            List of seasonal attractions with availability scores
        """
        try:
            query = GraphQueries.get_seasonal_attractions(season, limit)
            results = await self.manager.execute_query(query, {"season": season})
            
            attractions = []
            for record in results:
                attraction_data = dict(record.get("a", {}))
                availability = record.get("availability", 1.0)
                attractions.append({
                    **attraction_data,
                    "availability_score": availability
                })
            
            return attractions
            
        except Exception as e:
            logger.error(f"Error getting seasonal attractions: {e}")
            return []
    
    async def create_attraction_category_relationship(
        self,
        attraction_id: str,
        category_name: str,
        relevance_score: float = 1.0
    ) -> bool:
        """
        Create relationship between attraction and category.
        
        Args:
            attraction_id: Attraction identifier
            category_name: Category name
            relevance_score: Relevance score (0-1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = GraphQueries.create_attraction_category_relationship(
                attraction_id, category_name, relevance_score
            )
            await self.manager.execute_query(query, {
                "attraction_id": attraction_id,
                "category_name": category_name,
                "relevance_score": relevance_score
            })
            logger.info(f"Created attraction-category relationship: {attraction_id} -> {category_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating attraction-category relationship: {e}")
            return False
    
    async def create_attraction_interest_relationship(
        self,
        attraction_id: str,
        interest_name: str,
        appeal_score: float = 1.0
    ) -> bool:
        """
        Create relationship between attraction and interest.
        
        Args:
            attraction_id: Attraction identifier
            interest_name: Interest name
            appeal_score: Appeal score (0-1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = GraphQueries.create_attraction_interest_relationship(
                attraction_id, interest_name, appeal_score
            )
            await self.manager.execute_query(query, {
                "attraction_id": attraction_id,
                "interest_name": interest_name,
                "appeal_score": appeal_score
            })
            logger.info(f"Created attraction-interest relationship: {attraction_id} -> {interest_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating attraction-interest relationship: {e}")
            return False
    
    async def create_proximity_relationship(
        self,
        attraction1_id: str,
        attraction2_id: str,
        distance_km: float,
        travel_time_minutes: Optional[float] = None
    ) -> bool:
        """
        Create proximity relationship between two attractions.
        
        Args:
            attraction1_id: First attraction ID
            attraction2_id: Second attraction ID
            distance_km: Distance in kilometers
            travel_time_minutes: Optional travel time in minutes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = GraphQueries.create_proximity_relationship(
                attraction1_id, attraction2_id, distance_km, travel_time_minutes
            )
            await self.manager.execute_query(query, {
                "attraction1_id": attraction1_id,
                "attraction2_id": attraction2_id,
                "distance_km": distance_km,
                "travel_time_minutes": travel_time_minutes
            })
            logger.info(f"Created proximity relationship: {attraction1_id} <-> {attraction2_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating proximity relationship: {e}")
            return False
    
    async def get_geographic_proximity_attractions(
        self,
        city: str,
        region: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get attractions in a city or region.
        
        Args:
            city: City name
            region: Optional region name
            limit: Maximum number of results
            
        Returns:
            List of attractions in the location
        """
        try:
            query = GraphQueries.get_geographic_proximity_attractions(city, region, limit)
            params = {"city": city}
            if region:
                params["region"] = region
            
            results = await self.manager.execute_query(query, params)
            
            attractions = []
            for record in results:
                attraction_data = dict(record.get("a", {}))
                attractions.append(attraction_data)
            
            return attractions
            
        except Exception as e:
            logger.error(f"Error getting geographic proximity attractions: {e}")
            return []
    
    async def get_similar_attractions(
        self,
        attraction_id: str,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get similar attractions based on graph relationships.
        
        Args:
            attraction_id: Source attraction ID
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of similar attractions with similarity scores
        """
        try:
            query = GraphQueries.get_similar_attractions(attraction_id, min_similarity)
            results = await self.manager.execute_query(query, {
                "attraction_id": attraction_id,
                "min_similarity": min_similarity
            })
            
            similar = []
            for record in results:
                attraction_data = dict(record.get("a2", {}))
                similarity = record.get("similarity", 0.0)
                similar.append({
                    **attraction_data,
                    "similarity_score": similarity
                })
            
            return similar
            
        except Exception as e:
            logger.error(f"Error getting similar attractions: {e}")
            return []

