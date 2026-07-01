"""
Pydantic models for host onboarding API.

Contains all request/response models and enums for the onboarding endpoints.
"""

from pydantic import BaseModel, Field, field_validator
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


class AccommodationSuggestionOption(BaseModel):
    """One selectable agent suggestion."""
    id: str
    label: str
    patch: AccommodationPatch


class AccommodationAgentMessageRequest(BaseModel):
    """Request for one turn of the Stay-tab onboarding agent."""
    message: str = Field(..., min_length=1, description="Host message or selected quick reply")
    focused_item_id: Optional[str] = Field(None, description="Checklist item currently being improved")
    checklist_state: List[ChecklistItemState] = Field(default_factory=list)
    accommodation_snapshot: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[AgentMessage] = Field(default_factory=list)


class AccommodationAgentMessageResponse(BaseModel):
    """Patch-safe conversational response for the Stay-tab onboarding agent."""
    success: bool
    reply: str
    quick_replies: List[str] = Field(default_factory=list)
    suggested_patch: AccommodationPatch = Field(default_factory=AccommodationPatch)
    suggestion_options: List[AccommodationSuggestionOption] = Field(default_factory=list)
    checklist_updates: List[ChecklistItemState] = Field(default_factory=list)
    next_focus_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

