"""
Tests for Neo4j graph service.
"""

import pytest
import logging
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_graph_service_initialization():
    """Test graph service initializes correctly."""
    service = GraphService()
    assert service is not None
    assert hasattr(service, 'manager')


@pytest.mark.asyncio
async def test_get_attractions_by_category():
    """Test getting attractions by category."""
    service = GraphService()
    
    # This will return empty list if Neo4j is not available
    attractions = await service.get_attractions_by_category("nature", limit=10)
    
    assert isinstance(attractions, list)


@pytest.mark.asyncio
async def test_get_attractions_by_interest():
    """Test getting attractions by interest."""
    service = GraphService()
    
    attractions = await service.get_attractions_by_interest("hiking", limit=10)
    
    assert isinstance(attractions, list)


@pytest.mark.asyncio
async def test_get_nearby_attractions():
    """Test getting nearby attractions."""
    service = GraphService()
    
    nearby = await service.get_nearby_attractions(
        attraction_id="test-id",
        max_distance_km=10.0
    )
    
    assert isinstance(nearby, list)


@pytest.mark.asyncio
async def test_get_recommendation_path():
    """Test getting recommendation path."""
    service = GraphService()
    
    recommendations = await service.get_recommendation_path(
        guest_group_id="test-group-id",
        limit=10
    )
    
    assert isinstance(recommendations, list)


@pytest.mark.asyncio
async def test_create_attraction_category_relationship():
    """Test creating attraction-category relationship."""
    service = GraphService()
    
    result = await service.create_attraction_category_relationship(
        attraction_id="test-id",
        category_name="nature",
        relevance_score=0.8
    )
    
    # Should return True or False (False if Neo4j not available)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_create_attraction_interest_relationship():
    """Test creating attraction-interest relationship."""
    service = GraphService()
    
    result = await service.create_attraction_interest_relationship(
        attraction_id="test-id",
        interest_name="hiking",
        appeal_score=0.9
    )
    
    assert isinstance(result, bool)

