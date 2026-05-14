"""
Recommendation models for the Croatian tourist host platform.

Defines recommendation requests, results, and tracking for the
intelligent recommendation engine that combines host knowledge,
guest preferences, and real-time tourism data.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, Date, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field

from app.db.postgresql.connection import Base


class RecommendationType(str, Enum):
    """Types of recommendations."""
    ATTRACTION = "attraction"           # Specific attractions
    ACTIVITY = "activity"              # Activities to do
    DINING = "dining"                  # Restaurants and food
    EVENT = "event"                    # Seasonal events and festivals
    EXPERIENCE = "experience"          # Complete experiences
    ITINERARY = "itinerary"           # Full day/multi-day itineraries


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations."""
    LOW = "low"                # Nice to have
    MEDIUM = "medium"          # Good match
    HIGH = "high"              # Strong match
    URGENT = "urgent"          # Time-sensitive (limited availability)


class WeatherContext(str, Enum):
    """Weather contexts for recommendations."""
    SUNNY = "sunny"            # Clear, sunny weather
    RAINY = "rainy"           # Rainy weather
    CLOUDY = "cloudy"         # Overcast but dry
    HOT = "hot"               # Very hot weather
    COLD = "cold"             # Cold weather
    WINDY = "windy"           # Windy conditions


class RecommendationRequest(Base):
    """
    Recommendation request from a guest group.
    
    Captures the context and preferences for generating
    personalized recommendations.
    """
    
    __tablename__ = "recommendation_requests"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    
    # Request Context
    request_type = Column(String(50), default=RecommendationType.ATTRACTION)
    request_date = Column(DateTime, default=datetime.utcnow)
    target_date = Column(Date, nullable=True)  # When they want to do the activity
    
    # Location Context
    current_location = Column(String(200), nullable=True)
    preferred_radius_km = Column(Float, default=10.0)  # Search radius
    
    # Group Context
    group_size = Column(Integer, nullable=True)
    duration_hours = Column(Float, nullable=True)  # How long they have
    budget_range = Column(String(50), nullable=True)  # "budget", "moderate", "luxury"
    
    # Weather and Seasonal Context
    weather_context = Column(String(20), nullable=True)
    season = Column(String(20), nullable=True)
    temperature_celsius = Column(Integer, nullable=True)
    
    # Specific Preferences for this Request
    preferred_categories = Column(JSON, default=[])  # Specific categories requested
    excluded_categories = Column(JSON, default=[])   # Categories to avoid
    accessibility_requirements = Column(JSON, default=[])
    
    # Language Preference
    response_language = Column(String(10), default="en")
    
    # Request Status
    status = Column(String(20), default="pending")  # pending, processed, delivered
    processed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    user_agent = Column(String(500), nullable=True)  # Device/browser info
    ip_address = Column(String(45), nullable=True)


class Recommendation(Base):
    """
    Individual recommendation generated for a guest group.
    
    Links attractions/activities with personalized context and
    host insights for guest groups.
    """
    
    __tablename__ = "recommendations"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    request_id = Column(UUID(as_uuid=True), ForeignKey("recommendation_requests.id"), nullable=False)
    attraction_id = Column(UUID(as_uuid=True), ForeignKey("attractions.id"), nullable=True)
    seasonal_event_id = Column(UUID(as_uuid=True), ForeignKey("seasonal_events.id"), nullable=True)
    
    # Recommendation Details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    recommendation_type = Column(String(50), nullable=False)
    
    # Scoring and Ranking
    relevance_score = Column(Float, nullable=False)  # 0.0 - 1.0
    priority = Column(String(20), default=RecommendationPriority.MEDIUM)
    rank_order = Column(Integer, nullable=False)  # Order in the recommendation list
    
    # Host Contribution
    host_insight = Column(Text, nullable=True)  # Host's personal insight for this recommendation
    host_tip = Column(Text, nullable=True)      # Specific tip from host
    why_recommended = Column(Text, nullable=True)  # Algorithm explanation
    
    # Practical Information
    estimated_duration = Column(String(50), nullable=True)  # "2-3 hours"
    best_time_to_visit = Column(String(100), nullable=True)  # "Morning", "Afternoon"
    estimated_cost = Column(String(50), nullable=True)      # "Free", "10-20 EUR"
    booking_required = Column(Boolean, default=False)
    booking_info = Column(Text, nullable=True)
    
    # Location and Logistics
    distance_km = Column(Float, nullable=True)
    travel_time_minutes = Column(Integer, nullable=True)
    transportation_note = Column(String(200), nullable=True)
    
    # Contextual Suitability
    weather_suitability = Column(JSON, default=[])  # Weather conditions this is good for
    season_suitability = Column(JSON, default=[])   # Seasons this is best
    group_suitability = Column(JSON, default=[])    # Group types this suits
    
    # Multi-language Support
    title_translations = Column(JSON, default={})
    description_translations = Column(JSON, default={})
    
    # Guest Interaction
    viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    accepted = Column(Boolean, default=False)  # Guest indicated interest
    accepted_at = Column(DateTime, nullable=True)
    feedback_rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_comment = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecommendationSet(Base):
    """
    A complete set of recommendations delivered to a guest group.
    
    Groups individual recommendations together and tracks
    overall performance and guest satisfaction.
    """
    
    __tablename__ = "recommendation_sets"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    request_id = Column(UUID(as_uuid=True), ForeignKey("recommendation_requests.id"), nullable=False)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    
    # Set Information
    title = Column(String(200), nullable=False)  # "Morning Activities in Lovran"
    description = Column(Text, nullable=True)
    total_recommendations = Column(Integer, default=0)
    
    # Algorithm Information
    algorithm_version = Column(String(20), default="1.0")
    processing_time_ms = Column(Integer, nullable=True)
    
    # Personalization Context
    personalization_factors = Column(JSON, default={})  # What factors were considered
    host_contribution_weight = Column(Float, default=0.5)  # How much host input influenced
    
    # Performance Tracking
    delivered_at = Column(DateTime, nullable=True)
    first_viewed_at = Column(DateTime, nullable=True)
    recommendations_viewed = Column(Integer, default=0)
    recommendations_accepted = Column(Integer, default=0)
    
    # Guest Feedback
    overall_satisfaction = Column(Integer, nullable=True)  # 1-5 stars
    feedback_comment = Column(Text, nullable=True)
    would_recommend_host = Column(Boolean, nullable=True)
    
    # Host Performance
    host_insights_helpful = Column(Boolean, nullable=True)  # Guest feedback on host insights
    host_tips_used = Column(Integer, default=0)  # How many host tips were included
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API requests/responses
class RecommendationRequestAPI(SQLModel):
    """API request model for recommendations."""
    guest_group_id: Optional[uuid.UUID] = None
    max_recommendations: int = Field(default=10, ge=1, le=50)
    include_weather: bool = True
    include_seasonal: bool = True
    activity_duration: Optional[str] = None  # "short", "half_day", "full_day"
    preferred_time: Optional[str] = None     # "morning", "afternoon", "evening"
    weather_context: Optional[Dict[str, Any]] = None
    target_date: Optional[date] = None
    current_location: Optional[str] = None
    preferred_radius_km: float = Field(default=15.0, ge=0.1, le=100.0)
    preferred_categories: List[str] = Field(default_factory=list)
    excluded_categories: List[str] = Field(default_factory=list)
    accessibility_requirements: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)


class RecommendationRequestCreate(SQLModel):
    """Recommendation request creation model."""
    request_type: str = Field(default=RecommendationType.ATTRACTION, max_length=50)
    target_date: Optional[date] = None
    current_location: Optional[str] = Field(default=None, max_length=200)
    preferred_radius_km: float = Field(default=10.0, ge=0.1, le=100.0)
    group_size: Optional[int] = Field(default=None, ge=1, le=50)
    duration_hours: Optional[float] = Field(default=None, ge=0.5, le=24.0)
    budget_range: Optional[str] = Field(default=None, max_length=50)
    weather_context: Optional[str] = Field(default=None, max_length=20)
    temperature_celsius: Optional[int] = Field(default=None, ge=-20, le=50)
    preferred_categories: List[str] = Field(default_factory=list)
    excluded_categories: List[str] = Field(default_factory=list)
    accessibility_requirements: List[str] = Field(default_factory=list)
    response_language: str = Field(default="en", max_length=10)


class RecommendationResponse(SQLModel):
    """Individual recommendation response model."""
    id: uuid.UUID
    title: str
    description: str
    recommendation_type: str
    relevance_score: float
    priority: str
    rank_order: int
    host_insight: Optional[str] = None
    host_tip: Optional[str] = None
    why_recommended: Optional[str] = None
    estimated_duration: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    estimated_cost: Optional[str] = None
    booking_required: bool
    booking_info: Optional[str] = None
    distance_km: Optional[float] = None
    travel_time_minutes: Optional[int] = None
    transportation_note: Optional[str] = None
    weather_suitability: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationSetResponse(SQLModel):
    """Recommendation set response model."""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    total_recommendations: int
    algorithm_version: str
    processing_time_ms: Optional[int] = None
    personalization_factors: Dict[str, Any] = Field(default_factory=dict)
    host_contribution_weight: float
    recommendations: List[RecommendationResponse] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationFeedback(SQLModel):
    """Feedback on a recommendation."""
    recommendation_id: uuid.UUID
    accepted: bool
    feedback_rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback_comment: Optional[str] = None


class RecommendationSetFeedback(SQLModel):
    """Feedback on a complete recommendation set."""
    recommendation_set_id: uuid.UUID
    overall_satisfaction: Optional[int] = Field(default=None, ge=1, le=5)
    feedback_comment: Optional[str] = None
    would_recommend_host: Optional[bool] = None
    host_insights_helpful: Optional[bool] = None
    individual_feedback: List[RecommendationFeedback] = Field(default_factory=list)


# Recommendation algorithm configuration
RECOMMENDATION_WEIGHTS = {
    "vector_similarity": 0.15,  # Vector embedding similarity weight
    "guest_preferences": 0.4,      # Guest group preferences weight
    "host_insights": 0.3,          # Host knowledge and tips weight
    "popularity": 0.1,             # Attraction popularity weight
    "seasonal_relevance": 0.1,     # Seasonal appropriateness weight
    "location_proximity": 0.1      # Distance/convenience weight
}

PREFERENCE_CATEGORIES = {
    "nature": ["hiking", "parks", "beaches", "wildlife", "scenic_views"],
    "culture": ["museums", "historic_sites", "architecture", "local_traditions"],
    "food": ["restaurants", "local_cuisine", "food_tours", "cooking_classes"],
    "adventure": ["sports", "outdoor_activities", "extreme_sports", "water_sports"],
    "relaxation": ["spas", "beaches", "parks", "quiet_spots"],
    "family": ["family_friendly", "children_activities", "educational"],
    "romantic": ["couples_activities", "romantic_dining", "scenic_spots"],
    "nightlife": ["bars", "clubs", "evening_entertainment"],
    "shopping": ["markets", "local_products", "souvenirs"],
    "seasonal": ["festivals", "seasonal_events", "weather_dependent"]
}

CROATIAN_SEASONAL_FACTORS = {
    "spring": {
        "months": [3, 4, 5],
        "highlights": ["wildflowers", "mild_weather", "cherry_blossoms", "asparagus_season"],
        "avoid": ["swimming", "outdoor_dining_evening"]
    },
    "summer": {
        "months": [6, 7, 8],
        "highlights": ["beaches", "swimming", "outdoor_dining", "festivals", "long_days"],
        "avoid": ["hot_hiking", "crowded_indoor_activities"]
    },
    "autumn": {
        "months": [9, 10, 11],
        "highlights": ["chestnuts", "wine_harvest", "comfortable_hiking", "beautiful_colors"],
        "avoid": ["swimming", "beach_activities"]
    },
    "winter": {
        "months": [12, 1, 2],
        "highlights": ["christmas_markets", "cozy_restaurants", "indoor_activities", "hot_springs"],
        "avoid": ["beach_activities", "long_outdoor_activities"]
    }
}


class RecommendationBatch(SQLModel):
    """Batch of recommendations with metadata."""
    recommendations: List[RecommendationResponse]
    total_count: int
    generated_at: datetime
    guest_group_id: Optional[uuid.UUID] = None
    request_context: Dict[str, Any] = Field(default_factory=dict)
    # Mirrors RecommendationSet / builder output (strings, lists, nested algorithm_weights).
    personalization_factors: Dict[str, Any] = Field(default_factory=dict)


class RecommendationAnalytics(SQLModel):
    """Recommendation analytics and performance metrics."""
    total_recommendations: int
    average_rating: float
    guest_satisfaction: float
    top_categories: List[str]
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    time_period: Dict[str, Any] = Field(default_factory=dict)
    host_contribution_impact: float = 0.0


class RecommendationFeedbackCreate(SQLModel):
    """Recommendation feedback creation model."""
    recommendation_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    feedback_text: Optional[str] = None
    visited: bool = False
    helpful_factors: List[str] = Field(default_factory=list)
    improvement_suggestions: Optional[str] = None


class RecommendationFeedbackResponse(RecommendationFeedbackCreate):
    """Recommendation feedback response model."""
    id: uuid.UUID
    guest_group_id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True 