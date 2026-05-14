"""
Neo4j database connection manager for graph relationships.

Handles Neo4j connections and graph operations for the Croatian tourist platform.
"""

from typing import Dict, List, Optional, Any
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jManager:
    """
    Neo4j database manager for relationship intelligence.
    
    Handles host-partner relationships, attraction interconnections,
    and guest journey patterns.
    """
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
    
    async def connect(self) -> None:
        """
        Initialize Neo4j driver connection.
        """
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            logger.info("Neo4j driver initialized successfully")
            
            # Test connection
            await self.health_check()
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close Neo4j driver connection.
        """
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j driver closed")
    
    async def get_session(self) -> AsyncSession:
        """
        Get a new Neo4j session.
        
        Returns:
            AsyncSession: Neo4j session
        """
        if not self.driver:
            await self.connect()
        return self.driver.session()
    
    async def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        async with (await self.get_session()) as session:
            try:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"Neo4j query error: {e}")
                raise
    
    async def create_host_node(self, host_id: str, host_data: Dict) -> None:
        """
        Create a host node in the graph.
        
        Args:
            host_id: Unique host identifier
            host_data: Host information
        """
        query = """
        MERGE (h:Host {id: $host_id})
        SET h += $host_data
        SET h.updated_at = datetime()
        RETURN h
        """
        await self.execute_query(query, {
            "host_id": host_id,
            "host_data": host_data
        })
        logger.info(f"Created/updated host node: {host_id}")
    
    async def create_partner_node(self, partner_id: str, partner_data: Dict) -> None:
        """
        Create a business partner node in the graph.
        
        Args:
            partner_id: Unique partner identifier
            partner_data: Partner information
        """
        query = """
        MERGE (p:Partner {id: $partner_id})
        SET p += $partner_data
        SET p.updated_at = datetime()
        RETURN p
        """
        await self.execute_query(query, {
            "partner_id": partner_id,
            "partner_data": partner_data
        })
        logger.info(f"Created/updated partner node: {partner_id}")
    
    async def create_host_partner_relationship(
        self, 
        host_id: str, 
        partner_id: str, 
        relationship_data: Dict
    ) -> None:
        """
        Create a relationship between host and partner.
        
        Args:
            host_id: Host identifier
            partner_id: Partner identifier
            relationship_data: Relationship properties
        """
        query = """
        MATCH (h:Host {id: $host_id})
        MATCH (p:Partner {id: $partner_id})
        MERGE (h)-[r:PARTNERS_WITH]->(p)
        SET r += $relationship_data
        SET r.updated_at = datetime()
        RETURN r
        """
        await self.execute_query(query, {
            "host_id": host_id,
            "partner_id": partner_id,
            "relationship_data": relationship_data
        })
        logger.info(f"Created partnership: {host_id} -> {partner_id}")
    
    async def get_host_partners(self, host_id: str) -> List[Dict]:
        """
        Get all partners for a specific host.
        
        Args:
            host_id: Host identifier
            
        Returns:
            List of partner data with relationship info
        """
        query = """
        MATCH (h:Host {id: $host_id})-[r:PARTNERS_WITH]->(p:Partner)
        RETURN p, r
        ORDER BY r.priority DESC, p.name ASC
        """
        return await self.execute_query(query, {"host_id": host_id})
    
    async def get_attraction_recommendations(
        self, 
        location: str, 
        interests: List[str]
    ) -> List[Dict]:
        """
        Get attraction recommendations based on location and interests.
        
        Args:
            location: Location (e.g., "Lovran")
            interests: List of interest categories
            
        Returns:
            List of recommended attractions
        """
        query = """
        MATCH (a:Attraction)
        WHERE a.location CONTAINS $location
        AND ANY(interest IN $interests WHERE interest IN a.categories)
        RETURN a
        ORDER BY a.rating DESC, a.popularity DESC
        LIMIT 20
        """
        return await self.execute_query(query, {
            "location": location,
            "interests": interests
        })
    
    async def init_graph_schema(self) -> None:
        """
        Initialize Neo4j graph schema with constraints and indexes.
        """
        constraints_and_indexes = [
            # Unique constraints
            "CREATE CONSTRAINT host_id_unique IF NOT EXISTS FOR (h:Host) REQUIRE h.id IS UNIQUE",
            "CREATE CONSTRAINT partner_id_unique IF NOT EXISTS FOR (p:Partner) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT attraction_id_unique IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX host_location_idx IF NOT EXISTS FOR (h:Host) ON (h.location)",
            "CREATE INDEX partner_type_idx IF NOT EXISTS FOR (p:Partner) ON (p.type)",
            "CREATE INDEX attraction_location_idx IF NOT EXISTS FOR (a:Attraction) ON (a.location)",
        ]
        
        for constraint in constraints_and_indexes:
            try:
                session = await self.get_session()
                async with session:
                    await session.run(constraint)
                logger.info(f"Applied constraint/index: {constraint}")
            except Exception as e:
                logger.warning(f"Constraint/index already exists or failed: {e}")
    
    async def health_check(self) -> bool:
        """
        Check Neo4j database health.
        
        Returns:
            bool: True if database is healthy
        """
        try:
            session = await self.get_session()
            async with session:
                result = await session.run("RETURN 1 as health")
                records = await result.data()
                return len(records) > 0 and records[0].get("health") == 1
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False


# Global Neo4j manager instance
neo4j_manager = Neo4jManager()


async def init_neo4j() -> None:
    """
    Initialize Neo4j database connection and schema.
    """
    await neo4j_manager.connect()
    await neo4j_manager.init_graph_schema()
    logger.info("Neo4j initialized successfully")


async def close_neo4j() -> None:
    """
    Close Neo4j database connection.
    """
    await neo4j_manager.close() 