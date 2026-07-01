"""
Guest group models for the Croatian tourist host platform.

Defines guest groups, access codes, and preference collection for
the B2B SaaS platform where hosts provide AI-powered local guide services.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import secrets
import string

from pydantic import ConfigDict, field_validator

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field

from app.db.postgresql.connection import Base
from app.core.config import settings


class GuestGroupStatus(str, Enum):
    """Status of a guest group."""
    PENDING = "pending"  # Access code created, not yet activated
    ACTIVE = "active"    # Group has activated and is using services
    COMPLETED = "completed"  # Stay completed
    CANCELLED = "cancelled"  # Cancelled by host or expired


class AccessCodeStatus(str, Enum):
    """Status of an access code."""
    ACTIVE = "active"      # Code can be used
    USED = "used"         # Code has been activated by guests
    EXPIRED = "expired"   # Code has expired
    REVOKED = "revoked"   # Code revoked by host


class GuestGroup(Base):
    """
    Guest group model for Croatian tourist platform.
    
    Represents a group of tourists staying with a host who will
    receive AI-powered local recommendations and services.
    """
    
    __tablename__ = "guest_groups"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Host Relationship
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    # Links this stay/group to the host's accommodation row (host_profiles). Set on create; ON DELETE SET NULL in DB.
    host_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("host_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Group Information
    group_name = Column(String(100), nullable=True)  # Optional friendly name
    group_size = Column(Integer, nullable=False)
    status = Column(String(20), default=GuestGroupStatus.PENDING)
    
    # Stay Information
    check_in_date = Column(DateTime, nullable=True)
    check_out_date = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    actual_departure = Column(DateTime, nullable=True)
    
    # Contact Information
    lead_guest_name = Column(String(100), nullable=True)
    lead_guest_email = Column(String(255), nullable=True)
    lead_guest_phone = Column(String(20), nullable=True)
    
    # Language Preferences (Croatian/English/German/Italian)
    preferred_language = Column(String(10), default="en")
    supported_languages = Column(JSON, default=["en", "hr"])
    
    # Group Preferences (JSON for flexibility)
    age_groups = Column(JSON, default=[])  # ["adults", "children", "seniors"]
    interests = Column(JSON, default=[])   # ["nature", "culture", "food", "adventure"]
    mobility_requirements = Column(JSON, default=[])  # ["wheelchair_accessible", "limited_walking"]
    dietary_restrictions = Column(JSON, default=[])   # ["vegetarian", "gluten_free", "allergies"]
    
    # Vector Embedding for Preference Matching
    preference_embedding = Column(Text, nullable=True)  # Stored as text, converted to vector in queries
    budget_level = Column(String(20), default="moderate")  # "budget", "moderate", "luxury"
    
    # Activity Preferences
    preferred_activities = Column(JSON, default=[])  # Specific activities they want
    avoided_activities = Column(JSON, default=[])    # Things to avoid
    
    # Personalization Data
    previous_visits_croatia = Column(Boolean, default=False)
    travel_style = Column(String(50), default="balanced")  # "relaxed", "balanced", "active"
    group_dynamics = Column(String(50), default="family")  # "family", "friends", "couple", "solo"
    
    # Croatian Tourism Specific
    interested_regions = Column(JSON, default=["lovran"])  # Croatian regions of interest
    seasonal_preferences = Column(JSON, default={})        # Season-specific preferences
    
    # Analytics and Feedback
    recommendations_given = Column(Integer, default=0)
    recommendations_accepted = Column(Integer, default=0)
    satisfaction_rating = Column(Float, nullable=True)  # 1-5 rating
    feedback_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)  # When they first used access code


class AccessCode(Base):
    """
    Temporary access codes for guest groups.
    
    Hosts generate these codes for their guests to access the platform
    and receive personalized recommendations.
    """
    
    __tablename__ = "access_codes"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Code Information
    code = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(String(20), default=AccessCodeStatus.ACTIVE)
    
    # Relationships
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    
    # Expiration and Usage
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    max_usage_count = Column(Integer, default=1)  # How many times code can be used
    
    # Security
    created_by_ip = Column(String(45), nullable=True)  # IP that created the code
    used_from_ip = Column(String(45), nullable=True)   # IP that used the code
    user_agent = Column(Text, nullable=True)           # Browser info when used
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuestPreference(Base):
    """
    Individual guest preferences within a group.
    
    Allows for more granular preference tracking when group members
    have different interests or requirements.
    """
    
    __tablename__ = "guest_preferences"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    
    # Individual Guest Info
    guest_name = Column(String(100), nullable=True)
    age_category = Column(String(200), nullable=True)  # e.g. "child,adult" (multi-select)
    
    # Individual Preferences
    personal_interests = Column(JSON, default=[])
    dietary_needs = Column(JSON, default=[])
    mobility_notes = Column(Text, nullable=True)
    language_preference = Column(String(10), default="en")
    
    # Croatian Cultural Interests
    cultural_interests = Column(JSON, default=[])  # ["history", "folklore", "music", "art"]
    food_interests = Column(JSON, default=[])      # ["seafood", "wine", "traditional", "modern"]
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuestEVisitorData(Base):
    """
    Individual guest e-visitor registration data for Croatia.
    
    Stores personal information required for Croatian e-visitor registration
    including passport/ID details and personal information.
    """
    
    __tablename__ = "guest_evisitor_data"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    
    # Personal Information (Required for e-visitor)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    nationality = Column(String(100), nullable=False)
    
    # ID Information
    id_type = Column(String(20), nullable=False)  # "passport" or "id_card"
    id_number = Column(String(100), nullable=False)  # Passport or ID number
    id_issuing_country = Column(String(100), nullable=False)
    id_expiry_date = Column(DateTime, nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Stay Information
    arrival_date = Column(DateTime, nullable=False)
    departure_date = Column(DateTime, nullable=False)
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # E-visitor Status
    evisitor_registered = Column(Boolean, default=False)
    evisitor_registration_date = Column(DateTime, nullable=True)
    evisitor_confirmation_number = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API requests/responses
class GuestGroupBase(SQLModel):
    """Base guest group model for common fields."""
    group_name: Optional[str] = Field(default=None, max_length=100)
    group_size: int = Field(ge=1, le=50)
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    lead_guest_name: Optional[str] = Field(default=None, max_length=100)
    lead_guest_email: Optional[str] = Field(default=None, max_length=255)
    lead_guest_phone: Optional[str] = Field(default=None, max_length=20)
    preferred_language: str = Field(default="en", max_length=10)
    supported_languages: List[str] = Field(default_factory=lambda: ["en", "hr"])
    budget_level: str = Field(default="moderate", max_length=20)
    travel_style: str = Field(default="balanced", max_length=50)
    group_dynamics: str = Field(default="family", max_length=50)


class GuestGroupAccommodationSummary(SQLModel):
    """Live snapshot from host_profiles for dashboards and guest context (one property per host today)."""

    host_profile_id: uuid.UUID
    property_name: Optional[str] = None
    property_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class GuestGroupAccommodationGuestSummary(SQLModel):
    """Guest-safe accommodation snapshot — omits host_profile_id."""

    property_name: Optional[str] = None
    property_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class GuestGroupCreate(GuestGroupBase):
    """Guest group creation model."""
    age_groups: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    mobility_requirements: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    preferred_activities: List[str] = Field(default_factory=list)
    avoided_activities: List[str] = Field(default_factory=list)
    previous_visits_croatia: bool = Field(default=False)
    interested_regions: List[str] = Field(default_factory=lambda: ["lovran"])
    seasonal_preferences: Dict[str, Any] = Field(default_factory=dict)


class GuestGroupUpdate(SQLModel):
    """Guest group update model - all fields optional."""
    group_name: Optional[str] = Field(default=None, max_length=100)
    group_size: Optional[int] = Field(default=None, ge=1, le=50)
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    lead_guest_name: Optional[str] = Field(default=None, max_length=100)
    lead_guest_email: Optional[str] = Field(default=None, max_length=255)
    lead_guest_phone: Optional[str] = Field(default=None, max_length=20)
    preferred_language: Optional[str] = Field(default=None, max_length=10)
    age_groups: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    budget_level: Optional[str] = Field(default=None, max_length=20)
    satisfaction_rating: Optional[float] = Field(default=None, ge=1, le=5)
    feedback_notes: Optional[str] = None


class GuestGroupResponse(GuestGroupBase):
    """Guest group response model."""
    id: uuid.UUID
    host_id: uuid.UUID
    host_profile_id: Optional[uuid.UUID] = None
    status: str
    age_groups: List[str]
    interests: List[str]
    mobility_requirements: List[str]
    dietary_restrictions: List[str]
    recommendations_given: int
    recommendations_accepted: int
    satisfaction_rating: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    # Latest usable access code for host UI (not stored on guest_groups row)
    access_code: Optional[str] = Field(default=None, max_length=32)
    # Current accommodation/property for this group (from host_profiles)
    accommodation: Optional[GuestGroupAccommodationSummary] = None
    saved_event_recommendations: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator(
        "age_groups",
        "interests",
        "mobility_requirements",
        "dietary_restrictions",
        mode="before",
    )
    @classmethod
    def _coerce_json_lists(cls, value: Any) -> List[str]:
        return value if isinstance(value, list) else []

    @field_validator("supported_languages", mode="before")
    @classmethod
    def _coerce_supported_languages(cls, value: Any) -> List[str]:
        return value if isinstance(value, list) else ["en", "hr"]

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _coerce_preferred_language(cls, value: Any) -> str:
        return value if value else "en"

    @field_validator("budget_level", mode="before")
    @classmethod
    def _coerce_budget_level(cls, value: Any) -> str:
        return value if value else "moderate"

    @field_validator("travel_style", mode="before")
    @classmethod
    def _coerce_travel_style(cls, value: Any) -> str:
        return value if value else "balanced"

    @field_validator("group_dynamics", mode="before")
    @classmethod
    def _coerce_group_dynamics(cls, value: Any) -> str:
        return value if value else "family"

    class Config:
        from_attributes = True


class GuestGroupGuestBase(SQLModel):
    """Guest-safe group fields — no lead contact PII (email/phone)."""

    group_name: Optional[str] = Field(default=None, max_length=100)
    group_size: int = Field(ge=1, le=50)
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    lead_guest_name: Optional[str] = Field(default=None, max_length=100)
    preferred_language: str = Field(default="en", max_length=10)
    supported_languages: List[str] = Field(default_factory=lambda: ["en", "hr"])
    budget_level: str = Field(default="moderate", max_length=20)
    travel_style: str = Field(default="balanced", max_length=50)
    group_dynamics: str = Field(default="family", max_length=50)


class GuestGroupGuestResponse(GuestGroupGuestBase):
    """Guest access-code response — omits host/internal tenant IDs and lead contact PII."""

    id: uuid.UUID
    age_groups: List[str]
    interests: List[str]
    mobility_requirements: List[str]
    dietary_restrictions: List[str]
    access_code: Optional[str] = Field(default=None, max_length=32)
    accommodation: Optional[GuestGroupAccommodationGuestSummary] = None
    saved_event_recommendations: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator(
        "age_groups",
        "interests",
        "mobility_requirements",
        "dietary_restrictions",
        mode="before",
    )
    @classmethod
    def _coerce_json_lists_guest(cls, value: Any) -> List[str]:
        return value if isinstance(value, list) else []

    @field_validator("supported_languages", mode="before")
    @classmethod
    def _coerce_supported_languages_guest(cls, value: Any) -> List[str]:
        return value if isinstance(value, list) else ["en", "hr"]

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _coerce_preferred_language_guest(cls, value: Any) -> str:
        return value if value else "en"

    @field_validator("budget_level", mode="before")
    @classmethod
    def _coerce_budget_level_guest(cls, value: Any) -> str:
        return value if value else "moderate"

    @field_validator("travel_style", mode="before")
    @classmethod
    def _coerce_travel_style_guest(cls, value: Any) -> str:
        return value if value else "balanced"

    @field_validator("group_dynamics", mode="before")
    @classmethod
    def _coerce_group_dynamics_guest(cls, value: Any) -> str:
        return value if value else "family"

    class Config:
        from_attributes = True


class HostGuestExperienceResponse(SQLModel):
    """
    Host-authenticated payload to open the same guest UI guests use.

    Includes the canonical guest group record plus the current usable access code (if any).
    """

    guest_group: GuestGroupResponse
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None
    guest_app_path: str = ""
    guest_join_path: str = "/guest/join"


class AccessCodeCreate(SQLModel):
    """Access code creation model."""
    guest_group_id: uuid.UUID
    expires_in_hours: int = Field(default=168, ge=1, le=720)  # Default 7 days, max 30 days
    max_usage_count: int = Field(default=1, ge=1, le=10)


class AccessCodeResponse(SQLModel):
    """Access code response model."""
    id: uuid.UUID
    code: str
    status: str
    guest_group_id: uuid.UUID
    expires_at: datetime
    usage_count: int
    max_usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AccessCodeActivation(SQLModel):
    """Access code activation model."""
    code: str = Field(max_length=20)
    guest_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GuestPreferenceCreate(SQLModel):
    """Guest preference creation model."""
    guest_name: Optional[str] = Field(default=None, max_length=100)
    age_category: Optional[str] = Field(default=None, max_length=200)
    personal_interests: List[str] = Field(default_factory=list)
    dietary_needs: List[str] = Field(default_factory=list)
    mobility_notes: Optional[str] = None
    language_preference: str = Field(default="en", max_length=10)
    cultural_interests: List[str] = Field(default_factory=list)
    food_interests: List[str] = Field(default_factory=list)


class GuestPreferenceGuestResponse(GuestPreferenceCreate):
    """Guest access-code preference response — omits guest_group_id and lifecycle timestamps."""

    id: uuid.UUID

    class Config:
        from_attributes = True


class GuestPreferenceResponse(GuestPreferenceCreate):
    """Guest preference response model."""
    id: uuid.UUID
    guest_group_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GuestPreferenceUpdate(SQLModel):
    """Guest preference update model."""
    guest_name: Optional[str] = Field(default=None, max_length=100)
    age_category: Optional[str] = Field(default=None, max_length=200)
    personal_interests: Optional[List[str]] = None
    dietary_needs: Optional[List[str]] = None
    mobility_notes: Optional[str] = None
    language_preference: Optional[str] = Field(default=None, max_length=10)
    cultural_interests: Optional[List[str]] = None
    food_interests: Optional[List[str]] = None


class AccessCodeValidation(SQLModel):
    """Access code validation request model."""
    access_code: str = Field(min_length=6, max_length=12)
    ip_address: Optional[str] = Field(default=None, max_length=45)


def generate_access_code(length: int = None) -> str:
    """
    Generate a secure, human-readable access code.
    
    Args:
        length: Length of the code (default from settings)
        
    Returns:
        str: Generated access code
    """
    if length is None:
        length = settings.access_code_length
    
    # Use uppercase letters and numbers, avoid confusing characters (0, O, I, 1)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def is_access_code_valid(code: str) -> bool:
    """
    Validate access code format.
    
    Args:
        code: Access code to validate
        
    Returns:
        bool: True if format is valid
    """
    if not code or len(code) != settings.access_code_length:
        return False
    
    # Check if code contains only allowed characters
    allowed_chars = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    return all(c in allowed_chars for c in code.upper())


# E-visitor Data Pydantic Models
class GuestEVisitorDataBase(SQLModel):
    """Base e-visitor data model for common fields."""
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    date_of_birth: datetime
    nationality: str = Field(max_length=100)
    id_type: str = Field(max_length=20)  # "passport" or "id_card"
    id_number: str = Field(max_length=100)
    id_issuing_country: str = Field(max_length=100)
    id_expiry_date: Optional[datetime] = None
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state_province: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=100)
    arrival_date: datetime
    departure_date: datetime
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)


class GuestEVisitorDataCreate(GuestEVisitorDataBase):
    """E-visitor data creation model."""
    pass


class EVisitorRegisterRequest(SQLModel):
    """Request body for marking e-visitor data as registered."""
    confirmation_number: str = Field(..., max_length=100)


class GuestEVisitorDataUpdate(SQLModel):
    """E-visitor data update model - all fields optional."""
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[datetime] = None
    nationality: Optional[str] = Field(default=None, max_length=100)
    id_type: Optional[str] = Field(default=None, max_length=20)
    id_number: Optional[str] = Field(default=None, max_length=100)
    id_issuing_country: Optional[str] = Field(default=None, max_length=100)
    id_expiry_date: Optional[datetime] = None
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state_province: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=100)
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)


class GuestEVisitorDataResponse(GuestEVisitorDataBase):
    """E-visitor data response model."""
    id: uuid.UUID
    guest_group_id: uuid.UUID
    evisitor_registered: bool
    evisitor_registration_date: Optional[datetime] = None
    evisitor_confirmation_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HostGroupBroadcastRecord(SQLModel):
    """Single host broadcast stored on guest group seasonal_preferences."""

    message: str
    host_name: str
    sent_at: str


class HostGroupBroadcastDelivery(SQLModel):
    """Delivery channels attempted for a host group broadcast."""

    in_app: bool
    sms: bool


class HostGroupBroadcastResponse(SQLModel):
    """POST /guest-groups/{id}/message success envelope."""

    success: bool
    message: str
    delivery: HostGroupBroadcastDelivery
    broadcast: HostGroupBroadcastRecord


class HostSavedEventRecord(SQLModel):
    """Host-visible saved event row (guest fields + host workflow)."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    title: Optional[str] = None
    host_status: Optional[str] = None
    host_action_at: Optional[str] = None
    host_note: Optional[str] = None


class HostSavedEventsResponse(SQLModel):
    """PUT /guest-groups/{id}/saved-events/{event_id} success envelope."""

    success: bool
    saved_event_ids: List[str]
    saved_events: List[HostSavedEventRecord]


class HostSavedEventItineraryActivityResponse(SQLModel):
    """POST .../saved-events/{event_id}/itinerary-activity success envelope."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    saved_event_ids: List[str]
    saved_events: List[HostSavedEventRecord]
    activity: Dict[str, Any]
    already_added: bool


class GuestSavedEventRecord(SQLModel):
    """Guest-visible saved event row (mirrors frontend GuestSavedEventRecord)."""

    model_config = ConfigDict(extra="ignore")

    event_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    event_type: Optional[str] = None
    cities: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    schedule_label: Optional[str] = None
    venue_name: Optional[str] = None
    admission_info: Optional[str] = None
    booking_required: Optional[Union[bool, str]] = None
    distance_km: Optional[Union[float, str]] = None
    why_recommended: Optional[str] = None
    plan_hint: Optional[str] = None
    saved_at: Optional[str] = None
    in_itinerary: Optional[bool] = None
    guest_action: Optional[str] = None
    guest_note: Optional[str] = None
    guest_action_at: Optional[str] = None
    preferred_day_plan_id: Optional[str] = None
    preferred_day_number: Optional[Union[int, str]] = None
    preferred_day_title: Optional[str] = None
    itinerary_activity_title: Optional[str] = None
    itinerary_activity_start_time: Optional[str] = None
    itinerary_activity_end_time: Optional[str] = None


class GuestSavedEventsResponse(SQLModel):
    """Guest saved-events list/mutation success envelope."""

    success: bool
    saved_event_ids: List[str]
    saved_events: List[GuestSavedEventRecord]


class GuestHostOfferingsApiResponse(SQLModel):
    """GET /guest-groups/access/{access_code}/host-offerings success envelope."""

    success: bool
    host_offerings: Dict[str, Any]
    access_code: str
    valid_access: bool


class GuestEventRecommendation(SQLModel):
    """Single guest-facing event recommendation."""

    model_config = ConfigDict(extra="ignore")

    event_id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    event_type: Optional[str] = None
    cities: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    schedule_label: Optional[str] = None
    admission_info: Optional[str] = None
    booking_required: Optional[bool] = None
    distance_km: Optional[float] = None
    venue_name: Optional[str] = None
    why_recommended: Optional[str] = None
    plan_hint: Optional[str] = None


class GuestEventStayWindow(SQLModel):
    """Stay window metadata on event recommendations."""

    check_in: Optional[str] = None
    check_out: Optional[str] = None


class GuestEventRecommendationsResponse(SQLModel):
    """GET /guest-groups/access/{access_code}/event-recommendations payload."""

    model_config = ConfigDict(extra="ignore")

    recommendations: List[GuestEventRecommendation] = Field(default_factory=list)
    city: Optional[str] = None
    access_code: Optional[str] = None
    stay_window: Optional[GuestEventStayWindow] = None
    personalization: Optional[Dict[str, Any]] = None


class GuestConciergeMessageResponse(SQLModel):
    """POST host-message and assistant routes for guest access code."""

    success: bool
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None
    can_contact_host: Optional[bool] = None