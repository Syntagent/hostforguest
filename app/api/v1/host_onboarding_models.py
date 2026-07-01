"""
Pydantic models for host onboarding API.

Contains all request/response models and enums for the onboarding endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


# Enums for better type safety
class PropertyType(str, Enum):
    APARTMENT = "apartment"
    VILLA = "villa"
    HOUSE = "house"
    ROOM = "room"
    STUDIO = "studio"


class CroatianRegion(str, Enum):
    ISTRIA = "Istria"
    DALMATIA = "Dalmatia"
    KVARNER = "Kvarner"
    CENTRAL_CROATIA = "Central Croatia"
    SLAVONIA = "Slavonia"


class LocalExperience(str, Enum):
    LESS_THAN_1_YEAR = "less_than_1_year"
    ONE_TO_5_YEARS = "1_to_5_years"
    FIVE_TO_15_YEARS = "5_to_15_years"
    FIFTEEN_PLUS_YEARS = "15_plus_years"
    BORN_HERE = "born_here"


class KnowledgeLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class AttractionCategory(str, Enum):
    CULINARY = "culinary"
    CULTURAL = "cultural"
    NATURE = "nature"
    BEACH = "beach"
    ADVENTURE = "adventure"
    EXPERIENCE = "experience"


class AuthenticityLevel(str, Enum):
    HIGH = "high"
    VERY_HIGH = "very_high"


class CostEstimate(str, Enum):
    FREE = "free"
    LOW = "low"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"


class BestTime(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    MORNING_OR_SUNSET = "morning_or_sunset"
    ANYTIME = "anytime"


class Difficulty(str, Enum):
    EASY = "easy"
    MODERATE = "moderate"
    CHALLENGING = "challenging"


# Enhanced request/response models
class GooglePlaceLocation(BaseModel):
    """Google Places location data with validation"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    lng: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class GooglePlaceInfo(BaseModel):
    """Google Places information"""
    place_id: str
    name: str
    rating: Optional[float] = None
    types: List[str] = Field(default_factory=list)
    vicinity: Optional[str] = None
    location: GooglePlaceLocation


class AttractionSuggestion(BaseModel):
    """AI-suggested attraction with metadata"""
    name: str
    description: str
    category: str
    cost_estimate: str
    authenticity_level: str
    best_time: str
    difficulty: Optional[str] = None
    data_source: Optional[str] = None
    enhanced: bool = False
    relevance_score: float = 0.5


class EnhancedAttractionSuggestionsRequest(BaseModel):
    """Enhanced request for attraction suggestions with full context"""
    city: str = Field(..., description="Host's city")
    address: Optional[str] = Field(None, description="Property address")
    region: Optional[CroatianRegion] = Field(None, description="Croatian region")
    property_name: Optional[str] = Field(None, description="Property/business name")
    property_type: Optional[str] = Field(None, description="Type of accommodation")
    coordinates: Optional[GooglePlaceLocation] = Field(None, description="GPS coordinates")
    interests: List[str] = Field(default_factory=list, description="Host interests/specialties")
    languages: List[str] = Field(default_factory=list, description="Languages spoken by the host")
    local_experience: Optional[LocalExperience] = Field(None, description="Local experience level")
    knowledge_level: KnowledgeLevel = Field(default=KnowledgeLevel.EXPERT, description="Knowledge level")
    location_story: Optional[str] = Field(None, description="Host's location story")
    preferred_guests: List[str] = Field(default_factory=list, description="Preferred guest types")


class AttractionSuggestionsResponse(BaseModel):
    """AI-generated attraction suggestions response"""
    success: bool
    attractions: List[Dict[str, Any]]
    categories: Dict[str, List[Dict[str, Any]]]
    reasoning: str
    ui_components: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GooglePlacePhoto(BaseModel):
    """Google Places photo metadata."""

    photo_reference: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class GooglePlaceNearbyItem(BaseModel):
    """Single nearby place from Google Places nearby search."""

    name: Optional[str] = None
    place_id: Optional[str] = None
    rating: Optional[float] = None
    types: List[str] = Field(default_factory=list)
    vicinity: Optional[str] = None
    location: Optional[GooglePlaceLocation] = None
    price_level: Optional[int] = None
    photos: List[GooglePlacePhoto] = Field(default_factory=list)


class NearbyGooglePlacesResponse(BaseModel):
    """GET /onboarding/google-places/nearby response."""

    success: bool
    nearby_places: List[GooglePlaceNearbyItem] = Field(default_factory=list)
    total_found: Optional[int] = None
    search_location: Optional[GooglePlaceLocation] = None
    search_radius: Optional[int] = None
    error: Optional[str] = None


class GooglePlacesResponse(BaseModel):
    """Google Places API response"""
    success: bool
    place_info: Optional[GooglePlaceInfo] = None
    nearby_attractions: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if failed")


class OnboardingBasicInfo(BaseModel):
    """Basic information for AI-powered profile generation"""
    first_name: str = Field(..., description="Host's first name")
    last_name: str = Field(..., description="Host's last name")
    business_name: str = Field(..., description="Property/business name")
    city: str = Field(..., description="Host's city")
    address: str = Field(..., description="Property address")
    region: Optional[str] = Field(default="Istria", description="Croatian region")
    business_type: str = Field(default="apartment", description="Type of accommodation")
    max_group_size: int = Field(default=4, ge=1, le=20, description="Maximum guests")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    local_experience: str = Field(..., description="Host's local experience level")
    location_story: str = Field(default="", description="Host's personal story about the location")
    specialties: List[str] = Field(default_factory=list, description="Host's specialties and expertise")
    preferred_guests: List[str] = Field(default_factory=list, description="Preferred guest types")
    languages: List[str] = Field(default=["hr", "en"], description="Languages spoken")
    hosting_experience: int = Field(default=0, ge=0, description="Years of hosting experience")
    interests: List[str] = Field(default_factory=list, description="Host's interests and expertise")
    profile_style: str = Field(default="warm_authentic", description="Preferred profile style")
    target_guests: List[str] = Field(default=["families", "couples"], description="Target guest types")


class ProfileSuggestionsResponse(BaseModel):
    """AI-generated profile suggestions response"""
    success: bool
    suggestions: Dict[str, List[str]]
    reasoning: str
    alternatives: List[str]
    ui_components: Dict[str, Any]


class WelcomeMessageResponse(BaseModel):
    """AI-generated welcome message suggestions"""
    success: bool
    welcome_messages: Dict[str, List[str]]
    tips: List[str]
    ui_components: Dict[str, Any]


class ProfileValidationResponse(BaseModel):
    """Profile validation and enhancement response"""
    success: bool
    validation: Dict[str, Any]
    enhancements: List[Dict[str, Any]]
    completeness_score: float
    ui_components: Dict[str, Any]


class OnboardingStepResponse(BaseModel):
    """Multi-step onboarding response with UI components"""
    step: int
    total_steps: int
    step_name: str
    content: Dict[str, Any]
    ui_components: Dict[str, Any]
    next_step_available: bool


class EditSuggestionRequest(BaseModel):
    """Request to edit or co-write a profile suggestion"""
    suggestion_id: str = Field(..., description="ID of the suggestion to edit")
    category: str = Field(..., description="Category (business_description, welcome_message, etc.)")
    original_text: str = Field(..., description="Original AI suggestion")
    user_edit: str = Field(..., description="User's edited version")
    is_collaborative: bool = Field(default=False, description="Whether to use AI collaboration")
    collaboration_prompt: Optional[str] = Field(None, description="Specific instructions for AI collaboration")


class CoWriteRequest(BaseModel):
    """Request to co-write content with AI assistance"""
    category: str = Field(..., description="Content category")
    user_input: str = Field(..., description="User's initial input or partial content")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for AI")
    style_preference: str = Field(default="warm_authentic", description="Preferred writing style")


class EditSuggestionResponse(BaseModel):
    """POST /onboarding/edit-suggestion response."""

    success: bool
    original: str
    user_edit: str
    final_suggestion: str
    collaboration_used: bool
    ai_improved: Optional[str] = None


class CoWriteResponse(BaseModel):
    """POST /onboarding/co-write response."""

    success: bool
    user_input: str
    co_written: str
    category: str


class LocationAnalysisSection(BaseModel):
    """Location analysis subsection for analyze-location."""

    city: Optional[str] = None
    region: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None
    local_experience_score: float = 0.0
    knowledge_level: Optional[str] = None


class MarketPotentialSection(BaseModel):
    """Market potential subsection for analyze-location."""

    guest_alignment: Optional[Dict[str, Any]] = None
    interest_diversity: int = 0
    location_story_quality: Optional[Dict[str, Any]] = None
    authenticity_indicators: List[Any] = Field(default_factory=list)


class LocationRecommendationsSection(BaseModel):
    """Recommendations subsection for analyze-location."""

    suggested_improvements: List[str] = Field(default_factory=list)
    marketing_angles: List[str] = Field(default_factory=list)
    competitive_advantages: List[str] = Field(default_factory=list)


class LocationAnalysisMetadata(BaseModel):
    """Metadata subsection for analyze-location."""

    analysis_timestamp: Optional[str] = None
    data_sources: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class LocationPotentialAnalysis(BaseModel):
    """Nested analysis payload for analyze-location."""

    location_analysis: LocationAnalysisSection = Field(default_factory=LocationAnalysisSection)
    market_potential: MarketPotentialSection = Field(default_factory=MarketPotentialSection)
    recommendations: LocationRecommendationsSection = Field(default_factory=LocationRecommendationsSection)
    metadata: LocationAnalysisMetadata = Field(default_factory=LocationAnalysisMetadata)


class AnalyzeLocationResponse(BaseModel):
    """POST /onboarding/analyze-location response."""

    success: bool
    analysis: LocationPotentialAnalysis
    insights: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class OnboardingProgressStepItem(BaseModel):
    """Single onboarding progress step."""

    name: str
    required: bool
    completed: bool


class OnboardingProgressResponse(BaseModel):
    """GET /onboarding/progress/{host_id} response."""

    host_id: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: Optional[int] = None
    completion_percentage: Optional[float] = None
    steps: List[OnboardingProgressStepItem] = Field(default_factory=list)
    next_step: Optional[str] = None
    error: Optional[str] = None


class OnboardingTrackStepResponse(BaseModel):
    """POST /onboarding/track-step response."""

    success: bool
    message: str


class OnboardingSuccessMetricsResponse(BaseModel):
    """GET /onboarding/success-metrics/{host_id} response."""

    host_id: Optional[str] = None
    time_to_complete_hours: Optional[float] = None
    profile_completeness_score: Optional[int] = None
    onboarding_completed: Optional[bool] = None
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    error: Optional[str] = None


class OnboardingDropOffPoint(BaseModel):
    """Drop-off point in admin onboarding analytics."""

    step: str
    drop_off_rate: float


class OnboardingAdminAnalyticsResponse(BaseModel):
    """GET /onboarding/analytics admin response."""

    period_days: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_hosts: Optional[int] = None
    completed_onboarding: Optional[int] = None
    completion_rate: Optional[float] = None
    average_time_to_complete_hours: Optional[float] = None
    drop_off_points: List[OnboardingDropOffPoint] = Field(default_factory=list)
    error: Optional[str] = None


class AttractionSuggestionsRequest(BaseModel):
    """Request for generating attraction suggestions"""
    city: Optional[str] = Field(None, description="City name")
    address: Optional[str] = Field(None, description="Address or location")
    region: Optional[str] = Field(None, description="Region name")
    interests: List[str] = Field(default_factory=list, description="Host interests")
    knowledge_level: str = Field(default="expert", description="Local knowledge level")


class AIEnhancementResponse(BaseModel):
    """Response for AI accommodation enhancement"""
    success: bool
    enhancement_type: str = "comprehensive"
    enhanced_content: Dict[str, Any] = Field(default_factory=dict)
    original_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None


class ChecklistItemState(BaseModel):
    """Client-visible state for an accommodation onboarding checklist item."""
    id: str
    status: Literal["missing", "in_progress", "draft", "done", "skipped"] = "missing"
    label: Optional[str] = None
    notes: Optional[str] = None


class AgentMessage(BaseModel):
    """Conversation message exchanged with the accommodation agent."""
    role: Literal["assistant", "user", "system"]
    content: str


class AccommodationPatch(BaseModel):
    """Allowed profile patch fields emitted by the accommodation agent."""
    property_name: Optional[str] = None
    property_type: Optional[str] = None
    max_guests: Optional[int] = None
    number_of_rooms: Optional[int] = None
    city: Optional[str] = None
    county: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_story: Optional[str] = None
    amenities: Optional[List[str]] = None
    services_offered: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    welcome_message: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    property_rules: Optional[Dict[str, Any]] = None


class AccommodationAgentContext(BaseModel):
    """UI/agent state carried inside accommodation_snapshot._agent_context."""
    model_config = ConfigDict(extra="allow")

    page_goal: Optional[str] = None
    allowed_actions: Optional[List[str]] = None
    safety_rules: Optional[List[str]] = None
    pending_patch: Optional[AccommodationPatch] = None
    active_item_id: Optional[str] = None
    checklist_state: Optional[List[ChecklistItemState]] = None
    source: Optional[str] = None
    option_field: Optional[str] = None
    visible_options: Optional[List[str]] = None
    selected_options: Optional[List[str]] = None
    interpretation_goal: Optional[str] = None


class AccommodationSnapshot(AccommodationPatch):
    """Stay-tab profile snapshot sent with accommodation agent and voice requests."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    propertyRulesComplete: Optional[bool] = None
    agent_context: Optional[AccommodationAgentContext] = Field(
        default=None,
        alias="_agent_context",
        validation_alias="_agent_context",
        serialization_alias="_agent_context",
    )

    def to_agent_dict(self) -> Dict[str, Any]:
        """Serialize for the onboarding service (includes _agent_context alias)."""
        return self.model_dump(by_alias=True, exclude_none=True)


class AccommodationSuggestionOption(BaseModel):
    """One selectable agent suggestion."""
    id: str
    label: str
    patch: AccommodationPatch


class AccommodationAgentAction(BaseModel):
    """A safe page-domain action requested by the accommodation agent."""
    action: Literal["update_draft", "replace_draft", "move_focus", "open_fields", "ask_followup", "no_op"]
    target_item_id: Optional[str] = None
    field: Optional[str] = None
    patch: Optional[AccommodationPatch] = None
    reason: Optional[str] = None


class AccommodationAgentMessageRequest(BaseModel):
    """Request for one turn of the Stay-tab onboarding agent."""
    message: str = Field(..., min_length=1, description="Host message or selected quick reply")
    focused_item_id: Optional[str] = Field(None, description="Checklist item currently being improved")
    checklist_state: List[ChecklistItemState] = Field(default_factory=list)
    accommodation_snapshot: AccommodationSnapshot = Field(default_factory=AccommodationSnapshot)
    conversation_history: List[AgentMessage] = Field(default_factory=list)


class AccommodationAgentMessageResponse(BaseModel):
    """Patch-safe conversational response for the Stay-tab onboarding agent."""
    success: bool
    reply: str
    quick_replies: List[str] = Field(default_factory=list)
    suggested_patch: AccommodationPatch = Field(default_factory=AccommodationPatch)
    suggestion_options: List[AccommodationSuggestionOption] = Field(default_factory=list)
    actions: List[AccommodationAgentAction] = Field(default_factory=list)
    checklist_updates: List[ChecklistItemState] = Field(default_factory=list)
    next_focus_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompleteOnboardingResponse(BaseModel):
    """POST /onboarding/complete-onboarding success envelope."""

    success: bool
    message: str
    host_id: str
    guest_access_code: str
    attractions_generated: int
    profile_updated: bool
    guest_access_url: str
    next_steps: List[str]

