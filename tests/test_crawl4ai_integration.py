"""
Tests for Crawl4AI integration and service.
"""

import pytest
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.crawl4ai_scraper_service import Crawl4AIScraperService, CRAWL4AI_AVAILABLE
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_crawl4ai_service_initialization(db: AsyncSession):
    """Test Crawl4AI service initializes correctly."""
    ai_service = AIService()
    service = Crawl4AIScraperService(db, ai_service)
    assert service is not None
    assert hasattr(service, 'crawler')


@pytest.mark.asyncio
async def test_crawl4ai_context_manager(db: AsyncSession):
    """Test Crawl4AI service context manager."""
    ai_service = AIService()
    async with Crawl4AIScraperService(db, ai_service) as service:
        assert service is not None
        # Service should be usable within context


@pytest.mark.asyncio
async def test_crawl4ai_availability():
    """Test Crawl4AI availability check."""
    # CRAWL4AI_AVAILABLE should be a boolean
    assert isinstance(CRAWL4AI_AVAILABLE, bool)


@pytest.mark.asyncio
async def test_get_real_time_updates(db: AsyncSession):
    """Test getting real-time updates from Crawl4AI."""
    ai_service = AIService()
    async with Crawl4AIScraperService(db, ai_service) as service:
        updates = await service.get_real_time_updates(city="Lovran")
        # Should return a list
        assert isinstance(updates, list)


@pytest.mark.asyncio
async def test_extraction_strategies(db: AsyncSession):
    """Test extraction strategy creation."""
    from app.models.content_source import ContentSource, SourceStatus
    
    ai_service = AIService()
    service = Crawl4AIScraperService(db, ai_service)
    
    # Create a test source
    source = ContentSource(
        name="Test Source",
        url="https://example.com",
        status=SourceStatus.ACTIVE,
        scraping_enabled=True
    )
    
    strategies = service._create_extraction_strategies(source)
    # Should return a dictionary of strategies
    assert isinstance(strategies, dict)

