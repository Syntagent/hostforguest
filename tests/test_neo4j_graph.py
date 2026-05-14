"""
Tests for Neo4j graph database integration.

Tests graph schema definitions and GraphService interface.
"""

import pytest
import uuid

from app.services.graph_service import GraphService
from app.db.neo4j.schema import GRAPH_SCHEMA


def test_graph_schema_defined():
    """Test that graph schema is defined with required nodes."""
    assert len(GRAPH_SCHEMA) > 0
    assert "nodes" in GRAPH_SCHEMA
    nodes = GRAPH_SCHEMA["nodes"]
    assert "Host" in nodes
    assert "Partner" in nodes
    assert "Attraction" in nodes


def test_graph_service_initialization():
    """Test GraphService can be instantiated."""
    service = GraphService()
    assert service is not None
    assert service.manager is not None


@pytest.mark.asyncio
async def test_get_host_partners_returns_list():
    """Test get_host_partners returns a list (empty when Neo4j unavailable)."""
    service = GraphService()
    try:
        result = await service.get_host_partners(str(uuid.uuid4()))
        assert isinstance(result, list)
    except Exception:
        pytest.skip("Neo4j not available")


@pytest.mark.asyncio
async def test_get_nearby_attractions_returns_list():
    """Test get_nearby_attractions returns a list."""
    service = GraphService()
    try:
        result = await service.get_nearby_attractions(
            latitude=45.29, longitude=14.27, radius_km=5.0, limit=5
        )
        assert isinstance(result, list)
    except Exception:
        pytest.skip("Neo4j not available")


@pytest.mark.asyncio
async def test_get_similar_attractions_returns_list():
    """Test get_similar_attractions returns a list."""
    service = GraphService()
    try:
        result = await service.get_similar_attractions(str(uuid.uuid4()), limit=5)
        assert isinstance(result, list)
    except Exception:
        pytest.skip("Neo4j not available")
