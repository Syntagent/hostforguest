"""
Simple attractions test to verify basic functionality.

This test verifies that the attractions endpoints work correctly
without complex database operations.
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_attractions_endpoint_structure():
    """Test that attractions endpoints have correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test endpoints that should return 401 (unauthorized) instead of 500 (server error)

        # Test create attraction endpoint (should require auth)
        create_response = await client.post("/api/v1/attractions/")
        assert create_response.status_code == 401  # Unauthorized, not 500

        # Test get host attractions endpoint (should require auth)
        attractions_response = await client.get("/api/v1/attractions/host")
        assert attractions_response.status_code == 401  # Unauthorized, not 500

        # Test get all attractions endpoint (public)
        all_attractions_response = await client.get("/api/v1/attractions/")
        assert all_attractions_response.status_code == 200  # Public endpoint

        print("✅ Attractions endpoints have correct authentication structure")


@pytest.mark.asyncio
async def test_attractions_router_included():
    """Test that attractions router is properly included in the API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test that the router is included by checking for 401 instead of 404
        response = await client.get("/api/v1/attractions/")
        # Should return 200 (public endpoint) not 404 (not found)
        assert response.status_code == 200

        print("✅ Attractions router is properly included in API")


@pytest.mark.asyncio
async def test_attractions_models_import():
    """Test that attraction models can be imported correctly."""
    try:
        from app.models.attraction import Attraction, AttractionCreate, AttractionResponse
        print("✅ Attraction models imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import attraction models: {e}")


@pytest.mark.asyncio
async def test_attractions_service_import():
    """Test that attraction service can be imported correctly."""
    try:
        from app.services.attraction_service import AttractionService
        print("✅ Attraction service imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import attraction service: {e}")


@pytest.mark.asyncio
async def test_attractions_api_structure():
    """Test that attractions API returns proper structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test public attractions endpoint
        response = await client.get("/api/v1/attractions/")
        assert response.status_code == 200
        
        attractions_data = response.json()
        assert isinstance(attractions_data, list)
        
        print(f"✅ Attractions API returns proper structure - {len(attractions_data)} attractions")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_attractions_endpoint_structure())
    asyncio.run(test_attractions_router_included())
    asyncio.run(test_attractions_models_import())
    asyncio.run(test_attractions_service_import())
    asyncio.run(test_attractions_api_structure())
    print("✅ All simple attractions tests passed!")
