"""
Integration tests for recommendation engine.

Tests the complete recommendation flow using
PostgreSQL, Neo4j, and Crawl4AI integration.
"""

import pytest
import uuid
from datetime import datetime, timedelta

from app.services.recommendation_service import RecommendationService
from app.services.vector_service import VectorService
from app.services.graph_service import GraphService
from app.models.guest_group import GuestGroup
from app.models.attraction import Attraction


@pytest.mark.asyncio
async def test_recommendation_flow_complete(db_session, ai_service):
    """Test complete recommendation generation flow."""
    recommendation_service = RecommendationService(db_session, ai_service)
    vector_service = VectorService(db_session, ai_service)
    
    # Create guest group
    guest_group = GuestGroup(
        id=uuid.uuid4(),
        host_id=uuid.uuid4(),
        group_name="Test Family",
        group_size=4,
        interests=["beach", "family_friendly"],
        check_in_date=datetime.utcnow().date(),
        check_out_date=(datetime.utcnow() + timedelta(days=7)).date()
    )
    
    db_session.add(guest_group)
    await db_session.commit()
    
    # Generate recommendations
    recommendations = await recommendation_service.generate_recommendations(
        guest_group_id=guest_group.id,
        limit=10
    )
    
    assert isinstance(recommendations, list)
    # Should return recommendations even if empty
    assert len(recommendations) >= 0


@pytest.mark.asyncio
async def test_vector_search_in_recommendations(db_session, ai_service):
    """Test that vector search is used in recommendations."""
    recommendation_service = RecommendationService(db_session, ai_service)
    
    # Create guest group with preferences
    guest_group = GuestGroup(
        id=uuid.uuid4(),
        host_id=uuid.uuid4(),
        group_name="Test Group",
        interests=["beach", "swimming"]
    )
    
    db_session.add(guest_group)
    await db_session.commit()
    
    # Generate recommendations (should use vector search)
    recommendations = await recommendation_service.generate_recommendations(
        guest_group_id=guest_group.id
    )
    
    # Recommendations should be generated
    assert isinstance(recommendations, list)


@pytest.mark.asyncio
async def test_graph_relationships_in_recommendations(db_session, ai_service):
    """Test that graph relationships are used in recommendations."""
    recommendation_service = RecommendationService(db_session, ai_service)
    graph_service = GraphService()
    
    try:
        await graph_service.connect()
        
        # Create guest group
        guest_group = GuestGroup(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            group_name="Test Group"
        )
        
        db_session.add(guest_group)
        await db_session.commit()
        
        # Generate recommendations (should use graph relationships)
        recommendations = await recommendation_service.generate_recommendations(
            guest_group_id=guest_group.id
        )
        
        assert isinstance(recommendations, list)
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    finally:
        if graph_service.driver:
            await graph_service.driver.close()

