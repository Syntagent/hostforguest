"""
Host models for the Croatian tourist host platform.

Defines the Host entity and related models for B2B SaaS platform
where Croatian tourist hosts can manage their guest services.
"""

from typing import Optional, List, Dict, Any
import re
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlmodel import SQLModel, Field
from pydantic import computed_field, field_validator
import uuid

from app.db.postgresql.connection import Base

# Pragmatic email check (avoids extra email-validator dependency; API + forms only).
_HOST_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Host(Base):
    """
    Host model for Croatian tourist accommodation hosts.
    
    Represents hosts who offer accommodations and want to provide
    AI-powered local guide services to their guests.
    """
    
    __tablename__ = "hosts"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Business Information
    business_name = Column(String(200), nullable=True)  # Optional business name
    business_type = Column(String(50), default="apartment")  # apartment, villa, hotel, guesthouse
    
    # Location Information (Croatian focus)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    county = Column(String(100), nullable=True)  # Croatian county (županija)
    postal_code = Column(String(10), nullable=True)
    country = Column(String(50), default="Croatia")
    
    # Geographic Coordinates (for Lovran area)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Host Specialties and Local Knowledge
    local_specialties = Column(JSON, default=[])  # ["istrian_cuisine", "wine_tours", "hiking"]
    languages = Column(JSON, default=["hr", "en"])  # Supported languages
    
    # Business Configuration
    max_group_size = Column(Integer, default=12)
    typical_stay_duration = Column(Integer, default=7)  # Days
    
    # Host Description and Profile
    description = Column(Text, nullable=True)
    welcome_message = Column(Text, nullable=True)
    local_tips = Column(JSON, default=[])  # Array of local tips and recommendations
    
    # Subscription and Business Model
    subscription_tier = Column(String(20), default="basic")  # basic, premium, enterprise
    subscription_active = Column(Boolean, default=True)
    
    # Platform Statistics
    total_guest_groups = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    total_recommendations_given = Column(Integer, default=0)
    
    # Guest Access
    guest_access_code = Column(String(10), nullable=True, unique=True, index=True)
    onboarding_completed = Column(Boolean, default=False)

    # Telegram A2A bot binding
    telegram_id = Column(BigInteger, nullable=True, unique=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Add sessions relationship with correct Mapped type
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="host", cascade="all, delete-orphan")


class HostProfile(Base):
    """
    Extended host profile information.
    
    Additional details about the host's services, preferences,
    and local knowledge that don't fit in the main Host model.
    """
    
    __tablename__ = "host_profiles"
    
    # Primary Key and Foreign Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    
    # Property Information
    property_name = Column(String(255), nullable=True)  # Name of the property
    
    # Detailed Business Information
    property_type = Column(String(50), nullable=True)  # apartment, villa, house, room
    number_of_rooms = Column(Integer, nullable=True)
    max_guests = Column(Integer, nullable=True)
    
    # Location Information
    city = Column(String(100), nullable=True)
    county = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Services Offered
    services_offered = Column(JSON, default=[])  # ["airport_pickup", "grocery_shopping", "tour_guide"]
    amenities = Column(JSON, default=[])  # ["wifi", "parking", "kitchen", "sea_view"]
    
    # Local Expertise Areas
    expertise_areas = Column(JSON, default=[])  # ["istrian_wines", "hidden_beaches", "hiking_trails"]
    favorite_local_spots = Column(JSON, default=[])  # Array of favorite local recommendations
    
    # Partner Network
    trusted_partners = Column(JSON, default=[])  # Local business partnerships
    special_offers = Column(JSON, default=[])  # Special deals for guests
    
    # Seasonal Information
    seasonal_recommendations = Column(JSON, default={})  # Season-specific tips
    availability_calendar = Column(JSON, default={})  # Availability patterns
    
    # Guest Preferences
    typical_guest_profile = Column(JSON, default={})  # Common guest characteristics
    success_stories = Column(JSON, default=[])  # Positive guest experiences
    
    # Marketing and Promotion
    profile_image_url = Column(String(500), nullable=True)
    gallery_images = Column(JSON, default=[])  # Property and local area photos
    social_media_links = Column(JSON, default={})  # Social media profiles
    
    # Reviews and Testimonials
    guest_testimonials = Column(JSON, default=[])  # Guest reviews and testimonials
    
    # Onboarding and AI Data
    location_story = Column(Text, nullable=True)  # Personal location story
    google_verified = Column(Boolean, default=False)  # Google Places verified
    onboarding_completed = Column(Boolean, default=False)  # Onboarding completion status
    onboarding_completed_at = Column(String(50), nullable=True)  # ISO timestamp
    ai_generated_content = Column(Boolean, default=False)  # Has AI-generated content
    property_rules = Column(JSON, default={})  # check-in/out, house rules, wifi, emergency notes
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSession(Base):
    """
    Database model for storing user sessions and tokens.
    
    Provides session management, token invalidation, and user activity tracking.
    """
    __tablename__ = "user_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    host: Mapped["Host"] = relationship("Host", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, host_id={self.host_id}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_refresh_expired(self) -> bool:
        """Check if refresh token is expired."""
        if not self.refresh_expires_at:
            return True
        return datetime.utcnow() > self.refresh_expires_at


# Pydantic models for API requests/responses
class HostBase(SQLModel):
    """Base host model for common fields."""
    email: str = Field(index=True, max_length=255)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    business_name: Optional[str] = Field(default=None, max_length=200)
    business_type: str = Field(default="apartment", max_length=50)
    address: str
    city: str = Field(max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=10)
    country: str = Field(default="Croatia", max_length=50)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    local_specialties: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["hr", "en"])
    max_group_size: int = Field(default=12, ge=1, le=50)
    description: Optional[str] = None
    welcome_message: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str) -> str:
        s = (v or "").strip()
        if len(s) > 255:
            raise ValueError("Email must be at most 255 characters")
        if not _HOST_EMAIL_RE.match(s):
            raise ValueError("Invalid email address")
        return s.lower()


class HostCreate(HostBase):
    """Host creation model."""
    password: str = Field(min_length=8, max_length=100)


class HostUpdate(SQLModel):
    """Host update model - all fields optional."""
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    business_name: Optional[str] = Field(default=None, max_length=200)
    business_type: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    local_specialties: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    max_group_size: Optional[int] = Field(default=None, ge=1, le=50)
    description: Optional[str] = None
    welcome_message: Optional[str] = None


class HostResponse(HostBase):
    """Host response model."""
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    subscription_tier: str
    total_guest_groups: int
    average_rating: float
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
        
    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name from first and last name."""
        return f"{self.first_name} {self.last_name}".strip()


class HostLogin(SQLModel):
    """Host login credentials."""
    email: str = Field(max_length=255)
    password: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def _login_email_format(cls, v: str) -> str:
        s = (v or "").strip()
        if len(s) > 255:
            raise ValueError("Email must be at most 255 characters")
        if not _HOST_EMAIL_RE.match(s):
            raise ValueError("Invalid email address")
        return s.lower()


class HostPasswordChange(SQLModel):
    """Change password for the authenticated host."""
    current_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)


class HostProfileCreate(SQLModel):
    """Host profile creation model."""
    property_name: Optional[str] = Field(default=None, max_length=255)
    property_type: Optional[str] = Field(default=None, max_length=50)
    number_of_rooms: Optional[int] = Field(default=None, ge=1)
    max_guests: Optional[int] = Field(default=None, ge=1)
    services_offered: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    expertise_areas: List[str] = Field(default_factory=list)
    favorite_local_spots: List[Dict[str, Any]] = Field(default_factory=list)
    location_story: Optional[str] = None


class HostProfileUpdate(SQLModel):
    """Host profile update model - all fields optional."""
    property_name: Optional[str] = Field(default=None, max_length=255)  # Name of the property
    property_type: Optional[str] = Field(default=None, max_length=50)
    number_of_rooms: Optional[int] = Field(default=None, ge=1)
    max_guests: Optional[int] = Field(default=None, ge=1)
    services_offered: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    favorite_local_spots: Optional[List[Dict[str, Any]]] = None
    location_story: Optional[str] = None
    # Location fields
    city: Optional[str] = Field(default=None, max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    profile_image_url: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    social_media_links: Optional[Dict[str, str]] = None
    guest_testimonials: Optional[List[Dict[str, Any]]] = None
    seasonal_recommendations: Optional[Dict[str, Any]] = None
    availability_calendar: Optional[Dict[str, Any]] = None
    typical_guest_profile: Optional[Dict[str, Any]] = None
    success_stories: Optional[List[Dict[str, Any]]] = None
    trusted_partners: Optional[List[str]] = None
    special_offers: Optional[List[str]] = None
    property_rules: Optional[Dict[str, Any]] = None


class HostProfileResponse(SQLModel):
    """Host profile response model."""
    id: uuid.UUID
    host_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    # All the fields that can be returned
    property_name: Optional[str] = None
    property_type: Optional[str] = None
    number_of_rooms: Optional[int] = None
    max_guests: Optional[int] = None
    services_offered: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    favorite_local_spots: Optional[List[Dict[str, Any]]] = None
    location_story: Optional[str] = None
    
    # Location fields
    city: Optional[str] = None
    county: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Additional fields
    profile_image_url: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    social_media_links: Optional[Dict[str, str]] = None
    guest_testimonials: Optional[List[Dict[str, Any]]] = None
    seasonal_recommendations: Optional[Dict[str, Any]] = None
    availability_calendar: Optional[Dict[str, Any]] = None
    typical_guest_profile: Optional[Dict[str, Any]] = None
    success_stories: Optional[List[Dict[str, Any]]] = None
    trusted_partners: Optional[List[str]] = None
    special_offers: Optional[List[str]] = None
    property_rules: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True 