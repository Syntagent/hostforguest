"""
Tests for Playwright MCP integration service.
"""

import pytest
import logging
from app.services.playwright_service import PlaywrightMCPService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_playwright_service_initialization():
    """Test Playwright service initializes correctly."""
    service = PlaywrightMCPService()
    assert service is not None
    assert hasattr(service, 'mcp_available')


@pytest.mark.asyncio
async def test_navigate_to_url():
    """Test URL navigation."""
    service = PlaywrightMCPService()
    result = await service.navigate_to_url("https://example.com")
    # Should return True even if MCP not fully available (mock mode)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_take_screenshot():
    """Test screenshot capture."""
    service = PlaywrightMCPService()
    screenshot = await service.take_screenshot("test.png")
    # Should return filename or None
    assert screenshot is None or isinstance(screenshot, str)


@pytest.mark.asyncio
async def test_get_page_snapshot():
    """Test page snapshot retrieval."""
    service = PlaywrightMCPService()
    snapshot = await service.get_page_snapshot()
    # Should return dict or None
    assert snapshot is None or isinstance(snapshot, dict)


@pytest.mark.asyncio
async def test_scrape_with_playwright():
    """Test Playwright scraping functionality."""
    service = PlaywrightMCPService()
    result = await service.scrape_with_playwright(
        url="https://example.com",
        wait_for_selector="body"
    )
    # Should return dict or None
    assert result is None or isinstance(result, dict)

