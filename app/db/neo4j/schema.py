"""
Neo4j graph schema definitions for TouristGuideLocal.

Defines node types, relationships, and graph patterns for:
- Host-Partner relationships
- Attraction-Category-Interest relationships
- Geographic proximity relationships
- Guest preference patterns
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


# Node Labels
class NodeLabel:
    """Node labels in the graph."""
    HOST = "Host"
    PARTNER = "Partner"
    ATTRACTION = "Attraction"
    CATEGORY = "Category"
    INTEREST = "Interest"
    GUEST_GROUP = "GuestGroup"
    SEASON = "Season"
    REGION = "Region"
    CITY = "City"


# Relationship Types
class RelationshipType:
    """Relationship types in the graph."""
    PARTNERS_WITH = "PARTNERS_WITH"
    IN_CATEGORY = "IN_CATEGORY"
    APPEALS_TO = "APPEALS_TO"
    NEAR = "NEAR"
    PREFERS = "PREFERS"
    AVAILABLE_IN = "AVAILABLE_IN"
    LOCATED_IN = "LOCATED_IN"
    RECOMMENDED_FOR = "RECOMMENDED_FOR"
    SIMILAR_TO = "SIMILAR_TO"


# Graph Schema Definition
GRAPH_SCHEMA = {
    "nodes": {
        "Host": {
            "properties": ["id", "name", "email", "city", "region", "latitude", "longitude"],
            "indexes": ["id", "city", "region"]
        },
        "Partner": {
            "properties": ["id", "name", "type", "category", "city", "region", "rating"],
            "indexes": ["id", "type", "category", "city"]
        },
        "Attraction": {
            "properties": ["id", "name", "type", "category", "city", "region", "rating"],
            "indexes": ["id", "type", "category", "city"]
        },
        "Category": {
            "properties": ["name", "description"],
            "indexes": ["name"]
        },
        "Interest": {
            "properties": ["name", "description"],
            "indexes": ["name"]
        },
        "Season": {
            "properties": ["name", "months"],
            "indexes": ["name"]
        },
        "Region": {
            "properties": ["name", "country"],
            "indexes": ["name"]
        },
        "City": {
            "properties": ["name", "region", "country"],
            "indexes": ["name", "region"]
        }
    },
    "relationships": {
        "PARTNERS_WITH": {
            "from": "Host",
            "to": "Partner",
            "properties": ["priority", "commission_rate", "created_at", "status"]
        },
        "IN_CATEGORY": {
            "from": "Attraction",
            "to": "Category",
            "properties": ["relevance_score"]
        },
        "APPEALS_TO": {
            "from": "Attraction",
            "to": "Interest",
            "properties": ["appeal_score"]
        },
        "NEAR": {
            "from": "Attraction",
            "to": "Attraction",
            "properties": ["distance_km", "travel_time_minutes"]
        },
        "PREFERS": {
            "from": "GuestGroup",
            "to": "Interest",
            "properties": ["preference_strength"]
        },
        "AVAILABLE_IN": {
            "from": "Attraction",
            "to": "Season",
            "properties": ["availability_score"]
        },
        "LOCATED_IN": {
            "from": "Attraction",
            "to": "City",
            "properties": []
        },
        "SIMILAR_TO": {
            "from": "Attraction",
            "to": "Attraction",
            "properties": ["similarity_score"]
        }
    }
}


# Cypher Query Templates
class GraphQueries:
    """Common Cypher query templates."""
    
    @staticmethod
    def get_host_partners(host_id: str) -> str:
        """Get all partners for a host."""
        return """
        MATCH (h:Host {id: $host_id})-[r:PARTNERS_WITH]->(p:Partner)
        RETURN p, r
        ORDER BY r.priority DESC, p.name ASC
        """
    
    @staticmethod
    def get_attractions_by_category(category: str, limit: int = 20) -> str:
        """Get attractions in a specific category."""
        return f"""
        MATCH (a:Attraction)-[r:IN_CATEGORY]->(c:Category {{name: $category}})
        RETURN a, r.relevance_score as relevance
        ORDER BY relevance DESC, a.rating DESC
        LIMIT {limit}
        """
    
    @staticmethod
    def get_attractions_by_interest(interest: str, limit: int = 20) -> str:
        """Get attractions that appeal to a specific interest."""
        return f"""
        MATCH (a:Attraction)-[r:APPEALS_TO]->(i:Interest {{name: $interest}})
        RETURN a, r.appeal_score as appeal
        ORDER BY appeal DESC, a.rating DESC
        LIMIT {limit}
        """
    
    @staticmethod
    def get_nearby_attractions(attraction_id: str, max_distance_km: float = 10.0) -> str:
        """Get attractions near a specific attraction."""
        return f"""
        MATCH (a1:Attraction {{id: $attraction_id}})-[r:NEAR]-(a2:Attraction)
        WHERE r.distance_km <= $max_distance_km
        RETURN a2, r.distance_km as distance, r.travel_time_minutes as travel_time
        ORDER BY distance ASC
        LIMIT 20
        """
    
    @staticmethod
    def get_recommendation_path(guest_group_id: str, limit: int = 10) -> str:
        """Get recommendations based on guest preferences via graph path."""
        return f"""
        MATCH (gg:GuestGroup {{id: $guest_group_id}})-[:PREFERS]->(i:Interest)
        MATCH (a:Attraction)-[:APPEALS_TO]->(i)
        RETURN DISTINCT a, count(i) as matching_interests
        ORDER BY matching_interests DESC, a.rating DESC
        LIMIT {limit}
        """
    
    @staticmethod
    def get_seasonal_attractions(season: str, limit: int = 20) -> str:
        """Get attractions available in a specific season."""
        return f"""
        MATCH (a:Attraction)-[r:AVAILABLE_IN]->(s:Season {{name: $season}})
        RETURN a, r.availability_score as availability
        ORDER BY availability DESC, a.rating DESC
        LIMIT {limit}
        """
    
    @staticmethod
    def get_geographic_proximity_attractions(
        city: str,
        region: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Get attractions in a city or region."""
        if region:
            return f"""
            MATCH (a:Attraction)-[:LOCATED_IN]->(c:City {{name: $city}})
            WHERE c.region = $region
            RETURN a
            ORDER BY a.rating DESC
            LIMIT {limit}
            """
        else:
            return f"""
            MATCH (a:Attraction)-[:LOCATED_IN]->(c:City {{name: $city}})
            RETURN a
            ORDER BY a.rating DESC
            LIMIT {limit}
            """
    
    @staticmethod
    def get_similar_attractions(attraction_id: str, min_similarity: float = 0.7) -> str:
        """Get similar attractions based on graph relationships."""
        return f"""
        MATCH (a1:Attraction {{id: $attraction_id}})-[r:SIMILAR_TO]-(a2:Attraction)
        WHERE r.similarity_score >= $min_similarity
        RETURN a2, r.similarity_score as similarity
        ORDER BY similarity DESC
        LIMIT 10
        """
    
    @staticmethod
    def create_attraction_category_relationship(
        attraction_id: str,
        category_name: str,
        relevance_score: float = 1.0
    ) -> str:
        """Create relationship between attraction and category."""
        return """
        MATCH (a:Attraction {id: $attraction_id})
        MERGE (c:Category {name: $category_name})
        MERGE (a)-[r:IN_CATEGORY]->(c)
        SET r.relevance_score = $relevance_score
        RETURN r
        """
    
    @staticmethod
    def create_attraction_interest_relationship(
        attraction_id: str,
        interest_name: str,
        appeal_score: float = 1.0
    ) -> str:
        """Create relationship between attraction and interest."""
        return """
        MATCH (a:Attraction {id: $attraction_id})
        MERGE (i:Interest {name: $interest_name})
        MERGE (a)-[r:APPEALS_TO]->(i)
        SET r.appeal_score = $appeal_score
        RETURN r
        """
    
    @staticmethod
    def create_proximity_relationship(
        attraction1_id: str,
        attraction2_id: str,
        distance_km: float,
        travel_time_minutes: Optional[float] = None
    ) -> str:
        """Create proximity relationship between two attractions."""
        return """
        MATCH (a1:Attraction {id: $attraction1_id})
        MATCH (a2:Attraction {id: $attraction2_id})
        MERGE (a1)-[r:NEAR]-(a2)
        SET r.distance_km = $distance_km
        SET r.travel_time_minutes = $travel_time_minutes
        RETURN r
        """


# Schema Initialization Queries
SCHEMA_INIT_QUERIES = [
    # Unique constraints
    "CREATE CONSTRAINT host_id_unique IF NOT EXISTS FOR (h:Host) REQUIRE h.id IS UNIQUE",
    "CREATE CONSTRAINT partner_id_unique IF NOT EXISTS FOR (p:Partner) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT attraction_id_unique IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT interest_name_unique IF NOT EXISTS FOR (i:Interest) REQUIRE i.name IS UNIQUE",
    
    # Indexes
    "CREATE INDEX host_city_idx IF NOT EXISTS FOR (h:Host) ON (h.city)",
    "CREATE INDEX host_region_idx IF NOT EXISTS FOR (h:Host) ON (h.region)",
    "CREATE INDEX partner_type_idx IF NOT EXISTS FOR (p:Partner) ON (p.type)",
    "CREATE INDEX partner_category_idx IF NOT EXISTS FOR (p:Partner) ON (p.category)",
    "CREATE INDEX attraction_type_idx IF NOT EXISTS FOR (a:Attraction) ON (a.type)",
    "CREATE INDEX attraction_category_idx IF NOT EXISTS FOR (a:Attraction) ON (a.category)",
    "CREATE INDEX attraction_city_idx IF NOT EXISTS FOR (a:Attraction) ON (a.city)",
    "CREATE INDEX category_name_idx IF NOT EXISTS FOR (c:Category) ON (c.name)",
    "CREATE INDEX interest_name_idx IF NOT EXISTS FOR (i:Interest) ON (i.name)",
]

