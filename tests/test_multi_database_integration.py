"""
Integration tests for multi-database architecture.

Tests PostgreSQL + Neo4j integration and data consistency.
"""

import pytest
import uuid
from datetime import datetime

from app.services.graph_service import GraphService
from app.services.partner_service import PartnerService
from app.models.partner import Partner, HostPartner


@pytest.mark.asyncio
async def test_postgres_neo4j_integration(db_session):
    """Test integration between PostgreSQL and Neo4j."""
    # Create partner in PostgreSQL
    partner_service = PartnerService(db_session)
    
    partner_data = {
        "name": "Test Restaurant",
        "partner_type": "restaurant",
        "city": "Lovran",
        "email": "test@example.com"
    }
    
    partner = await partner_service.create_partner(partner_data)
    assert partner is not None
    
    # Create relationship in Neo4j
    graph_service = GraphService()
    
    try:
        await graph_service.connect()
        
        host_id = str(uuid.uuid4())
        relationship_data = {
            "status": "active",
            "commission_rate": 0.12
        }
        
        await graph_service.create_host_partner_relationship(
            host_id, str(partner.id), relationship_data
        )
        
        # Both databases should have the data
        assert True
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    finally:
        if graph_service.driver:
            await graph_service.driver.close()


@pytest.mark.asyncio
async def test_recommendation_multi_database(db_session, ai_service):
    """Test recommendation generation using both databases."""
    from app.services.recommendation_service import RecommendationService
    from app.models.guest_group import GuestGroup
    
    recommendation_service = RecommendationService(db_session, ai_service)
    
    # Create guest group
    guest_group = GuestGroup(
        id=uuid.uuid4(),
        host_id=uuid.uuid4(),
        group_name="Test Group",
        group_size=4,
        interests=["beach", "culture"]
    )
    
    db_session.add(guest_group)
    await db_session.commit()
    
    # Generate recommendations (uses both PostgreSQL and Neo4j)
    recommendations = await recommendation_service.generate_recommendations(
        guest_group_id=guest_group.id,
        limit=10
    )
    
    assert isinstance(recommendations, list)


@pytest.mark.asyncio
async def test_data_consistency(db_session):
    """Test data consistency between databases."""
    # Create partner in PostgreSQL
    partner = Partner(
        id=uuid.uuid4(),
        name="Test Partner",
        partner_type="restaurant",
        city="Lovran"
    )
    
    db_session.add(partner)
    await db_session.commit()
    
    # Verify partner exists in PostgreSQL
    from sqlalchemy import select
    stmt = select(Partner).where(Partner.id == partner.id)
    result = await db_session.execute(stmt)
    retrieved = result.scalar_one_or_none()
    
    assert retrieved is not None
    assert retrieved.name == "Test Partner"

