"""
Simple guest groups test to verify basic functionality.

This test verifies that the guest groups endpoints work correctly
without complex database operations.
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_guest_groups_endpoint_structure():
    """Test that guest groups endpoints have correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test endpoints that should return 401 (unauthorized) instead of 500 (server error)
        
        # Test create guest group endpoint (should require auth)
        create_response = await client.post("/api/v1/guest-groups/")
        assert create_response.status_code == 401  # Unauthorized, not 500
        
        # Test get host guest groups endpoint (should require auth)
        groups_response = await client.get("/api/v1/guest-groups/host")
        assert groups_response.status_code == 401  # Unauthorized, not 500
        
        print("✅ Guest groups endpoints have correct authentication structure")


@pytest.mark.asyncio
async def test_guest_groups_router_included():
    """Test that guest groups router is properly included in the API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test that the router is included by checking for 401 instead of 404
        response = await client.get("/api/v1/guest-groups/")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 405]  # 401 for auth required, 405 for method not allowed
        
        print("✅ Guest groups router is properly included in API")


@pytest.mark.asyncio
async def test_guest_groups_models_import():
    """Test that guest group models can be imported correctly."""
    try:
        from app.models.guest_group import GuestGroup, GuestGroupCreate, GuestGroupResponse
        print("✅ Guest group models imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import guest group models: {e}")


@pytest.mark.asyncio
async def test_guest_groups_service_import():
    """Test that guest group service can be imported correctly."""
    try:
        from app.services.guest_group_service import GuestGroupService
        print("✅ Guest group service imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import guest group service: {e}")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_guest_groups_endpoint_structure())
    asyncio.run(test_guest_groups_router_included())
    asyncio.run(test_guest_groups_models_import())
    asyncio.run(test_guest_groups_service_import())
    print("✅ All simple guest groups tests passed!")
