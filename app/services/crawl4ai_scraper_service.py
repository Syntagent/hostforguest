"""
Enhanced content scraper service using Crawl4AI for real-time tourism data.

Provides advanced web scraping capabilities for Croatian tourism websites
with real-time data feeds and structured extraction.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import uuid

logger = logging.getLogger(__name__)

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai import JsonCssExtractionStrategy, RegexExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    # Fallback mock classes if Crawl4AI is not installed
    logger.warning("Crawl4AI not installed. Using mock implementation.")
    
    class MockAsyncWebCrawler:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def arun(self, *args, **kwargs):
            return type('MockResult', (), {
                'success': False,
                'cleaned_html': '',
                'extracted_content': '',
                'error_message': 'Crawl4AI not installed. Please install: pip install crawl4ai'
            })()
    
    AsyncWebCrawler = MockAsyncWebCrawler
    BrowserConfig = dict
    CrawlerRunConfig = dict
    CacheMode = type('CacheMode', (), {'ENABLED': 'enabled', 'DISABLED': 'disabled'})
    JsonCssExtractionStrategy = dict
    RegexExtractionStrategy = dict
    CRAWL4AI_AVAILABLE = False
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func

from app.models.content_source import (
    ContentSource,
    ContentUpdate,
    HostNotification,
    SourceStatus,
    ContentType,
    ContentSourceCreate,
    ContentUpdateCreate,
    HostNotificationCreate,
    QUALITY_KEYWORDS,
    CROATIAN_TOURISM_SOURCES
)
from app.models.attraction import Attraction
from app.models.host import Host
from app.services.ai_service import AIService
from app.services.content_scraper_service import ContentScraperService


class Crawl4AIScraperService(ContentScraperService):
    """
    Enhanced content scraper service using Crawl4AI for advanced web scraping.
    
    Provides real-time data extraction from Croatian tourism websites with:
    - Advanced CSS and regex extraction strategies
    - JavaScript execution for dynamic content
    - Robust error handling and fallback strategies
    - Real-time streaming capabilities
    """
    
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        """
        Initialize the Crawl4AI scraper service.
        
        Args:
            db: Database session
            ai_service: AI service for content analysis
        """
        super().__init__(db, ai_service)
        self.crawler = None
        if CRAWL4AI_AVAILABLE:
            self.browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                verbose=False,
                use_managed_browser=True,
                user_agent="HostForGuest/1.0 Croatian Tourism Monitor"
            )
        else:
            self.browser_config = {}
    
    async def __aenter__(self):
        """Async context manager entry with Crawl4AI initialization."""
        await super().__aenter__()
        if CRAWL4AI_AVAILABLE:
            self.crawler = AsyncWebCrawler(config=self.browser_config)
            await self.crawler.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)
    
    # Enhanced Scraping Operations
    async def scrape_source_advanced(self, source: ContentSource) -> List[ContentUpdate]:
        """
        Advanced scraping using Crawl4AI with multiple extraction strategies.
        
        Args:
            source: Content source to scrape
            
        Returns:
            List[ContentUpdate]: Content updates found
        """
        updates = []
        
        try:
            logger.info(f"Starting advanced Crawl4AI scrape of {source.name} ({source.url})")
            
            # Update scraping statistics
            source.total_scrapes += 1
            source.last_scraped = datetime.utcnow()
            
            # Create extraction strategies based on content types
            strategies = self._create_extraction_strategies(source)
            
            # Try each strategy with fallback support
            for strategy_name, strategy in strategies.items():
                try:
                    logger.debug(f"Trying {strategy_name} strategy for {source.name}")
                    
                    # Check if Crawl4AI is available
                    if not CRAWL4AI_AVAILABLE or not self.crawler:
                        logger.warning(f"Crawl4AI not available, skipping scrape for {source.name}")
                        continue
                    
                    # Configure crawler for this strategy
                    if CRAWL4AI_AVAILABLE:
                        config = CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS,
                            extraction_strategy=strategy,
                            word_count_threshold=10,
                            remove_overlay_elements=True,
                            wait_for="css:body",  # Wait for page load
                            timeout=source.timeout_seconds,
                            js_code=self._get_dynamic_content_js(source),
                            delay_before_return=2  # Allow dynamic content to load
                        )
                    else:
                        config = {}
                    
                    # Apply rate limiting
                    if source.rate_limit_delay > 0:
                        await asyncio.sleep(source.rate_limit_delay)
                    
                    # Perform the crawl
                    if CRAWL4AI_AVAILABLE:
                        result = await self.crawler.arun(url=source.url, config=config)
                    else:
                        result = type('MockResult', (), {
                            'success': False,
                            'extracted_content': '',
                            'error_message': 'Crawl4AI not available'
                        })()
                    
                    if result.success and result.extracted_content:
                        # Parse extracted content
                        content_items = self._parse_extracted_content(result.extracted_content, strategy_name)
                        
                        # Process each content item
                        for item in content_items:
                            update = await self._create_content_update_advanced(source, item, strategy_name)
                            if update:
                                updates.append(update)
                        
                        logger.info(f"Successfully extracted {len(content_items)} items using {strategy_name}")
                        break  # Success with this strategy, no need to try others
                        
                    else:
                        logger.warning(f"{strategy_name} strategy failed for {source.name}: {result.error_message}")
                        continue
                
                except Exception as e:
                    logger.error(f"Error with {strategy_name} strategy for {source.name}: {e}")
                    continue
            
            # Update source statistics
            if updates:
                source.successful_scrapes += 1
                source.content_updates_found += len(updates)
                source.consecutive_failures = 0
                logger.info(f"Successfully scraped {len(updates)} updates from {source.name}")
            else:
                logger.info(f"No new content found at {source.name}")
            
            # Schedule next scrape
            source.next_scrape = self._calculate_next_scrape(source.scraping_frequency)
            
        except Exception as e:
            # Handle scraping errors
            source.failed_scrapes += 1
            source.consecutive_failures += 1
            source.last_error = str(e)
            source.last_error_at = datetime.utcnow()
            
            logger.error(f"Error scraping {source.name}: {e}")
            
            # Disable source if too many consecutive failures
            if source.consecutive_failures >= 5:
                source.status = SourceStatus.ERROR
                logger.warning(f"Disabled source {source.name} due to consecutive failures")
        
        # Save source updates
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error saving source updates: {e}")
            await self.db.rollback()
        
        return updates
    
    def _create_extraction_strategies(self, source: ContentSource) -> Dict[str, Any]:
        """
        Create multiple extraction strategies for robust data extraction.
        
        Args:
            source: Content source configuration
            
        Returns:
            Dict[str, Any]: Named extraction strategies
        """
        strategies = {}
        
        # Strategy 1: CSS Schema-based extraction (primary)
        if source.scraping_selectors and CRAWL4AI_AVAILABLE:
            css_schema = self._build_css_schema(source)
            strategies["css_schema"] = JsonCssExtractionStrategy(css_schema, verbose=True)
        
        # Strategy 2: Regex-based extraction (fallback)
        if CRAWL4AI_AVAILABLE:
            strategies["regex_fallback"] = RegexExtractionStrategy(
                pattern=RegexExtractionStrategy.Email | RegexExtractionStrategy.PhoneUS
            )
        
        # Strategy 3: Croatian tourism specific schema
        if CRAWL4AI_AVAILABLE:
            croatian_schema = self._build_croatian_tourism_schema(source)
            strategies["croatian_tourism"] = JsonCssExtractionStrategy(croatian_schema, verbose=True)
        
        return strategies
    
    def _build_css_schema(self, source: ContentSource) -> Dict[str, Any]:
        """
        Build CSS extraction schema from source configuration.
        
        Args:
            source: Content source with selectors
            
        Returns:
            Dict[str, Any]: CSS extraction schema
        """
        selectors = source.scraping_selectors
        content_types = source.content_types
        
        # Base schema structure
        schema = {
            "name": f"{source.name} Content",
            "baseSelector": "article, .content-item, .news-item, .event-item, .attraction-item",
            "fields": []
        }
        
        # Add standard fields
        schema["fields"].extend([
            {
                "name": "title",
                "selector": selectors.get("title", "h1, h2, h3, .title, .naslov"),
                "type": "text"
            },
            {
                "name": "content",
                "selector": selectors.get("content", ".content, .description, .sadrzaj, p"),
                "type": "text"
            },
            {
                "name": "date",
                "selector": selectors.get("date", ".date, .datum, time, .published"),
                "type": "text"
            },
            {
                "name": "url",
                "selector": "a",
                "type": "attribute",
                "attribute": "href"
            }
        ])
        
        # Add content-type specific fields
        for content_type in content_types:
            if content_type == ContentType.EVENTS:
                schema["fields"].extend([
                    {
                        "name": "event_date",
                        "selector": ".event-date, .datum-dogadaja, .when",
                        "type": "text"
                    },
                    {
                        "name": "location",
                        "selector": ".location, .mjesto, .where",
                        "type": "text"
                    }
                ])
            elif content_type == ContentType.OPENING_HOURS:
                schema["fields"].append({
                    "name": "opening_hours",
                    "selector": ".opening-hours, .radno-vrijeme, .working-hours",
                    "type": "text"
                })
            elif content_type == ContentType.PRICES:
                schema["fields"].extend([
                    {
                        "name": "price",
                        "selector": ".price, .cijena, .cost",
                        "type": "text"
                    },
                    {
                        "name": "currency",
                        "selector": ".currency, .valuta",
                        "type": "text"
                    }
                ])
        
        return schema
    
    def _build_croatian_tourism_schema(self, source: ContentSource) -> Dict[str, Any]:
        """
        Build Croatian tourism-specific extraction schema.
        
        Args:
            source: Content source
            
        Returns:
            Dict[str, Any]: Croatian tourism schema
        """
        return {
            "name": "Croatian Tourism Data",
            "baseSelector": ".turisticka-informacija, .tourism-info, .attraction, .atrakcija, .event, .dogadaj",
            "fields": [
                {
                    "name": "naziv",
                    "selector": "h1, h2, h3, .naziv, .title, .naslov",
                    "type": "text"
                },
                {
                    "name": "opis",
                    "selector": ".opis, .description, .sadrzaj, .content, p",
                    "type": "text"
                },
                {
                    "name": "lokacija",
                    "selector": ".lokacija, .location, .mjesto, .address",
                    "type": "text"
                },
                {
                    "name": "radno_vrijeme",
                    "selector": ".radno-vrijeme, .opening-hours, .radni-sati",
                    "type": "text"
                },
                {
                    "name": "cijena",
                    "selector": ".cijena, .price, .kosta, .ulaznica",
                    "type": "text"
                },
                {
                    "name": "kontakt",
                    "selector": ".kontakt, .contact, .telefon, .email",
                    "type": "text"
                },
                {
                    "name": "sezona",
                    "selector": ".sezona, .season, .kada",
                    "type": "text"
                },
                {
                    "name": "slika",
                    "selector": "img",
                    "type": "attribute",
                    "attribute": "src"
                },
                {
                    "name": "link",
                    "selector": "a",
                    "type": "attribute",
                    "attribute": "href"
                }
            ]
        }
    
    def _get_dynamic_content_js(self, source: ContentSource) -> str:
        """
        Get JavaScript code for loading dynamic content.
        
        Args:
            source: Content source
            
        Returns:
            str: JavaScript code
        """
        # Common patterns for Croatian tourism sites
        js_patterns = [
            "window.scrollTo(0, document.body.scrollHeight);",  # Load more content
            "document.querySelectorAll('.load-more, .ucitaj-vise').forEach(btn => btn.click());",  # Click load more
            "setTimeout(() => {}, 2000);",  # Wait for dynamic content
        ]
        
        # Combine patterns
        return "\n".join(js_patterns)
    
    def _parse_extracted_content(self, extracted_content: str, strategy_name: str) -> List[Dict[str, Any]]:
        """
        Parse extracted content based on strategy used.
        
        Args:
            extracted_content: Raw extracted content
            strategy_name: Name of extraction strategy used
            
        Returns:
            List[Dict[str, Any]]: Parsed content items
        """
        try:
            if strategy_name in ["css_schema", "croatian_tourism"]:
                # JSON-based extraction
                data = json.loads(extracted_content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
                else:
                    return []
            else:
                # Regex or other extraction - convert to standard format
                return [{"content": extracted_content, "extraction_method": strategy_name}]
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from {strategy_name} strategy")
            return [{"content": extracted_content, "extraction_method": strategy_name}]
    
    async def _create_content_update_advanced(self, source: ContentSource, item: Dict[str, Any], strategy_name: str) -> Optional[ContentUpdate]:
        """
        Create content update with advanced processing.
        
        Args:
            source: Content source
            item: Extracted content item
            strategy_name: Extraction strategy used
            
        Returns:
            ContentUpdate: Created update or None
        """
        try:
            # Normalize item data based on extraction strategy
            normalized_item = self._normalize_content_item(item, strategy_name)
            
            # Use parent method with normalized data
            return await self._create_content_update(source, normalized_item)
            
        except Exception as e:
            logger.error(f"Error creating advanced content update: {e}")
            return None
    
    def _normalize_content_item(self, item: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
        """
        Normalize content item to standard format.
        
        Args:
            item: Raw extracted item
            strategy_name: Extraction strategy used
            
        Returns:
            Dict[str, Any]: Normalized content item
        """
        normalized = {
            "content_type": "general",
            "title": "",
            "content": "",
            "url": None,
            "publication_date": None,
            "language": "hr",
            "extraction_strategy": strategy_name
        }
        
        # Map fields based on strategy and available data
        if strategy_name == "croatian_tourism":
            normalized.update({
                "title": item.get("naziv", item.get("title", "")),
                "content": item.get("opis", item.get("content", "")),
                "url": item.get("link", item.get("url")),
                "location": item.get("lokacija", ""),
                "opening_hours": item.get("radno_vrijeme", ""),
                "price": item.get("cijena", ""),
                "contact": item.get("kontakt", ""),
                "season": item.get("sezona", ""),
                "image_url": item.get("slika", "")
            })
        else:
            # Standard mapping
            normalized.update({
                "title": item.get("title", item.get("naziv", "")),
                "content": item.get("content", item.get("opis", "")),
                "url": item.get("url", item.get("link")),
                "publication_date": self._parse_date(item.get("date", item.get("datum", "")))
            })
        
        # Detect content type based on content
        normalized["content_type"] = self._detect_content_type(normalized)
        
        return normalized
    
    def _detect_content_type(self, item: Dict[str, Any]) -> str:
        """
        Detect content type based on content analysis.
        
        Args:
            item: Content item
            
        Returns:
            str: Detected content type
        """
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        
        # Croatian and English keywords for content type detection
        type_keywords = {
            ContentType.EVENTS: [
                "događaj", "event", "festival", "manifestacija", "koncert", "concert",
                "izložba", "exhibition", "predstava", "performance", "proslava", "celebration"
            ],
            ContentType.ATTRACTIONS: [
                "atrakcija", "attraction", "muzej", "museum", "crkva", "church",
                "park", "plaža", "beach", "spomenik", "monument", "tvrđava", "fortress"
            ],
            ContentType.OPENING_HOURS: [
                "radno vrijeme", "opening hours", "otvoreno", "open", "zatvoreno", "closed",
                "raspored", "schedule", "radni sati", "working hours"
            ],
            ContentType.PRICES: [
                "cijena", "price", "kosta", "cost", "ulaznica", "ticket",
                "besplatno", "free", "popust", "discount", "tarifa", "rate"
            ]
        }
        
        # Find best match
        for content_type, keywords in type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return content_type
        
        return ContentType.NEWS  # Default fallback
    
    # Real-time Data Feed Methods
    async def get_real_time_updates(self, city: Optional[str] = None, content_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get real-time updates for immediate consumption.
        
        Args:
            city: Filter by city
            content_types: Filter by content types
            
        Returns:
            List[Dict[str, Any]]: Real-time updates
        """
        try:
            from app.services.events_feed_service import EventsFeedService

            feed = EventsFeedService(self.db)
            updates = await feed.get_updates(
                city=city,
                content_types=content_types,
                hours=168,
                limit=50,
            )
            logger.info(f"Retrieved {len(updates)} real-time updates")
            return updates
        except Exception as e:
            logger.error(f"Error getting real-time updates: {e}")
            return []
    
    async def stream_live_updates(self, sources: List[ContentSource]) -> List[Dict[str, Any]]:
        """
        Stream live updates from multiple sources concurrently.
        
        Args:
            sources: List of content sources to monitor
            
        Returns:
            List[Dict[str, Any]]: Streamed updates
        """
        try:
            logger.info(f"Starting live update stream from {len(sources)} sources")
            
            # Create tasks for concurrent scraping
            tasks = []
            for source in sources:
                task = asyncio.create_task(self.scrape_source_advanced(source))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect all updates
            all_updates = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error streaming from source {sources[i].name}: {result}")
                else:
                    all_updates.extend(result)
            
            # Convert to stream format
            stream_data = []
            for update in all_updates:
                stream_data.append({
                    "update_id": str(update.id),
                    "source_name": update.source.name,
                    "content_type": update.content_type,
                    "title": update.title,
                    "summary": update.content[:200] + "..." if len(update.content) > 200 else update.content,
                    "url": update.url,
                    "timestamp": update.created_at.isoformat(),
                    "relevance_score": update.relevance_score,
                    "cities": update.relevant_cities,
                    "regions": update.relevant_regions
                })
            
            logger.info(f"Streamed {len(stream_data)} live updates")
            return stream_data
            
        except Exception as e:
            logger.error(f"Error streaming live updates: {e}")
            return [] 