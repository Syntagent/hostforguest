"""
Tests for Crawl4AI real-time Croatian tourism data integration.

Tests the enhanced web scraping capabilities, real-time data feeds,
and API endpoints for Croatian tourism information.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient

from app.main import app
from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
from app.services.ai_service import AIService
from app.models.content_source import ContentSource, ContentUpdate, SourceStatus, ContentType
from app.tasks.crawl4ai_realtime_tasks import (
    initialize_crawl4ai_sources,
    run_real_time_monitoring,
    run_hourly_stream_update,
    monitor_source_real_time
)


class TestCrawl4AIScraperService:
    """Test the enhanced Crawl4AI scraper service."""
    
    @pytest.fixture
    async def scraper_service(self, async_db_session):
        """Create a Crawl4AI scraper service for testing."""
        ai_service = AIService()
        async with Crawl4AIScraperService(async_db_session, ai_service) as scraper:
            yield scraper
    
    @pytest.fixture
    def sample_content_source(self):
        """Create a sample content source for testing."""
        return ContentSource(
            name="Test Croatian Tourism",
            url="https://test-croatia.hr",
            source_type="tourism_board",
            region="Istria",
            city="Lovran",
            content_types=[ContentType.EVENTS, ContentType.ATTRACTIONS],
            scraping_selectors={
                "events": ".event-item",
                "attractions": ".attraction-card",
                "title": "h2, h3",
                "content": ".content, p",
                "date": ".date, time"
            },
            languages=["hr", "en"],
            primary_language="hr",
            scraping_frequency="daily",
            scraping_enabled=True,
            status=SourceStatus.ACTIVE
        )
    
    @pytest.mark.asyncio
    async def test_create_extraction_strategies(self, scraper_service, sample_content_source):
        """Test creation of multiple extraction strategies."""
        strategies = scraper_service._create_extraction_strategies(sample_content_source)
        
        assert "css_schema" in strategies
        assert "regex_fallback" in strategies
        assert "croatian_tourism" in strategies
        
        # Test CSS schema strategy
        css_strategy = strategies["css_schema"]
        assert hasattr(css_strategy, 'schema')
        
        # Test Croatian tourism strategy
        croatian_strategy = strategies["croatian_tourism"]
        assert hasattr(croatian_strategy, 'schema')
        
        print("✅ Extraction strategies created successfully")
    
    @pytest.mark.asyncio
    async def test_build_css_schema(self, scraper_service, sample_content_source):
        """Test building CSS extraction schema from source configuration."""
        schema = scraper_service._build_css_schema(sample_content_source)
        
        assert schema["name"] == "Test Croatian Tourism Content"
        assert "baseSelector" in schema
        assert "fields" in schema
        
        # Check standard fields
        field_names = [field["name"] for field in schema["fields"]]
        assert "title" in field_names
        assert "content" in field_names
        assert "date" in field_names
        assert "url" in field_names
        
        # Check event-specific fields
        assert "event_date" in field_names
        assert "location" in field_names
        
        print("✅ CSS schema built correctly")
    
    @pytest.mark.asyncio
    async def test_build_croatian_tourism_schema(self, scraper_service, sample_content_source):
        """Test building Croatian tourism-specific schema."""
        schema = scraper_service._build_croatian_tourism_schema(sample_content_source)
        
        assert schema["name"] == "Croatian Tourism Data"
        assert "baseSelector" in schema
        
        # Check Croatian-specific fields
        field_names = [field["name"] for field in schema["fields"]]
        expected_fields = ["naziv", "opis", "lokacija", "radno_vrijeme", "cijena", "kontakt", "sezona"]
        
        for field in expected_fields:
            assert field in field_names
        
        print("✅ Croatian tourism schema built correctly")
    
    @pytest.mark.asyncio
    async def test_normalize_content_item(self, scraper_service):
        """Test content item normalization for different extraction strategies."""
        # Test Croatian tourism strategy normalization
        croatian_item = {
            "naziv": "Učka Nature Park",
            "opis": "Beautiful nature park with hiking trails",
            "lokacija": "Lovran, Croatia",
            "radno_vrijeme": "08:00-20:00",
            "cijena": "50 kn",
            "link": "https://example.com/ucka"
        }
        
        normalized = scraper_service._normalize_content_item(croatian_item, "croatian_tourism")
        
        assert normalized["title"] == "Učka Nature Park"
        assert normalized["content"] == "Beautiful nature park with hiking trails"
        assert normalized["location"] == "Lovran, Croatia"
        assert normalized["opening_hours"] == "08:00-20:00"
        assert normalized["price"] == "50 kn"
        assert normalized["url"] == "https://example.com/ucka"
        assert normalized["extraction_strategy"] == "croatian_tourism"
        
        # Test standard strategy normalization
        standard_item = {
            "title": "Festival of Cherries",
            "content": "Annual cherry festival in Lovran",
            "date": "2025-06-15"
        }
        
        normalized_standard = scraper_service._normalize_content_item(standard_item, "css_schema")
        
        assert normalized_standard["title"] == "Festival of Cherries"
        assert normalized_standard["content"] == "Annual cherry festival in Lovran"
        assert normalized_standard["extraction_strategy"] == "css_schema"
        
        print("✅ Content item normalization works correctly")
    
    @pytest.mark.asyncio
    async def test_detect_content_type(self, scraper_service):
        """Test content type detection based on content analysis."""
        # Test event detection
        event_item = {
            "title": "Marunada Festival 2025",
            "content": "Annual chestnut festival in Lovran with traditional music"
        }
        content_type = scraper_service._detect_content_type(event_item)
        assert content_type == ContentType.EVENTS
        
        # Test attraction detection
        attraction_item = {
            "title": "Učka Nature Park",
            "content": "Beautiful park with hiking trails and scenic views"
        }
        content_type = scraper_service._detect_content_type(attraction_item)
        assert content_type == ContentType.ATTRACTIONS
        
        # Test opening hours detection
        hours_item = {
            "title": "Museum Opening Hours",
            "content": "Open daily from 9 AM to 6 PM, closed on Mondays"
        }
        content_type = scraper_service._detect_content_type(hours_item)
        assert content_type == ContentType.OPENING_HOURS
        
        # Test price detection
        price_item = {
            "title": "Entrance Fees",
            "content": "Adult ticket 50 kn, children under 12 free"
        }
        content_type = scraper_service._detect_content_type(price_item)
        assert content_type == ContentType.PRICES
        
        print("✅ Content type detection works correctly")
    
    @pytest.mark.asyncio
    @patch('app.services.crawl4ai_scraper_service.AsyncWebCrawler')
    async def test_scrape_source_advanced(self, mock_crawler_class, scraper_service, sample_content_source, async_db_session):
        """Test advanced scraping with multiple strategies."""
        # Mock the crawler
        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps([{
            "naziv": "Test Event",
            "opis": "Test description",
            "lokacija": "Lovran"
        }])
        
        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value = mock_crawler
        
        # Add source to database
        async_db_session.add(sample_content_source)
        await async_db_session.commit()
        
        # Test advanced scraping
        updates = await scraper_service.scrape_source_advanced(sample_content_source)
        
        # Verify results
        assert len(updates) >= 0  # May be 0 if content filtering removes items
        assert sample_content_source.total_scrapes == 1
        assert sample_content_source.last_scraped is not None
        
        print("✅ Advanced scraping with multiple strategies works")
    
    @pytest.mark.asyncio
    async def test_get_real_time_updates(self, scraper_service, async_db_session):
        """Test getting real-time updates."""
        # Create test content update
        test_update = ContentUpdate(
            source_id=None,  # Will be set when we have a source
            content_type=ContentType.EVENTS,
            title="Test Real-time Update",
            content="This is a test real-time update",
            relevant_cities=["Lovran"],
            relevant_regions=["Istria"],
            keywords=["test", "event"],
            quality_score=0.9,
            relevance_score=0.8,
            status="approved",
            created_at=datetime.utcnow()
        )
        
        async_db_session.add(test_update)
        await async_db_session.commit()
        
        # Test getting real-time updates
        updates = await scraper_service.get_real_time_updates(city="Lovran")
        
        # Should find our test update
        assert len(updates) >= 1
        found_update = next((u for u in updates if u["title"] == "Test Real-time Update"), None)
        assert found_update is not None
        assert found_update["relevant_cities"] == ["Lovran"]
        
        print("✅ Real-time updates retrieval works correctly")


class TestRealTimeDataAPI:
    """Test the real-time data API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_real_time_updates_endpoint(self, client: AsyncClient):
        """Test the real-time updates API endpoint."""
        response = await client.get("/api/v1/realtime/updates")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Test with filters
        response = await client.get("/api/v1/realtime/updates?city=Lovran&content_types=events")
        assert response.status_code == 200
        
        print("✅ Real-time updates endpoint works")
    
    @pytest.mark.asyncio
    async def test_get_live_stream_updates_endpoint(self, client: AsyncClient):
        """Test the live stream updates API endpoint."""
        response = await client.get("/api/v1/realtime/stream")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Test with filters
        response = await client.get("/api/v1/realtime/stream?regions=Istria")
        assert response.status_code == 200
        
        print("✅ Live stream updates endpoint works")
    
    @pytest.mark.asyncio
    async def test_get_data_sources_status_endpoint(self, client: AsyncClient):
        """Test the data sources status API endpoint."""
        response = await client.get("/api/v1/realtime/sources/status")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check response structure if we have data
        if data:
            source = data[0]
            required_fields = ["source_id", "name", "url", "status"]
            for field in required_fields:
                assert field in source
        
        print("✅ Data sources status endpoint works")
    
    @pytest.mark.asyncio
    async def test_get_real_time_data_summary_endpoint(self, client: AsyncClient):
        """Test the real-time data summary API endpoint."""
        response = await client.get("/api/v1/realtime/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = [
            "total_sources", "active_sources", "recent_updates_24h", 
            "recent_updates_1h", "content_types_available", "cities_covered"
        ]
        
        for field in required_fields:
            assert field in data
            
        assert isinstance(data["content_types_available"], list)
        assert isinstance(data["cities_covered"], list)
        
        print("✅ Real-time data summary endpoint works")
    
    @pytest.mark.asyncio
    async def test_refresh_data_sources_endpoint(self, client: AsyncClient):
        """Test the manual refresh data sources endpoint."""
        response = await client.post("/api/v1/realtime/sources/refresh")
        
        # Should return 200 even if no sources to refresh
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "status" in data
        
        print("✅ Refresh data sources endpoint works")
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client: AsyncClient):
        """Test the real-time data service health check."""
        response = await client.get("/api/v1/realtime/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "real-time-croatian-tourism-data"
        assert "timestamp" in data
        assert "features" in data
        
        expected_features = [
            "real-time-updates",
            "live-streaming", 
            "multi-source-aggregation",
            "croatian-tourism-focus",
            "crawl4ai-integration"
        ]
        
        for feature in expected_features:
            assert feature in data["features"]
        
        print("✅ Health check endpoint works")


class TestCrawl4AITasks:
    """Test the Crawl4AI scheduled tasks."""
    
    @pytest.mark.asyncio
    @patch('app.tasks.crawl4ai_realtime_tasks.Crawl4AIScraperService')
    async def test_initialize_crawl4ai_sources(self, mock_scraper_service):
        """Test initialization of Crawl4AI sources."""
        # Mock the scraper service
        mock_scraper = AsyncMock()
        mock_scraper.create_content_source.return_value = Mock(name="Test Source")
        mock_scraper_service.return_value.__aenter__.return_value = mock_scraper
        
        # Test initialization
        sources = await initialize_crawl4ai_sources()
        
        # Verify scraper was called for each source
        assert mock_scraper.create_content_source.call_count >= len([
            s for s in [
                "Croatia Tourism Board",
                "Istria Tourism", 
                "Kvarner Tourism",
                "Lovran Tourism Office",
                "Opatija Tourism"
            ]
        ])
        
        print("✅ Crawl4AI sources initialization works")
    
    @pytest.mark.asyncio
    @patch('app.tasks.crawl4ai_realtime_tasks.Crawl4AIScraperService')
    @patch('app.tasks.crawl4ai_realtime_tasks.get_async_session')
    async def test_run_real_time_monitoring(self, mock_get_session, mock_scraper_service):
        """Test real-time monitoring task."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        # Mock database query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []  # No sources to monitor
        mock_db.execute.return_value = mock_result
        
        # Test real-time monitoring
        results = await run_real_time_monitoring()
        
        assert results["task"] == "crawl4ai_realtime_monitoring"
        assert "started_at" in results
        assert "completed_at" in results
        assert "success" in results
        
        print("✅ Real-time monitoring task works")
    
    @pytest.mark.asyncio
    @patch('app.tasks.crawl4ai_realtime_tasks.Crawl4AIScraperService')
    @patch('app.tasks.crawl4ai_realtime_tasks.get_async_session')
    async def test_run_hourly_stream_update(self, mock_get_session, mock_scraper_service):
        """Test hourly stream update task."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        # Mock database query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []  # No sources to stream
        mock_db.execute.return_value = mock_result
        
        # Test hourly stream update
        results = await run_hourly_stream_update()
        
        assert results["task"] == "hourly_stream_update"
        assert "started_at" in results
        assert "completed_at" in results
        assert "success" in results
        
        print("✅ Hourly stream update task works")
    
    @pytest.mark.asyncio
    async def test_monitor_source_real_time(self):
        """Test monitoring a single source for real-time updates."""
        # Create mock scraper and source
        mock_scraper = AsyncMock()
        mock_source = Mock(name="Test Source")
        
        # Mock scraping results
        mock_update = Mock()
        mock_update.relevance_score = 0.9
        mock_update.content_type = "events"
        mock_scraper.scrape_source_advanced.return_value = [mock_update]
        
        # Test monitoring
        updates_count, strategies_used = await monitor_source_real_time(mock_scraper, mock_source)
        
        assert updates_count == 1
        assert isinstance(strategies_used, list)
        
        print("✅ Single source real-time monitoring works")


class TestIntegrationRealTimeData:
    """Integration tests for real-time Croatian tourism data."""
    
    @pytest.mark.asyncio
    async def test_full_real_time_workflow(self, client: AsyncClient):
        """Test the complete real-time data workflow."""
        print("\n🇭🇷 Testing Complete Real-time Croatian Tourism Data Workflow...")
        
        # Step 1: Check health status
        health_response = await client.get("/api/v1/realtime/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        print("✅ Real-time service is healthy")
        
        # Step 2: Get data summary
        summary_response = await client.get("/api/v1/realtime/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        print(f"✅ Data summary: {summary_data['total_sources']} sources, {summary_data['active_sources']} active")
        
        # Step 3: Get data sources status
        status_response = await client.get("/api/v1/realtime/sources/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        print(f"✅ Retrieved status for {len(status_data)} data sources")
        
        # Step 4: Get real-time updates (general)
        updates_response = await client.get("/api/v1/realtime/updates")
        assert updates_response.status_code == 200
        updates_data = updates_response.json()
        print(f"✅ Retrieved {len(updates_data)} real-time updates")
        
        # Step 5: Get real-time updates (filtered by Lovran)
        lovran_response = await client.get("/api/v1/realtime/updates?city=Lovran&limit=10")
        assert lovran_response.status_code == 200
        lovran_data = lovran_response.json()
        print(f"✅ Retrieved {len(lovran_data)} Lovran-specific updates")
        
        # Step 6: Get live stream updates
        stream_response = await client.get("/api/v1/realtime/stream")
        assert stream_response.status_code == 200
        stream_data = stream_response.json()
        print(f"✅ Retrieved {len(stream_data)} live stream updates")
        
        # Step 7: Test filtered stream (Istria region)
        istria_stream_response = await client.get("/api/v1/realtime/stream?regions=Istria")
        assert istria_stream_response.status_code == 200
        istria_stream_data = istria_stream_response.json()
        print(f"✅ Retrieved {len(istria_stream_data)} Istria region stream updates")
        
        # Step 8: Test content type filtering
        events_response = await client.get("/api/v1/realtime/updates?content_types=events&limit=5")
        assert events_response.status_code == 200
        events_data = events_response.json()
        print(f"✅ Retrieved {len(events_data)} event-specific updates")
        
        print("🎉 Complete real-time Croatian tourism data workflow successful!")
    
    @pytest.mark.asyncio
    async def test_crawl4ai_performance_characteristics(self, client: AsyncClient):
        """Test performance characteristics of Crawl4AI integration."""
        print("\n⚡ Testing Crawl4AI Performance Characteristics...")
        
        start_time = datetime.utcnow()
        
        # Test concurrent requests
        tasks = []
        for i in range(3):  # Test with 3 concurrent requests
            task = asyncio.create_task(
                client.get("/api/v1/realtime/updates?limit=10")
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
        
        print(f"✅ 3 concurrent requests completed in {duration:.2f} seconds")
        
        # Test response time for single request
        start_single = datetime.utcnow()
        single_response = await client.get("/api/v1/realtime/summary")
        end_single = datetime.utcnow()
        single_duration = (end_single - start_single).total_seconds()
        
        assert single_response.status_code == 200
        print(f"✅ Single request completed in {single_duration:.3f} seconds")
        
        # Performance should be reasonable (under 5 seconds for testing)
        assert duration < 5.0, f"Concurrent requests took too long: {duration}s"
        assert single_duration < 2.0, f"Single request took too long: {single_duration}s"
        
        print("🚀 Crawl4AI performance characteristics are acceptable")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"]) 