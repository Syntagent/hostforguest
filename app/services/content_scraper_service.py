"""
Content scraper service for automated tourism content updates.

Scrapes Croatian tourism websites, analyzes content, and notifies hosts of
relevant updates.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import uuid

import aiohttp
from bs4 import BeautifulSoup
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
    QUALITY_KEYWORDS
)
from app.models.attraction import Attraction
from app.models.host import Host
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class ContentScraperService:
    """
    Service for automated content scraping and host notification.

    Keeps host knowledge current with official Croatian tourism updates.
    """

    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        """
        Initialize the content scraper service.

        Args:
            db: Database session
            ai_service: AI service for content analysis
        """
        self.db = db
        self.ai_service = ai_service
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'TouristGuideLocal/1.0 Croatian Tourism Content Monitor'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    # Content Source Management
    async def create_content_source(self, source_data: ContentSourceCreate) -> Optional[ContentSource]:
        """
        Create a new content source for monitoring.

        Args:
            source_data: Content source creation data

        Returns:
            ContentSource: Created source or None
        """
        try:
            # Calculate next scrape time
            next_scrape = self._calculate_next_scrape(source_data.scraping_frequency)

            source = ContentSource(
                name=source_data.name,
                url=source_data.url,
                source_type=source_data.source_type,
                region=source_data.region,
                city=source_data.city,
                content_types=source_data.content_types,
                scraping_selectors=source_data.scraping_selectors,
                content_patterns=source_data.content_patterns,
                languages=source_data.languages,
                primary_language=source_data.primary_language,
                scraping_frequency=source_data.scraping_frequency,
                next_scrape=next_scrape,
                headers=source_data.headers,
                rate_limit_delay=source_data.rate_limit_delay,
                timeout_seconds=source_data.timeout_seconds,
                max_retries=source_data.max_retries,
                content_filters=source_data.content_filters,
                quality_threshold=source_data.quality_threshold,
                requires_human_review=source_data.requires_human_review,
                scraping_enabled=source_data.scraping_enabled
            )

            self.db.add(source)
            await self.db.commit()
            await self.db.refresh(source)

            logger.info(f"Content source created: {source.name}")
            return source

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating content source: {e}")
            return None

    async def get_sources_ready_for_scraping(self) -> List[ContentSource]:
        """
        Get content sources that are ready for scraping.

        Returns:
            List[ContentSource]: Sources ready for scraping
        """
        try:
            now = datetime.utcnow()
            stmt = select(ContentSource).where(
                and_(
                    ContentSource.scraping_enabled == True,
                    ContentSource.status == SourceStatus.ACTIVE,
                    or_(
                        ContentSource.next_scrape <= now,
                        ContentSource.next_scrape.is_(None)
                    )
                )
            )

            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting sources ready for scraping: {e}")
            return []

    # Web Scraping Operations
    async def scrape_source(self, source: ContentSource) -> List[ContentUpdate]:
        """
        Scrape content from a single source.

        Args:
            source: Content source to scrape

        Returns:
            List[ContentUpdate]: Content updates found
        """
        updates = []

        try:
            logger.info(f"Starting scrape of {source.name} ({source.url})")

            # Update scraping statistics
            source.total_scrapes += 1
            source.last_scraped = datetime.utcnow()

            # Perform the scraping
            content_items = await self._scrape_website(source)

            # Process each content item
            for item in content_items:
                try:
                    # Create content update
                    update = await self._create_content_update(source, item)
                    if update:
                        updates.append(update)

                except Exception as e:
                    logger.error(f"Error processing content item from {source.name}: {e}")

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

    async def _scrape_website(self, source: ContentSource) -> List[Dict[str, Any]]:
        """
        Scrape content from a website using configured selectors.

        Args:
            source: Content source with scraping configuration

        Returns:
            List[Dict]: Raw content items extracted
        """
        if not self.session:
            raise RuntimeError("ContentScraperService must be used as async context manager")

        content_items = []

        try:
            # Apply rate limiting
            if source.rate_limit_delay > 0:
                await asyncio.sleep(source.rate_limit_delay)

            # Prepare headers
            headers = source.headers or {}

            # Fetch the webpage
            async with self.session.get(
                source.url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=source.timeout_seconds)
            ) as response:

                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Extract content using configured selectors
                    for content_type in source.content_types:
                        items = self._extract_content_by_type(soup, source, content_type)
                        content_items.extend(items)

                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            raise Exception("Request timeout")
        except Exception as e:
            raise Exception(f"Scraping error: {e}")

        return content_items

    def _extract_content_by_type(self, soup: BeautifulSoup, source: ContentSource,
                                content_type: str) -> List[Dict[str, Any]]:
        """
        Extract specific content type from webpage.

        Args:
            soup: BeautifulSoup parsed HTML
            source: Content source configuration
            content_type: Type of content to extract

        Returns:
            List[Dict]: Extracted content items
        """
        items = []
        selectors = source.scraping_selectors

        try:
            # Get selector for this content type
            content_selector = selectors.get(content_type, '')
            if not content_selector:
                return items

            # Find content elements
            elements = soup.select(content_selector)

            for element in elements:
                try:
                    # Extract basic information
                    title = self._extract_text(element, selectors.get('title', 'h1, h2, h3, .title'))
                    content = self._extract_text(element, selectors.get('content', 'p, .content, .description'))
                    date_str = self._extract_text(element, selectors.get('date', '.date, time'))

                    # Skip if no meaningful content
                    if not title and not content:
                        continue

                    # Parse date if available
                    publication_date = self._parse_date(date_str) if date_str else None

                    # Extract URL if available
                    url = None
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        url = self._resolve_url(link_elem['href'], source.url)

                    # Create content item
                    item = {
                        'content_type': content_type,
                        'title': title or 'Untitled',
                        'content': content or '',
                        'url': url,
                        'publication_date': publication_date,
                        'language': source.primary_language,
                        'raw_element': str(element)  # Keep raw HTML for further analysis
                    }

                    # Apply content filters
                    if self._passes_content_filters(item, source.content_filters):
                        items.append(item)

                except Exception as e:
                    logger.warning(f"Error extracting item from {source.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting {content_type} from {source.name}: {e}")

        return items

    def _extract_text(self, element, selector: str) -> str:
        """Extract and clean text from element using selector."""
        try:
            target = element.select_one(selector) if selector else element
            if target:
                text = target.get_text(strip=True)
                return re.sub(r'\s+', ' ', text)  # Normalize whitespace
            return ""
        except:
            return ""

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        if not date_str:
            return None

        # Common Croatian date formats
        date_patterns = [
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # DD.MM.YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',   # YYYY-MM-DD
            r'(\d{1,2})/(\d{1,2})/(\d{4})',   # DD/MM/YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if '.' in date_str:  # DD.MM.YYYY format
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    elif '-' in date_str:  # YYYY-MM-DD format
                        year, month, day = match.groups()
                        return datetime(int(year), int(month), int(day))
                    elif '/' in date_str:  # DD/MM/YYYY format
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue

        return None

    def _resolve_url(self, href: str, base_url: str) -> str:
        """Resolve relative URL to absolute URL."""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            from urllib.parse import urljoin
            return urljoin(base_url, href)
        else:
            from urllib.parse import urljoin
            return urljoin(base_url + '/', href)

    def _passes_content_filters(self, item: Dict[str, Any], filters: List[str]) -> bool:
        """Check if content item passes quality filters."""
        if not filters:
            return True

        text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        # Check for exclude keywords
        for exclude_word in QUALITY_KEYWORDS.get('exclude', []):
            if exclude_word.lower() in text:
                return False

        # Check for include keywords (if any specified)
        include_keywords = [f for f in filters if not f.startswith('!')]
        if include_keywords:
            return any(keyword.lower() in text for keyword in include_keywords)

        return True

    # Content Analysis and Processing
    async def _create_content_update(self, source: ContentSource, item: Dict[str, Any]) -> Optional[ContentUpdate]:
        """
        Create a content update from scraped item.

        Args:
            source: Content source
            item: Scraped content item

        Returns:
            ContentUpdate: Created update or None
        """
        try:
            # Generate content hash for duplicate detection
            content_text = f"{item['title']}{item['content']}"
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()

            # Check if we've already seen this content
            existing_update = await self._find_existing_update(source.id, content_hash)
            if existing_update:
                logger.debug(f"Duplicate content detected from {source.name}")
                return None

            # Analyze content quality and relevance
            quality_score = self._calculate_quality_score(item)
            relevance_score = self._calculate_relevance_score(item, source)

            # Skip low-quality content
            if quality_score < source.quality_threshold:
                logger.debug(f"Content quality too low: {quality_score} < {source.quality_threshold}")
                return None

            # Extract keywords
            keywords = self._extract_keywords(item)

            # Determine geographic relevance
            relevant_cities, relevant_regions = self._extract_geographic_relevance(item, source)

            # Create content update
            update = ContentUpdate(
                source_id=source.id,
                content_type=item['content_type'],
                title=item['title'][:500],  # Truncate if too long
                content=item['content'],
                url=item.get('url'),
                language=item.get('language', source.primary_language),
                publication_date=item.get('publication_date'),
                relevant_cities=relevant_cities,
                relevant_regions=relevant_regions,
                keywords=keywords,
                quality_score=quality_score,
                relevance_score=relevance_score,
                content_hash=content_hash,
                status="pending"
            )

            self.db.add(update)
            await self.db.commit()
            await self.db.refresh(update)

            logger.info(f"Created content update: {update.title}")
            return update

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating content update: {e}")
            return None

    async def _find_existing_update(self, source_id: uuid.UUID, content_hash: str) -> Optional[ContentUpdate]:
        """Find existing content update by hash."""
        try:
            stmt = select(ContentUpdate).where(
                and_(
                    ContentUpdate.source_id == source_id,
                    ContentUpdate.content_hash == content_hash
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception:
            return None

    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """Calculate content quality score (0.0 - 1.0)."""
        score = 0.0
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        # Base score for having content
        if item.get('title'):
            score += 0.3
        if item.get('content') and len(item['content']) > 50:
            score += 0.3

        # Bonus for high-relevance keywords
        for keyword in QUALITY_KEYWORDS.get('high_relevance', []):
            if keyword.lower() in text:
                score += 0.1

        # Bonus for medium-relevance keywords
        for keyword in QUALITY_KEYWORDS.get('medium_relevance', []):
            if keyword.lower() in text:
                score += 0.05

        # Bonus for having a URL
        if item.get('url'):
            score += 0.1

        # Bonus for having a date
        if item.get('publication_date'):
            score += 0.1

        return min(1.0, score)

    def _calculate_relevance_score(self, item: Dict[str, Any], source: ContentSource) -> float:
        """Calculate content relevance score for the platform."""
        score = 0.5  # Base relevance
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        # Higher relevance for local content
        if source.city:
            city_keywords = [source.city.lower(), source.region.lower() if source.region else '']
            for keyword in city_keywords:
                if keyword and keyword in text:
                    score += 0.2

        # Tourism-specific keywords
        tourism_keywords = [
            'turizam', 'tourism', 'turistička', 'tourist', 'posjetitelj', 'visitor',
            'atrakcija', 'attraction', 'manifestacija', 'event', 'festival'
        ]

        for keyword in tourism_keywords:
            if keyword in text:
                score += 0.1

        return min(1.0, score)

    def _extract_keywords(self, item: Dict[str, Any]) -> List[str]:
        """Extract relevant keywords from content."""
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        keywords = []

        # Extract tourism-related keywords
        all_keywords = (
            QUALITY_KEYWORDS.get('high_relevance', []) +
            QUALITY_KEYWORDS.get('medium_relevance', [])
        )

        for keyword in all_keywords:
            if keyword.lower() in text:
                keywords.append(keyword)

        return list(set(keywords))  # Remove duplicates

    def _extract_geographic_relevance(self, item: Dict[str, Any], source: ContentSource) -> Tuple[List[str], List[str]]:
        """Extract geographic relevance from content."""
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        cities = []
        regions = []

        # Check for source's geographic area
        if source.city and source.city.lower() in text:
            cities.append(source.city)

        if source.region and source.region.lower() in text:
            regions.append(source.region)

        # Check for other Croatian locations
        croatian_cities = ['zagreb', 'split', 'rijeka', 'osijek', 'zadar', 'pula', 'lovran', 'opatija']
        croatian_regions = ['istria', 'istra', 'dalmatia', 'dalmacija', 'kvarner', 'slavonia', 'slavonija']

        for city in croatian_cities:
            if city in text:
                cities.append(city.title())

        for region in croatian_regions:
            if region in text:
                regions.append(region.title())

        return list(set(cities)), list(set(regions))

    # Host Notification System
    async def notify_relevant_hosts(self, content_update: ContentUpdate) -> List[HostNotification]:
        """
        Notify hosts about relevant content updates.

        Args:
            content_update: Content update to notify about

        Returns:
            List[HostNotification]: Created notifications
        """
        notifications = []

        try:
            # Find relevant hosts based on location and interests
            relevant_hosts = await self._find_relevant_hosts(content_update)

            for host in relevant_hosts:
                try:
                    # Create notification message
                    notification_data = self._create_notification_message(content_update, host)

                    # Create notification
                    notification = HostNotification(
                        host_id=host.id,
                        content_update_id=content_update.id,
                        title=notification_data['title'],
                        message=notification_data['message'],
                        priority=notification_data['priority'],
                        expires_at=datetime.utcnow() + timedelta(days=30)
                    )

                    self.db.add(notification)
                    notifications.append(notification)

                except Exception as e:
                    logger.error(f"Error creating notification for host {host.id}: {e}")

            # Update content update with notified hosts
            if notifications:
                content_update.notified_hosts = [str(n.host_id) for n in notifications]

            await self.db.commit()

            logger.info(f"Created {len(notifications)} notifications for content update: {content_update.title}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error notifying hosts about content update: {e}")

        return notifications

    async def _find_relevant_hosts(self, content_update: ContentUpdate) -> List[Host]:
        """Find hosts relevant to a content update."""
        try:
            stmt = select(Host)

            # Filter by geographic relevance
            if content_update.relevant_cities or content_update.relevant_regions:
                # This would need to be enhanced based on host location fields
                # For now, get all active hosts
                stmt = stmt.where(Host.is_active == True)

            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error finding relevant hosts: {e}")
            return []

    def _create_notification_message(self, content_update: ContentUpdate, host: Host) -> Dict[str, str]:
        """Create notification message for host."""
        # Determine priority based on content type and relevance
        priority = "normal"
        if content_update.content_type in [ContentType.EVENTS, ContentType.OPENING_HOURS]:
            priority = "high"
        elif content_update.relevance_score and content_update.relevance_score > 0.8:
            priority = "high"

        # Create message
        message = f"""
Novo ažuriranje sadržaja relevantno za vaše goste:

**{content_update.title}**

{content_update.content[:300]}{'...' if len(content_update.content) > 300 else ''}

Tip sadržaja: {content_update.content_type}
Izvor: {content_update.source_id}
Datum objave: {content_update.publication_date.strftime('%d.%m.%Y') if content_update.publication_date else 'Nepoznat'}

Možete pregledati i integrirati ove informacije u svoje atrakcije ili dodati vlastite komentare.
        """.strip()

        return {
            'title': f"Novo: {content_update.title[:50]}{'...' if len(content_update.title) > 50 else ''}",
            'message': message,
            'priority': priority
        }

    # Scheduling and Automation
    def _calculate_next_scrape(self, frequency: str) -> datetime:
        """Calculate next scrape time based on frequency."""
        now = datetime.utcnow()

        if frequency == "daily":
            return now + timedelta(days=1)
        elif frequency == "weekly":
            return now + timedelta(weeks=1)
        elif frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(weeks=1)  # Default to weekly

    async def run_scheduled_scraping(self) -> Dict[str, Any]:
        """
        Run scheduled scraping for all active sources.

        Returns:
            Dict: Scraping results summary
        """
        logger.info("Starting scheduled content scraping")

        results = {
            'sources_processed': 0,
            'total_updates': 0,
            'notifications_sent': 0,
            'errors': []
        }

        try:
            # Get sources ready for scraping
            sources = await self.get_sources_ready_for_scraping()
            logger.info(f"Found {len(sources)} sources ready for scraping")

            for source in sources:
                try:
                    # Scrape the source
                    updates = await self.scrape_source(source)
                    results['sources_processed'] += 1
                    results['total_updates'] += len(updates)

                    # Notify hosts about new updates
                    for update in updates:
                        notifications = await self.notify_relevant_hosts(update)
                        results['notifications_sent'] += len(notifications)

                except Exception as e:
                    error_msg = f"Error processing source {source.name}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

            logger.info(f"Scheduled scraping completed: {results}")

        except Exception as e:
            error_msg = f"Error in scheduled scraping: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results
