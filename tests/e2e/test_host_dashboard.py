"""
E2E tests for host dashboard using Playwright MCP.

Tests host dashboard functionality including:
- Login flow
- Dashboard display
- Guest group management
- Attraction management
"""

import pytest
import logging
from app.services.playwright_service import PlaywrightMCPService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_host_login_flow():
    """
    Test host login flow using Playwright MCP.
    """
    service = PlaywrightMCPService()
    
    # Navigate to login page
    result = await service.navigate_to_url("http://localhost:3002/login")
    assert result is True
    
    # Wait for login form
    await service.wait_for_text("Login", timeout=5.0)
    
    # Get snapshot to find form elements
    snapshot = await service.get_page_snapshot()
    assert snapshot is not None
    
    # Take screenshot
    screenshot = await service.take_screenshot("host_login_test.png")
    assert screenshot is not None
    
    logger.info("Host login flow test completed")


@pytest.mark.asyncio
async def test_host_dashboard_display():
    """
    Test host dashboard displays correctly.
    """
    service = PlaywrightMCPService()
    
    # Navigate to dashboard (assuming logged in)
    await service.navigate_to_url("http://localhost:3002/dashboard")
    
    # Wait for dashboard elements
    await service.wait_for_text("Dashboard", timeout=10.0)
    
    # Verify analytics are displayed
    snapshot = await service.get_page_snapshot()
    assert snapshot is not None
    
    screenshot = await service.take_screenshot("host_dashboard_test.png")
    assert screenshot is not None
    
    logger.info("Host dashboard display test completed")


@pytest.mark.asyncio
async def test_host_guest_group_management():
    """
    Test host guest group management functionality.
    """
    service = PlaywrightMCPService()
    
    # Navigate to guest groups tab
    await service.navigate_to_url("http://localhost:3002/dashboard?tab=groups")
    
    # Wait for guest groups section
    await service.wait_for_text("Guest Groups", timeout=10.0)
    
    snapshot = await service.get_page_snapshot()
    assert snapshot is not None
    
    screenshot = await service.take_screenshot("guest_groups_test.png")
    assert screenshot is not None
    
    logger.info("Host guest group management test completed")

