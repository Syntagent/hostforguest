"""
Content source models for automated tourism content updates.

Tracks external content sources, scraping schedules, and content change monitoring
for Croatian tourism boards and local information websites.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field

from app.db.postgresql.connection import Base


class SourceType(str, Enum):
    """Types of content sources."""
    TOURISM_BOARD = "tourism_board"      # Official tourism boards
    LOCAL_OFFICE = "local_office"        # Local tourism offices
    EVENT_CALENDAR = "event_calendar"    # Event listing sites
    NEWS_SITE = "news_site"              # Local news and information
    GOVERNMENT = "government"            # Government tourism sites
    CULTURAL_SITE = "cultural_site"      # Museums, cultural institutions


class SourceStatus(str, Enum):
    """Status of a content source."""
    ACTIVE = "active"           # Actively monitored
    INACTIVE = "inactive"       # Temporarily disabled
    ERROR = "error"            # Experiencing issues
    BLOCKED = "blocked"        # Blocked by source
    DEPRECATED = "deprecated"   # No longer relevant


class ContentType(str, Enum):
    """Types of content being monitored."""
    ATTRACTIONS = "attractions"
    EVENTS = "events"
    OPENING_HOURS = "opening_hours"
    PRICES = "prices"
    NEWS = "news"
    WEATHER_ALERTS = "weather_alerts"
    SEASONAL_INFO = "seasonal_info"


class ContentSource(Base):
    """
    External content sources for automated updates.
    
    Tracks Croatian tourism websites and their content for
    automated scraping and integration with host knowledge.
    """
    
    __tablename__ = "content_sources"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source Information
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    status = Column(String(20), default=SourceStatus.ACTIVE)
    
    # Geographic Focus
    country = Column(String(50), default="Croatia")
    region = Column(String(100), nullable=True)  # Istria, Kvarner, etc.
    city = Column(String(100), nullable=True)    # Lovran, Opatija, etc.
    
    # Content Configuration
    content_types = Column(JSON, default=[])  # What content to monitor
    scraping_selectors = Column(JSON, default={})  # CSS/XPath selectors
    content_patterns = Column(JSON, default={})    # Regex patterns for extraction
    
    # Language Support
    languages = Column(JSON, default=["hr", "en"])  # Supported languages
    primary_language = Column(String(10), default="hr")
    
    # Scraping Configuration
    scraping_frequency = Column(String(50), default="weekly")  # daily, weekly, monthly
    last_scraped = Column(DateTime, nullable=True)
    next_scrape = Column(DateTime, nullable=True)
    scraping_enabled = Column(Boolean, default=True)
    
    # Technical Configuration
    headers = Column(JSON, default={})  # Custom headers for requests
    rate_limit_delay = Column(Integer, default=1)  # Seconds between requests
    timeout_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    
    # Content Validation
    content_filters = Column(JSON, default=[])  # Keywords to include/exclude
    quality_threshold = Column(Float, default=0.7)  # AI quality score threshold
    requires_human_review = Column(Boolean, default=False)
    
    # Performance Tracking
    total_scrapes = Column(Integer, default=0)
    successful_scrapes = Column(Integer, default=0)
    failed_scrapes = Column(Integer, default=0)
    content_updates_found = Column(Integer, default=0)
    
    # Error Tracking
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="system")


class ContentUpdate(Base):
    """
    Tracks content updates found from external sources.
    
    Records changes detected from tourism websites and their
    integration status with host-contributed content.
    """
    
    __tablename__ = "content_updates"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source Reference
    source_id = Column(UUID(as_uuid=True), ForeignKey("content_sources.id"), nullable=False)
    
    # Content Information
    content_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)  # Direct URL to the content
    
    # Content Metadata
    language = Column(String(10), default="hr")
    publication_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)  # When change takes effect
    expiry_date = Column(DateTime, nullable=True)     # When content expires
    
    # Geographic Relevance
    relevant_cities = Column(JSON, default=[])
    relevant_regions = Column(JSON, default=[])
    relevant_attractions = Column(JSON, default=[])  # UUIDs of related attractions
    
    # Content Analysis
    keywords = Column(JSON, default=[])
    sentiment_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    
    # Processing Status
    status = Column(String(50), default="pending")  # pending, reviewed, integrated, rejected
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(100), nullable=True)
    
    # Host Integration
    notified_hosts = Column(JSON, default=[])  # Host UUIDs notified about this update
    integrated_attractions = Column(JSON, default=[])  # Attractions updated with this content
    host_feedback = Column(JSON, default={})  # Host responses to the update
    
    # Change Detection
    content_hash = Column(String(64), nullable=True)  # Hash for duplicate detection
    previous_version_id = Column(UUID(as_uuid=True), nullable=True)  # Link to previous version
    change_type = Column(String(50), nullable=True)  # new, updated, deleted
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HostNotification(Base):
    """
    Notifications sent to hosts about relevant content updates.
    """
    
    __tablename__ = "host_notifications"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    content_update_id = Column(UUID(as_uuid=True), ForeignKey("content_updates.id"), nullable=False)
    
    # Notification Details
    notification_type = Column(String(50), default="content_update")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Delivery Status
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Host Response
    host_response = Column(String(50), nullable=True)  # interested, not_relevant, integrated
    response_at = Column(DateTime, nullable=True)
    response_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# Pydantic models for API requests/responses
class ContentSourceBase(SQLModel):
    """Base content source model."""
    name: str = Field(max_length=200)
    url: str = Field(max_length=500)
    source_type: str = Field(max_length=50)
    region: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    content_types: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["hr", "en"])
    primary_language: str = Field(default="hr", max_length=10)
    scraping_frequency: str = Field(default="weekly", max_length=50)
    scraping_enabled: bool = Field(default=True)


class ContentSourceCreate(ContentSourceBase):
    """Content source creation model."""
    scraping_selectors: Dict[str, str] = Field(default_factory=dict)
    content_patterns: Dict[str, str] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit_delay: int = Field(default=1, ge=1, le=60)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=1, le=10)
    content_filters: List[str] = Field(default_factory=list)
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    requires_human_review: bool = Field(default=False)


class ContentSourceResponse(ContentSourceBase):
    """Content source response model."""
    id: uuid.UUID
    status: str
    last_scraped: Optional[datetime] = None
    next_scrape: Optional[datetime] = None
    total_scrapes: int
    successful_scrapes: int
    failed_scrapes: int
    content_updates_found: int
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentUpdateCreate(SQLModel):
    """Content update creation model."""
    source_id: uuid.UUID
    content_type: str = Field(max_length=50)
    title: str = Field(max_length=500)
    content: str
    url: Optional[str] = Field(default=None, max_length=500)
    language: str = Field(default="hr", max_length=10)
    publication_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    relevant_cities: List[str] = Field(default_factory=list)
    relevant_regions: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ContentUpdateResponse(ContentUpdateCreate):
    """Content update response model."""
    id: uuid.UUID
    status: str
    quality_score: Optional[float] = None
    relevance_score: Optional[float] = None
    processed_at: Optional[datetime] = None
    notified_hosts: List[str] = Field(default_factory=list)
    scraped_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class HostNotificationCreate(SQLModel):
    """Host notification creation model."""
    host_id: uuid.UUID
    content_update_id: uuid.UUID
    title: str = Field(max_length=200)
    message: str
    priority: str = Field(default="normal", max_length=20)


class HostNotificationResponse(HostNotificationCreate):
    """Host notification response model."""
    id: uuid.UUID
    notification_type: str
    sent: bool
    sent_at: Optional[datetime] = None
    read: bool
    read_at: Optional[datetime] = None
    host_response: Optional[str] = None
    response_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Croatian Tourism Source Configurations
CROATIAN_TOURISM_SOURCES = [
    {
        "name": "Croatia Tourism Board",
        "url": "https://croatia.hr",
        "source_type": SourceType.TOURISM_BOARD,
        "region": None,
        "city": None,
        "content_types": [ContentType.ATTRACTIONS, ContentType.EVENTS, ContentType.NEWS],
        "scraping_selectors": {
            "events": ".event-item, .news-item",
            "attractions": ".destination-item, .attraction-card",
            "title": "h2, h3, .title",
            "content": ".content, .description, p",
            "date": ".date, time"
        },
        "languages": ["hr", "en", "de"],
        "primary_language": "hr",
        "scraping_frequency": "weekly"
    },
    {
        "name": "Istria Tourism",
        "url": "https://www.istra.hr",
        "source_type": SourceType.TOURISM_BOARD,
        "region": "Istria",
        "city": None,
        "content_types": [ContentType.ATTRACTIONS, ContentType.EVENTS, ContentType.SEASONAL_INFO],
        "scraping_selectors": {
            "events": ".event, .manifestacija",
            "attractions": ".atrakcija, .destinacija",
            "opening_hours": ".radno-vrijeme, .opening-hours"
        },
        "languages": ["hr", "en", "de", "it"],
        "primary_language": "hr",
        "scraping_frequency": "weekly"
    },
    {
        "name": "Kvarner Tourism",
        "url": "https://www.kvarner.hr",
        "source_type": SourceType.TOURISM_BOARD,
        "region": "Kvarner",
        "city": None,
        "content_types": [ContentType.ATTRACTIONS, ContentType.EVENTS, ContentType.WEATHER_ALERTS],
        "scraping_selectors": {
            "events": ".event-list-item, .calendar-event",
            "attractions": ".poi-item, .attraction"
        },
        "languages": ["hr", "en", "de"],
        "primary_language": "hr",
        "scraping_frequency": "weekly"
    },
    {
        "name": "Lovran Tourism Office",
        "url": "https://tz-lovran.hr",
        "source_type": SourceType.LOCAL_OFFICE,
        "region": "Kvarner",
        "city": "Lovran",
        "content_types": [ContentType.EVENTS, ContentType.OPENING_HOURS, ContentType.SEASONAL_INFO],
        "scraping_selectors": {
            "events": ".dogadanja, .events",
            "news": ".novosti, .news",
            "seasonal": ".sezonski, .seasonal"
        },
        "languages": ["hr", "en"],
        "primary_language": "hr",
        "scraping_frequency": "weekly"
    },
    {
        "name": "Opatija Tourism",
        "url": "https://www.opatija-tourism.hr",
        "source_type": SourceType.LOCAL_OFFICE,
        "region": "Kvarner",
        "city": "Opatija",
        "content_types": [ContentType.ATTRACTIONS, ContentType.EVENTS, ContentType.OPENING_HOURS],
        "scraping_selectors": {
            "attractions": ".attraction, .znamenitost",
            "events": ".event, .dogadaj",
            "hours": ".radno-vrijeme"
        },
        "languages": ["hr", "en", "de"],
        "primary_language": "hr",
        "scraping_frequency": "weekly"
    }
]

# Content quality keywords for Croatian tourism
QUALITY_KEYWORDS = {
    "high_relevance": [
        "otvoreno", "zatvoreno", "radno vrijeme", "cijena", "ulaznica",
        "festival", "manifestacija", "događaj", "sezona", "turistička sezona",
        "open", "closed", "opening hours", "price", "ticket", "festival", "event", "season"
    ],
    "medium_relevance": [
        "informacija", "novost", "obavijest", "promjena", "ažuriranje",
        "information", "news", "notice", "change", "update"
    ],
    "exclude": [
        "oglasi", "reklama", "spam", "prodaja", "kupi",
        "ads", "advertisement", "spam", "sale", "buy"
    ]
} 