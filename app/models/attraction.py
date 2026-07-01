"""
Attraction models for the Croatian tourist host platform.

Enables hosts to contribute local knowledge and create comprehensive
attraction databases for their guests with host-centric content creation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field

from app.db.postgresql.connection import Base


class AttractionStatus(str, Enum):
    """Status of an attraction."""
    DRAFT = "draft"          # Host is still working on it
    PENDING = "pending"      # Submitted for review
    APPROVED = "approved"    # Approved and visible to guests
    REJECTED = "rejected"    # Rejected, needs revision
    ARCHIVED = "archived"    # No longer active


class AttractionType(str, Enum):
    """Types of attractions in Croatian tourism."""
    HISTORIC = "historic"           # Historic sites, churches, old towns
    NATURAL = "natural"            # Parks, beaches, hiking trails
    CULTURAL = "cultural"          # Museums, galleries, events
    CULINARY = "culinary"          # Restaurants, food experiences
    ACTIVITY = "activity"          # Tours, sports, adventures
    SEASONAL = "seasonal"          # Seasonal events, festivals
    ACCOMMODATION = "accommodation" # Hotels, unique stays
    SHOPPING = "shopping"          # Markets, local products
    NIGHTLIFE = "nightlife"        # Bars, clubs, entertainment
    FAMILY = "family"              # Family-friendly activities
    ROMANTIC = "romantic"          # Couples experiences
    HIDDEN_GEM = "hidden_gem"      # Local secrets


class SeasonalAvailability(str, Enum):
    """Seasonal availability of attractions."""
    YEAR_ROUND = "year_round"
    SPRING = "spring"          # March-May
    SUMMER = "summer"          # June-August
    AUTUMN = "autumn"          # September-November
    WINTER = "winter"          # December-February
    SPRING_SUMMER = "spring_summer"
    AUTUMN_WINTER = "autumn_winter"


class ReviewStatus(str, Enum):
    """Status of a review."""
    PENDING = "pending"        # Waiting for host moderation
    APPROVED = "approved"      # Approved by host and visible
    REJECTED = "rejected"      # Rejected by host, not visible
    FLAGGED = "flagged"        # Flagged for inappropriate content
    ARCHIVED = "archived"      # Archived/hidden


class ReviewModerationAction(str, Enum):
    """Actions hosts can take on reviews."""
    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"
    VERIFY_VISIT = "verify_visit"
    UNVERIFY_VISIT = "unverify_visit"
    ARCHIVE = "archive"


class Attraction(Base):
    """
    Main attraction model with host contribution capabilities.
    
    Allows hosts to create and manage local attractions, adding their
    personal insights and expertise to enhance guest experiences.
    """
    
    __tablename__ = "attractions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Host Attribution (who created/contributed this)
    created_by_host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    last_updated_by_host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=True)
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(500), nullable=True)  # For previews
    
    # Classification
    attraction_type = Column(String(50), nullable=False, index=True)
    category_tags = Column(JSON, default=[])  # ["family_friendly", "outdoor", "cultural"]
    
    # Location Information (Croatian focus)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True, index=True)  # Istria, Kvarner, etc.
    county = Column(String(100), nullable=True)
    country = Column(String(50), default="Croatia")
    
    # Geographic Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Host Personal Insights (This is where hosts add value!)
    host_personal_tip = Column(Text, nullable=True)  # Host's personal recommendation
    host_favorite_time = Column(String(100), nullable=True)  # "early morning", "sunset"
    host_insider_info = Column(Text, nullable=True)  # Local secrets, best approaches
    host_story = Column(Text, nullable=True)  # Personal story about this place
    host_recommended_duration = Column(String(50), nullable=True)  # "2-3 hours"
    
    # Practical Information
    opening_hours = Column(JSON, default={})  # Day-specific hours
    admission_fee = Column(String(100), nullable=True)  # "Free", "10 EUR", "Varies"
    contact_info = Column(JSON, default={})  # phone, email, website
    
    # Seasonal Information
    seasonal_availability = Column(String(50), default=SeasonalAvailability.YEAR_ROUND)
    best_months = Column(JSON, default=[])  # [3, 4, 5] for March-May
    seasonal_notes = Column(Text, nullable=True)  # Special seasonal considerations
    
    # Guest Experience Data
    difficulty_level = Column(String(20), default="easy")  # easy, moderate, challenging
    duration_hours = Column(Float, nullable=True)  # Estimated duration
    group_size_recommendation = Column(String(100), nullable=True)
    
    # Accessibility & Requirements
    accessibility_info = Column(JSON, default={})  # wheelchair, parking, etc.
    age_suitability = Column(JSON, default=[])  # ["children", "adults", "seniors"]
    required_equipment = Column(JSON, default=[])  # ["hiking_boots", "swimwear"]
    
    # Multi-language Support
    name_translations = Column(JSON, default={})  # {"hr": "Croatian name", "de": "German"}
    description_translations = Column(JSON, default={})
    
    # Vector Embedding for Semantic Search
    embedding = Column(Text, nullable=True)  # Stored as text, converted to vector in queries
    
    # Media and Visual Content
    featured_image_url = Column(String(2048), nullable=True)
    image_gallery = Column(JSON, default=[])  # URLs to images
    video_url = Column(String(2048), nullable=True)
    
    # Content Moderation
    status = Column(String(20), default=AttractionStatus.DRAFT)
    moderation_notes = Column(Text, nullable=True)  # Admin feedback
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)  # Admin who approved
    
    # Analytics and Performance
    view_count = Column(Integer, default=0)
    recommendation_count = Column(Integer, default=0)  # How often recommended
    guest_rating = Column(Float, nullable=True)  # Average guest rating
    total_ratings = Column(Integer, default=0)

    # Google Places enrichment (cached locally — refresh after 30 days)
    google_place_id = Column(String(200), nullable=True, index=True)
    google_rating = Column(Float, nullable=True)
    google_user_ratings_total = Column(Integer, nullable=True)
    google_price_level = Column(Integer, nullable=True)
    google_photos = Column(JSON, default=[])
    google_website = Column(String(500), nullable=True)
    google_phone = Column(String(50), nullable=True)
    google_data_fetched_at = Column(DateTime, nullable=True)
    
    # Wikipedia Enrichment
    wikipedia_pageid = Column(Integer, nullable=True)
    wikipedia_extract = Column(Text, nullable=True)
    wikipedia_url = Column(String(500), nullable=True)
    wikipedia_image = Column(String(500), nullable=True)
    google_user_ratings_total = Column(Integer, nullable=True)
    google_price_level = Column(Integer, nullable=True)  # 0-4
    google_photos = Column(JSON, default=[])  # photo reference URLs (no binary fetch)
    google_website = Column(String(500), nullable=True)
    google_phone = Column(String(50), nullable=True)
    google_data_fetched_at = Column(DateTime, nullable=True)
    
    # Host Collaboration
    contributing_hosts = Column(JSON, default=[])  # Other hosts who added info
    collaboration_notes = Column(Text, nullable=True)  # Notes for other hosts
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)  # When approved and published


class AttractionReview(Base):
    """
    Guest reviews for attractions, contributed by hosts' guests.
    Enhanced with host moderation capabilities and review status management.
    """
    
    __tablename__ = "attraction_reviews"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    attraction_id = Column(UUID(as_uuid=True), ForeignKey("attractions.id"), nullable=False)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)  # Host who recommended it
    
    # Review Content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    
    # Experience Details
    visit_date = Column(Date, nullable=True)
    group_size = Column(Integer, nullable=True)
    visit_duration = Column(String(50), nullable=True)
    
    # Helpful Information
    pros = Column(JSON, default=[])  # What they liked
    cons = Column(JSON, default=[])  # What could be better
    tips_for_others = Column(Text, nullable=True)
    
    # Guest Information (anonymous)
    guest_age_group = Column(String(20), nullable=True)  # "family", "young_adults", etc.
    guest_travel_style = Column(String(20), nullable=True)  # "budget", "luxury", etc.
    
    # Review Status and Moderation
    status = Column(String(20), default=ReviewStatus.PENDING)
    moderation_notes = Column(Text, nullable=True)  # Host's moderation feedback
    moderated_at = Column(DateTime, nullable=True)  # When host took action
    moderated_by_host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=True)
    
    # Verification and Quality
    verified_visit = Column(Boolean, default=False)  # Host can verify the visit
    verified_at = Column(DateTime, nullable=True)
    quality_score = Column(Float, nullable=True)  # Algorithm-based quality score (0-1)
    helpfulness_score = Column(Float, default=0.0)  # Based on other guest feedback
    
    # Review Interaction
    helpful_votes = Column(Integer, default=0)  # How many found it helpful
    total_votes = Column(Integer, default=0)    # Total votes received
    
    # Language and Translation
    language = Column(String(10), default="en")  # Language of the review
    translated_versions = Column(JSON, default={})  # Translated versions
    
    # Analytics and Tracking
    view_count = Column(Integer, default=0)  # How many times viewed
    response_from_host = Column(Text, nullable=True)  # Host can respond to reviews
    host_response_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewModerationLog(Base):
    """
    Log of moderation actions taken on reviews by hosts.
    """
    
    __tablename__ = "review_moderation_logs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    review_id = Column(UUID(as_uuid=True), ForeignKey("attraction_reviews.id"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    
    # Moderation Details
    action = Column(String(20), nullable=False)  # ReviewModerationAction
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)  # Why the action was taken
    notes = Column(Text, nullable=True)   # Additional notes
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class SeasonalEvent(Base):
    """
    Seasonal events and activities that hosts can create and manage.
    """
    
    __tablename__ = "seasonal_events"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Host Attribution
    created_by_host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    
    # Event Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False)  # "festival", "market", "seasonal_activity"
    
    # Location
    location = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False)
    venue_details = Column(Text, nullable=True)
    
    # Timing
    start_date = Column(Date, nullable=True)  # For specific events
    end_date = Column(Date, nullable=True)
    recurring_pattern = Column(String(100), nullable=True)  # "annual", "monthly", "weekly"
    time_of_day = Column(String(100), nullable=True)  # "morning", "evening", "all_day"
    
    # Host Insights
    host_recommendation = Column(Text, nullable=True)
    best_time_to_visit = Column(String(200), nullable=True)
    what_to_expect = Column(Text, nullable=True)
    host_personal_experience = Column(Text, nullable=True)
    
    # Practical Info
    admission_info = Column(String(200), nullable=True)
    booking_required = Column(Boolean, default=False)
    contact_info = Column(JSON, default={})
    
    # Media
    featured_image_url = Column(String(2048), nullable=True)
    gallery_images = Column(JSON, default=[])
    
    # Status
    status = Column(String(20), default=AttractionStatus.DRAFT)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API requests/responses
class AttractionBase(SQLModel):
    """Base attraction model for common fields."""
    name: str = Field(max_length=200)
    description: str
    short_description: Optional[str] = Field(default=None, max_length=1000)
    attraction_type: str = Field(max_length=50)
    category_tags: List[str] = Field(default_factory=list)
    address: Optional[str] = None
    city: str = Field(max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Host insights
    host_personal_tip: Optional[str] = None
    host_favorite_time: Optional[str] = Field(default=None, max_length=100)
    host_insider_info: Optional[str] = None
    host_story: Optional[str] = None
    host_recommended_duration: Optional[str] = Field(default=None, max_length=50)
    
    # Practical info
    opening_hours: Dict[str, Any] = Field(default_factory=dict)
    admission_fee: Optional[str] = Field(default=None, max_length=100)
    contact_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Experience
    difficulty_level: str = Field(default="easy", max_length=20)
    duration_hours: Optional[float] = Field(default=None, ge=0.1, le=24.0)
    group_size_recommendation: Optional[str] = Field(default=None, max_length=100)
    
    # Seasonal
    seasonal_availability: str = Field(default=SeasonalAvailability.YEAR_ROUND)
    best_months: List[int] = Field(default_factory=list)
    seasonal_notes: Optional[str] = None

    # Media (URLs or data URLs from host uploads)
    featured_image_url: Optional[str] = Field(default=None, max_length=2048)
    image_gallery: List[str] = Field(default_factory=list)


class AttractionCreate(AttractionBase):
    """Attraction creation model."""
    accessibility_info: Dict[str, Any] = Field(default_factory=dict)
    age_suitability: List[str] = Field(default_factory=list)
    required_equipment: List[str] = Field(default_factory=list)
    name_translations: Dict[str, str] = Field(default_factory=dict)
    description_translations: Dict[str, str] = Field(default_factory=dict)


class AttractionUpdate(SQLModel):
    """Attraction update model - all fields optional."""
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=1000)
    attraction_type: Optional[str] = Field(default=None, max_length=50)
    category_tags: Optional[List[str]] = None
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    host_personal_tip: Optional[str] = None
    host_favorite_time: Optional[str] = Field(default=None, max_length=100)
    host_insider_info: Optional[str] = None
    host_story: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    admission_fee: Optional[str] = Field(default=None, max_length=100)
    contact_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    difficulty_level: Optional[str] = Field(default="", max_length=20)
    duration_hours: Optional[float] = Field(default=None, ge=0.1, le=24.0)
    group_size_recommendation: Optional[str] = Field(default=None, max_length=100)
    seasonal_availability: Optional[str] = None
    best_months: Optional[List[int]] = None
    seasonal_notes: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=20)
    featured_image_url: Optional[str] = Field(default=None, max_length=2048)
    image_gallery: Optional[List[str]] = Field(default_factory=list)


class AttractionGooglePlacesFields(SQLModel):
    """Google Places data cached on the attraction row."""

    google_place_id: Optional[str] = Field(default=None, max_length=200)
    google_rating: Optional[float] = None
    google_user_ratings_total: Optional[int] = None
    google_price_level: Optional[int] = Field(default=None, ge=0, le=4)
    google_photos: List[str] = Field(default_factory=list)
    google_website: Optional[str] = Field(default=None, max_length=500)
    google_phone: Optional[str] = Field(default=None, max_length=50)
    google_data_fetched_at: Optional[datetime] = None
    google_maps_url: Optional[str] = Field(default=None, max_length=500)
    static_map_image_url: Optional[str] = Field(default=None, max_length=2048)

    
    # Wikipedia enrichment
    wikipedia_pageid: Optional[int] = None
    wikipedia_extract: Optional[str] = None
    wikipedia_url: Optional[str] = None
    wikipedia_image: Optional[str] = None

class AttractionResponse(AttractionBase, AttractionGooglePlacesFields):
    """Attraction response model."""
    id: uuid.UUID
    created_by_host_id: uuid.UUID
    status: str
    view_count: int
    recommendation_count: int
    guest_rating: Optional[float] = None
    total_ratings: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

        # Google Places enrichment
    google_place_id: Optional[str] = None
    google_rating: Optional[float] = None
    google_user_ratings_total: Optional[int] = None
    google_price_level: Optional[int] = None
    google_photos: List[str] = Field(default_factory=list)
    google_website: Optional[str] = None
    google_phone: Optional[str] = None
    
    # Wikipedia enrichment
    wikipedia_pageid: Optional[int] = None
    wikipedia_extract: Optional[str] = None
    wikipedia_url: Optional[str] = None
    wikipedia_image: Optional[str] = None

class Config:
        from_attributes = True


class AttractionAnalyticsFeedbackItem(SQLModel):
    """Recent guest feedback row for host attraction analytics."""

    rating: int = Field(ge=1, le=5)
    comment: str
    created_at: str


class AttractionAnalyticsResponse(SQLModel):
    """Host dashboard analytics bundle for a single attraction."""

    views: int = 0
    recommendations: int = 0
    average_rating: float = 0.0
    review_count: int = 0
    guest_feedback: List[AttractionAnalyticsFeedbackItem] = Field(default_factory=list)


class AttractionPublicResponse(AttractionGooglePlacesFields):
    """Public attraction fields — no host insider content or tenant IDs."""

    id: uuid.UUID
    name: str
    description: str
    short_description: Optional[str] = None
    attraction_type: str
    category_tags: List[str] = Field(default_factory=list)
    address: Optional[str] = None
    city: str
    region: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_hours: Dict[str, Any] = Field(default_factory=dict)
    admission_fee: Optional[str] = None
    difficulty_level: str = "easy"
    duration_hours: Optional[float] = None
    group_size_recommendation: Optional[str] = None
    seasonal_availability: str = SeasonalAvailability.YEAR_ROUND
    best_months: List[int] = Field(default_factory=list)
    seasonal_notes: Optional[str] = None
    featured_image_url: Optional[str] = None
    image_gallery: List[str] = Field(default_factory=list)
    guest_rating: Optional[float] = None
    total_ratings: int

    class Config:
        from_attributes = True


class AttractionEnrichRequest(SQLModel):
    """Request body for POST /attractions/enrich."""

    city: Optional[str] = Field(default=None, max_length=100)
    attraction_ids: Optional[List[uuid.UUID]] = None
    force_refresh: bool = False


class AttractionEnrichResultItem(SQLModel):
    """Per-attraction enrichment outcome."""

    attraction_id: uuid.UUID
    name: str
    success: bool
    skipped: bool = False
    message: str = ""


class AttractionEnrichResponse(SQLModel):
    """Batch enrichment summary."""

    total: int
    enriched: int
    skipped: int
    failed: int
    results: List[AttractionEnrichResultItem] = Field(default_factory=list)


class AttractionEnrichmentStatusResponse(SQLModel):
    """Enrichment status for a single attraction."""

    attraction_id: uuid.UUID
    name: str
    is_enriched: bool
    google_place_id: Optional[str] = None
    google_data_fetched_at: Optional[datetime] = None
    days_since_fetch: Optional[int] = None
    needs_refresh: bool
    google_rating: Optional[float] = None
    google_user_ratings_total: Optional[int] = None
    google_price_level: Optional[int] = None
    google_photos_count: int = 0
    has_website: bool = False
    has_phone: bool = False
    google_maps_url: Optional[str] = None


class AttractionReviewCreate(SQLModel):
    """Attraction review creation model."""
    attraction_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = Field(default=None, max_length=200)
    review_text: Optional[str] = None
    visit_date: Optional[date] = None
    group_size: Optional[int] = Field(default=None, ge=1)
    visit_duration: Optional[str] = Field(default=None, max_length=50)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    tips_for_others: Optional[str] = None
    guest_age_group: Optional[str] = Field(default=None, max_length=20)
    guest_travel_style: Optional[str] = Field(default=None, max_length=20)
    language: str = Field(default="en", max_length=10)


class AttractionReviewResponse(AttractionReviewCreate):
    """Attraction review response model."""
    id: uuid.UUID
    host_id: uuid.UUID
    guest_group_id: uuid.UUID
    status: str
    verified_visit: bool
    quality_score: Optional[float] = None
    helpfulness_score: float
    helpful_votes: int
    total_votes: int
    view_count: int
    response_from_host: Optional[str] = None
    host_response_at: Optional[datetime] = None
    moderation_notes: Optional[str] = None
    moderated_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AttractionReviewPublicResponse(SQLModel):
    """Public-facing review fields (approved reviews only)."""
    id: uuid.UUID
    attraction_id: uuid.UUID
    rating: int
    title: Optional[str] = None
    review_text: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    tips_for_others: Optional[str] = None
    language: str = "en"
    response_from_host: Optional[str] = None

    class Config:
        from_attributes = True


class AttractionReviewGuestSubmitResponse(SQLModel):
    """Guest submit acknowledgement — id + moderation status only."""

    id: uuid.UUID
    status: str


class AttractionReviewUpdate(SQLModel):
    """Attraction review update model (for guests)."""
    title: Optional[str] = Field(default=None, max_length=200)
    review_text: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    tips_for_others: Optional[str] = None


class ReviewModerationRequest(SQLModel):
    """Request model for host review moderation actions."""
    action: str = Field(regex="^(approve|reject|flag|verify_visit|unverify_visit|archive)$")
    reason: Optional[str] = None
    notes: Optional[str] = None
    host_response: Optional[str] = None


class ReviewModerationResponse(SQLModel):
    """Response model for review moderation actions."""
    success: bool
    message: str
    review_id: uuid.UUID
    new_status: str
    action_taken: str
    moderated_at: datetime

    class Config:
        from_attributes = True


class ReviewAnalytics(SQLModel):
    """Analytics model for attraction reviews."""
    attraction_id: uuid.UUID
    total_reviews: int
    approved_reviews: int
    pending_reviews: int
    rejected_reviews: int
    average_rating: Optional[float] = None
    rating_distribution: Dict[int, int] = Field(default_factory=dict)  # {1: count, 2: count, ...}
    verified_reviews: int
    recent_reviews: int  # Last 30 days
    most_helpful_review_id: Optional[uuid.UUID] = None
    response_rate: float = Field(default=0.0)  # % of reviews with host responses


class HostReviewStats(SQLModel):
    """Host statistics for review management."""
    host_id: uuid.UUID
    total_reviews_received: int
    pending_moderation: int
    approved_this_month: int
    rejected_this_month: int
    average_response_time_hours: Optional[float] = None
    verification_rate: float = Field(default=0.0)  # % of reviews verified
    response_rate: float = Field(default=0.0)  # % of reviews with responses


class ReviewHelpfulnessVote(SQLModel):
    """Model for voting on review helpfulness."""
    helpful: bool  # True for helpful, False for not helpful


class ReviewHelpfulnessVoteResponse(SQLModel):
    """POST /attractions/reviews/{review_id}/helpful acknowledgement."""

    success: bool
    message: str
    review_id: str
    helpful: bool


class GuestReviewSubmission(SQLModel):
    """Model for guest review submission with access code."""
    access_code: str = Field(min_length=6, max_length=12)
    review_data: AttractionReviewCreate


class ReviewSearchRequest(SQLModel):
    """Search and filter request for reviews."""
    attraction_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    rating_min: Optional[int] = Field(default=None, ge=1, le=5)
    rating_max: Optional[int] = Field(default=None, ge=1, le=5)
    verified_only: bool = Field(default=False)
    language: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ReviewSearchResponse(SQLModel):
    """Response model for review search."""
    reviews: List[AttractionReviewResponse]
    total_count: int
    page: int
    per_page: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class SeasonalEventCreate(SQLModel):
    """Seasonal event creation model."""
    name: str = Field(max_length=200)
    description: str
    event_type: str = Field(max_length=50)
    location: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(max_length=100)
    venue_details: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    recurring_pattern: Optional[str] = Field(default=None, max_length=100)
    time_of_day: Optional[str] = Field(default=None, max_length=100)
    host_recommendation: Optional[str] = None
    best_time_to_visit: Optional[str] = Field(default=None, max_length=200)
    what_to_expect: Optional[str] = None
    host_personal_experience: Optional[str] = None
    admission_info: Optional[str] = Field(default=None, max_length=200)
    booking_required: bool = Field(default=False)
    contact_info: Dict[str, Any] = Field(default_factory=dict)


class SeasonalEventResponse(SeasonalEventCreate):
    """Seasonal event response model."""
    id: uuid.UUID
    created_by_host_id: uuid.UUID
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeasonalEventPublicResponse(SQLModel):
    """Public seasonal event listing — guest-safe fields only."""

    id: uuid.UUID
    name: str
    description: str
    event_type: str
    location: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(max_length=100)
    venue_details: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    recurring_pattern: Optional[str] = Field(default=None, max_length=100)
    time_of_day: Optional[str] = Field(default=None, max_length=100)
    what_to_expect: Optional[str] = None
    admission_info: Optional[str] = Field(default=None, max_length=200)
    booking_required: bool = Field(default=False)

    class Config:
        from_attributes = True


class HostContributionStats(SQLModel):
    """Statistics for host contributions to the platform."""
    host_id: uuid.UUID
    total_attractions: int
    approved_attractions: int
    pending_attractions: int
    total_views: int
    total_recommendations: int
    average_rating: Optional[float] = None
    expertise_areas: List[str] = Field(default_factory=list)
    contribution_score: float = Field(default=0.0)  # Algorithm-based score


# Utility functions for Croatian tourism
CROATIAN_REGIONS = [
    "Istria", "Kvarner", "Dalmatia", "Slavonia", "Central Croatia",
    "Zagorje", "Međimurje", "Lika-Senj", "Banovina"
]

LOVRAN_AREA_ATTRACTIONS = [
    "Lungomare Promenade", "Učka Nature Park", "Lovran Old Town",
    "St. George Church", "Medveja Beach", "Lovranska Draga",
    "Opatija", "Rijeka", "Kastav"
]

CROATIAN_SEASONAL_EVENTS = [
    "Marunada (Chestnut Festival)", "Cherry Days", "Asparagus Festival",
    "Summer Festival", "Advent Markets", "Carnival", "Wine Harvest"
]


class AttractionSearchRequest(SQLModel):
    """Attraction search request model."""
    q: Optional[str] = None
    city: Optional[str] = None
    attraction_type: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None
    language: Optional[str] = "en"
    skip: int = 0
    limit: int = 20


class AttractionSearchResponse(SQLModel):
    """Attraction search response model."""
    results: List[AttractionPublicResponse]
    total_count: int
    page: int
    per_page: int
    query: Optional[str] = None


class HostContributionCreate(SQLModel):
    """Host contribution creation model."""
    contribution_type: str = Field(max_length=50)  # tip, story, insider_info, etc.
    title: str = Field(max_length=200)
    content: str
    is_public: bool = True
    language: str = Field(default="en", max_length=10)


class HostContributionPublicBase(SQLModel):
    """Public contribution content — no visibility flag or lifecycle timestamps."""

    contribution_type: str = Field(max_length=50)
    title: str = Field(max_length=200)
    content: str
    language: str = Field(default="en", max_length=10)


class HostContributionPublicResponse(HostContributionPublicBase):
    """Public contribution fields — no contributing host tenant ID."""

    id: uuid.UUID
    attraction_id: uuid.UUID

    class Config:
        from_attributes = True


class HostContributionResponse(HostContributionCreate):
    """Host contribution response model."""
    id: uuid.UUID
    attraction_id: uuid.UUID
    host_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True 