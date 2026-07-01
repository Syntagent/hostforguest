"""
Itinerary and day planning models for guest trip planning.

Enables guests to create detailed itineraries with attractions, transportation,
timing, and Google Maps integration for Croatian tourism experiences.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timezone
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, Date, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import ConfigDict, model_validator, field_validator
from sqlmodel import SQLModel, Field

from app.db.postgresql.connection import Base


class ItineraryStatus(str, Enum):
    """Status of an itinerary."""
    DRAFT = "draft"          # Being created
    ACTIVE = "active"        # Currently being used
    COMPLETED = "completed"  # Trip finished
    ARCHIVED = "archived"    # Saved for reference


class ActivityStatus(str, Enum):
    """Status of an activity in itinerary."""
    PLANNED = "planned"      # Scheduled but not started
    ACTIVE = "active"        # Currently doing
    COMPLETED = "completed"  # Finished
    SKIPPED = "skipped"      # Decided not to do
    CANCELLED = "cancelled"  # Cancelled due to weather/other


class TransportMode(str, Enum):
    """Transportation modes for getting around."""
    WALKING = "walking"      # Walking directions
    DRIVING = "driving"      # Car/taxi
    TRANSIT = "transit"      # Public transport
    CYCLING = "cycling"      # Bicycle
    BOAT = "boat"           # Ferry/boat transport


class WeatherSuitability(str, Enum):
    """Weather suitability for activities."""
    ANY = "any"             # Weather independent
    SUNNY = "sunny"         # Best in sunny weather
    CLOUDY = "cloudy"       # Good for cloudy days
    INDOOR = "indoor"       # Indoor activity
    RAINY = "rainy"         # Good for rainy days


class Itinerary(Base):
    """
    Main itinerary model for guest trip planning.
    
    Represents a complete trip plan with daily activities, timing,
    and transportation for a guest group's Croatian tourism experience.
    """
    
    __tablename__ = "itineraries"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships (guest_group_id null when is_template — reusable route template)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=True, index=True)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    
    # Basic Information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=ItineraryStatus.DRAFT)
    is_template = Column(Boolean, default=False, nullable=False, index=True)
    
    # Trip Timing (null for templates until assigned to a guest group)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    total_days = Column(Integer, nullable=False, default=1)
    
    # Base Location (where guests are staying)
    base_location = Column(String(200), nullable=False)  # "Oprić 71, Lovran"
    base_latitude = Column(Float, nullable=True)
    base_longitude = Column(Float, nullable=True)
    
    # Trip Preferences
    pace = Column(String(20), default="moderate")  # "relaxed", "moderate", "active"
    budget_level = Column(String(20), default="moderate")  # "budget", "moderate", "luxury"
    transportation_preference = Column(String(20), default="mixed")  # "walking", "driving", "mixed"
    
    # Language and Localization
    language = Column(String(10), default="en")
    currency = Column(String(10), default="EUR")
    
    # Group Dynamics
    group_interests = Column(JSON, default=[])  # ["culture", "nature", "food"]
    mobility_considerations = Column(JSON, default=[])  # ["wheelchair", "limited_walking"]
    
    # Weather and Seasonal
    weather_backup_plans = Column(Boolean, default=True)  # Include indoor alternatives
    seasonal_preferences = Column(JSON, default={})  # Season-specific preferences
    
    # Collaboration Features
    shared_with_guests = Column(Boolean, default=True)  # Guests can view and comment
    allows_guest_modifications = Column(Boolean, default=False)  # Guests can modify
    voting_enabled = Column(Boolean, default=False)  # Guests can vote on activities
    
    # Analytics and Feedback
    completion_rate = Column(Float, default=0.0)  # % of activities completed
    guest_satisfaction = Column(Float, nullable=True)  # 1-5 rating
    host_notes = Column(Text, nullable=True)  # Host's notes and observations
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)


class DayPlan(Base):
    """
    Daily plan within an itinerary.
    
    Represents one day of activities with timing, transportation,
    and location information for detailed day planning.
    """
    
    __tablename__ = "day_plans"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    itinerary_id = Column(UUID(as_uuid=True), ForeignKey("itineraries.id"), nullable=False, index=True)
    
    # Day Information
    day_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    date = Column(Date, nullable=False)
    title = Column(String(200), nullable=True)  # "Exploring Lovran Old Town"
    theme = Column(String(100), nullable=True)  # "Cultural Day", "Nature Day", "Food Tour"
    
    # Timing
    start_time = Column(Time, default=time(9, 0))  # Default 9:00 AM
    end_time = Column(Time, default=time(18, 0))   # Default 6:00 PM
    estimated_duration = Column(Integer, nullable=True)  # Total minutes
    
    # Weather and Conditions
    weather_dependent = Column(Boolean, default=True)
    backup_plan_id = Column(UUID(as_uuid=True), ForeignKey("day_plans.id"), nullable=True)  # Indoor alternative
    
    # Transportation Summary
    total_distance = Column(Float, nullable=True)  # Total km for the day
    total_travel_time = Column(Integer, nullable=True)  # Total travel minutes
    main_transport_mode = Column(String(20), default=TransportMode.WALKING)
    
    # Budget and Costs
    estimated_cost = Column(Float, nullable=True)  # Estimated cost per person
    currency = Column(String(10), default="EUR")
    cost_breakdown = Column(JSON, default={})  # {"transport": 10, "food": 25, "activities": 30}
    
    # Status and Progress
    status = Column(String(20), default=ActivityStatus.PLANNED)
    completion_percentage = Column(Float, default=0.0)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    
    # Notes and Feedback
    description = Column(Text, nullable=True)
    host_tips = Column(Text, nullable=True)  # Host's advice for this day
    guest_notes = Column(Text, nullable=True)  # Guest's notes and feedback
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ItineraryActivity(Base):
    """
    Individual activity within a day plan.
    
    Represents a single activity (attraction visit, meal, transport)
    with detailed timing, location, and Google Maps integration.
    """
    
    __tablename__ = "itinerary_activities"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    day_plan_id = Column(UUID(as_uuid=True), ForeignKey("day_plans.id"), nullable=False, index=True)
    attraction_id = Column(UUID(as_uuid=True), ForeignKey("attractions.id"), nullable=True)  # If it's an attraction
    
    # Activity Information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(String(50), nullable=False)  # "attraction", "meal", "transport", "rest"
    category = Column(String(50), nullable=True)  # "cultural", "nature", "food", "shopping"
    
    # Timing
    sequence_order = Column(Integer, nullable=False)  # Order in the day (1, 2, 3...)
    scheduled_start_time = Column(DateTime, nullable=False)
    scheduled_end_time = Column(DateTime, nullable=False)
    estimated_duration = Column(Integer, nullable=False)  # Minutes
    buffer_time = Column(Integer, default=15)  # Extra time buffer in minutes
    
    # Location and Maps Integration
    location_name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    google_place_id = Column(String(200), nullable=True)  # Google Places API ID
    google_maps_url = Column(String(500), nullable=True)  # Direct Google Maps URL
    
    # Transportation to This Activity
    transport_from_previous = Column(String(20), default=TransportMode.WALKING)
    travel_time_minutes = Column(Integer, default=0)
    travel_distance_km = Column(Float, default=0.0)
    transport_cost = Column(Float, default=0.0)
    transport_instructions = Column(Text, nullable=True)  # Detailed directions
    
    # Activity Details
    cost_per_person = Column(Float, nullable=True)
    currency = Column(String(10), default="EUR")
    booking_required = Column(Boolean, default=False)
    booking_info = Column(JSON, default={})  # Contact, website, etc.
    opening_hours = Column(JSON, default={})  # Day-specific hours
    
    # Weather and Conditions
    weather_suitability = Column(String(20), default=WeatherSuitability.ANY)
    indoor_activity = Column(Boolean, default=False)
    backup_activity_id = Column(UUID(as_uuid=True), ForeignKey("itinerary_activities.id"), nullable=True)
    
    # Host Insights
    host_tip = Column(Text, nullable=True)  # Host's personal recommendation
    host_story = Column(Text, nullable=True)  # Host's personal story
    insider_info = Column(Text, nullable=True)  # Local secrets
    best_time_to_visit = Column(String(100), nullable=True)  # "early morning", "sunset"
    
    # Guest Interaction
    priority_level = Column(String(20), default="medium")  # "high", "medium", "low"
    guest_interest_score = Column(Float, nullable=True)  # Based on preferences
    allows_skipping = Column(Boolean, default=True)  # Can be skipped if needed
    
    # Status and Feedback
    status = Column(String(20), default=ActivityStatus.PLANNED)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    actual_cost = Column(Float, nullable=True)
    guest_rating = Column(Float, nullable=True)  # 1-5 rating
    guest_feedback = Column(Text, nullable=True)
    photos_taken = Column(JSON, default=[])  # URLs to photos
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityVote(Base):
    """
    Guest voting on activities for collaborative planning.
    """
    
    __tablename__ = "activity_votes"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    itinerary_activity_id = Column(UUID(as_uuid=True), ForeignKey("itinerary_activities.id"), nullable=False)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    
    # Vote Information
    guest_name = Column(String(100), nullable=True)  # Optional guest identification
    vote = Column(String(20), nullable=False)  # "yes", "no", "maybe"
    priority = Column(Integer, nullable=True)  # 1-5 priority rating
    reason = Column(Text, nullable=True)  # Why they voted this way
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API requests/responses

class ItineraryBase(SQLModel):
    """Base itinerary model for common fields."""
    title: str = Field(max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    base_location: str = Field(max_length=200)
    pace: str = Field(default="moderate", max_length=20)
    budget_level: str = Field(default="moderate", max_length=20)
    transportation_preference: str = Field(default="mixed", max_length=20)
    language: str = Field(default="en", max_length=10)


class ItineraryCreate(ItineraryBase):
    """Itinerary creation model."""
    is_template: bool = Field(default=False)
    group_interests: List[str] = Field(default_factory=list)
    mobility_considerations: List[str] = Field(default_factory=list)
    weather_backup_plans: bool = Field(default=True)
    shared_with_guests: bool = Field(default=True)
    allows_guest_modifications: bool = Field(default=False)
    voting_enabled: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_template_vs_guest_itinerary(self) -> "ItineraryCreate":
        if self.is_template:
            return self
        if self.start_date is None or self.end_date is None:
            raise ValueError("start_date and end_date are required when is_template is false")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ItineraryResponse(ItineraryBase):
    """Itinerary response model."""
    id: uuid.UUID
    guest_group_id: Optional[uuid.UUID] = None
    host_id: uuid.UUID
    status: str
    is_template: bool = False
    total_days: int
    completion_rate: float
    guest_satisfaction: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItineraryAssignFromTemplate(SQLModel):
    """Assign a route template to a guest group with a trip start date."""
    guest_group_id: uuid.UUID
    start_date: date


class DayPlanBase(SQLModel):
    """Base day plan model."""
    day_number: int = Field(ge=1)
    date: date
    title: Optional[str] = Field(default=None, max_length=200)
    theme: Optional[str] = Field(default=None, max_length=100)
    start_time: time = Field(default=time(9, 0))
    end_time: time = Field(default=time(18, 0))


class DayPlanCreate(DayPlanBase):
    """Day plan creation model."""
    description: Optional[str] = None
    weather_dependent: bool = Field(default=True)
    main_transport_mode: str = Field(default=TransportMode.WALKING)
    estimated_cost: Optional[float] = Field(default=None, ge=0)


class DayPlanResponse(DayPlanBase):
    """Day plan response model."""
    id: uuid.UUID
    itinerary_id: uuid.UUID
    status: str
    description: Optional[str] = None
    host_tips: Optional[str] = None
    estimated_duration: Optional[int] = None
    total_distance: Optional[float] = None
    total_travel_time: Optional[int] = None
    estimated_cost: Optional[float] = None
    completion_percentage: float
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityBase(SQLModel):
    """Base activity model."""
    title: str = Field(max_length=200)
    description: Optional[str] = None
    activity_type: str = Field(max_length=50)
    location_name: str = Field(max_length=200)
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    estimated_duration: int = Field(ge=1)


class ActivityCreate(ActivityBase):
    """Activity creation model."""
    category: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    attraction_id: Optional[uuid.UUID] = None
    host_tip: Optional[str] = None
    transport_from_previous: str = Field(default=TransportMode.WALKING)
    cost_per_person: Optional[float] = Field(default=None, ge=0)
    booking_required: bool = Field(default=False)
    priority_level: str = Field(default="medium", max_length=20)

    @field_validator("scheduled_start_time", "scheduled_end_time", mode="before")
    @classmethod
    def _coerce_naive_schedule(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        raise TypeError("scheduled time must be datetime or ISO string")


class ActivityResponse(ActivityBase):
    """Activity response model."""
    id: uuid.UUID
    day_plan_id: uuid.UUID
    sequence_order: int
    status: str
    travel_time_minutes: int
    travel_distance_km: float
    cost_per_person: Optional[float] = None
    google_maps_url: Optional[str] = None
    host_tip: Optional[str] = None
    guest_rating: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityVoteCreate(SQLModel):
    """Activity vote creation model."""
    guest_name: Optional[str] = Field(default=None, max_length=100)
    vote: str = Field(regex="^(yes|no|maybe)$")
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    reason: Optional[str] = None


class ActivityVoteResponse(ActivityVoteCreate):
    """Activity vote response model."""
    id: uuid.UUID
    itinerary_activity_id: uuid.UUID
    guest_group_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ItineraryWithDetails(ItineraryResponse):
    """Complete itinerary with day plans and activities."""
    day_plans: List[DayPlanResponse] = Field(default_factory=list)


class DayPlanWithActivities(DayPlanResponse):
    """Day plan with all activities."""
    activities: List[ActivityResponse] = Field(default_factory=list)


class GoogleMapsDirectionsRequest(SQLModel):
    """Request for Google Maps directions."""
    origin: str  # Address or coordinates
    destination: str  # Address or coordinates
    mode: str = Field(default=TransportMode.WALKING)
    language: str = Field(default="en")
    avoid: Optional[List[str]] = Field(default_factory=list)  # "tolls", "highways", "ferries"


class GoogleMapsDirectionsResponse(SQLModel):
    """Google Maps directions response."""
    distance: str  # "2.5 km"
    duration: str  # "30 mins"
    distance_value: int  # Distance in meters
    duration_value: int  # Duration in seconds
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    polyline: Optional[str] = None  # Encoded polyline
    maps_url: str  # Direct Google Maps URL


class ItinerarySuggestionRequest(SQLModel):
    """Request for AI-generated itinerary suggestions (guest-specific or generic template)."""
    guest_group_id: Optional[uuid.UUID] = None
    duration_days: int = Field(ge=1, le=14)
    interests: List[str] = Field(default_factory=list)
    theme_prompt: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional theme for generic template (e.g. 'Culinary day in Istria')",
    )
    budget_level: str = Field(default="moderate")
    pace: str = Field(default="moderate")
    must_see_attractions: List[uuid.UUID] = Field(default_factory=list)
    avoid_activities: List[str] = Field(default_factory=list)


class LLMItineraryDayPlan(SQLModel):
    """One day of an LLM-produced plan; attraction IDs must match the catalog sent in the prompt."""

    model_config = ConfigDict(extra="ignore")

    day_number: int = Field(ge=1, le=14)
    day_title: str = Field(default="", max_length=200)
    day_theme: str = Field(default="", max_length=150)
    ordered_attraction_ids: List[str] = Field(
        default_factory=list,
        description="UUID strings from the provided catalog, visit order within the day",
    )


class LLMItineraryPlanResult(SQLModel):
    """Structured JSON output from the itinerary LLM (Gemini native schema or parsed chat fallback)."""

    model_config = ConfigDict(extra="ignore")

    itinerary_title: str = Field(default="", max_length=200)
    itinerary_description: str = Field(default="", max_length=4000)
    reasoning_summary: str = Field(default="", max_length=2000)
    days: List[LLMItineraryDayPlan] = Field(default_factory=list)


class ItinerarySuggestionResponse(SQLModel):
    """AI-generated itinerary suggestion."""
    suggested_itinerary: ItineraryCreate
    day_plans: List[DayPlanCreate]
    activities: List[ActivityCreate]
    reasoning: str  # Why this itinerary was suggested
    alternatives: List[str] = Field(default_factory=list)  # Alternative suggestions 