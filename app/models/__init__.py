"""
Models package for HostForGuest.

Exports all database models and Pydantic schemas.
"""

# Import all models to ensure they are registered with SQLAlchemy

from .host import (
    Host,
    HostBase,
    HostCreate,
    HostUpdate,
    HostResponse,
    HostLogin,
    HostProfileCreate,
    HostProfileResponse
)

from .guest_group import (
    GuestGroup,
    AccessCode,
    GuestGroupStatus,
    AccessCodeStatus,
    GuestGroupBase,
    GuestGroupCreate,
    GuestGroupUpdate,
    GuestGroupResponse,
    GuestGroupGuestResponse,
    HostGuestExperienceResponse,
)

from .attraction import (
    Attraction,
    AttractionReview,
    ReviewModerationLog,
    SeasonalEvent,
    AttractionStatus,
    AttractionType,
    SeasonalAvailability,
    ReviewStatus,
    ReviewModerationAction,
    AttractionBase,
    AttractionCreate,
    AttractionUpdate,
    AttractionResponse,
    AttractionReviewCreate,
    AttractionReviewResponse,
    AttractionReviewUpdate,
    ReviewModerationRequest,
    ReviewModerationResponse,
    ReviewAnalytics,
    HostReviewStats,
    ReviewHelpfulnessVote,
    GuestReviewSubmission,
    ReviewSearchRequest,
    ReviewSearchResponse,
    SeasonalEventCreate,
    SeasonalEventResponse,
    HostContributionStats,
    HostContributionCreate,
    HostContributionResponse,
    AttractionSearchRequest,
    AttractionSearchResponse,
    CROATIAN_REGIONS,
    LOVRAN_AREA_ATTRACTIONS,
    CROATIAN_SEASONAL_EVENTS
)

from .itinerary import (
    Itinerary,
    DayPlan,
    ItineraryActivity,
    ActivityVote,
    ItineraryStatus,
    ActivityStatus,
    TransportMode,
    WeatherSuitability,
    ItineraryBase,
    ItineraryCreate,
    ItineraryResponse,
    ItineraryAssignFromTemplate,
    ItineraryWithDetails,
    ItineraryGuestResponse,
    ItineraryGuestWithDetails,
    DayPlanBase,
    DayPlanCreate,
    DayPlanResponse,
    DayPlanWithActivities,
    DayPlanGuestWithActivities,
    ActivityBase,
    ActivityCreate,
    ItineraryUpdate,
    RoutePointCreate,
    RoutePointReorder,
    RoutePointResponse,
    ActivityResponse,
    ActivityVoteCreate,
    ActivityVoteResponse,
    GoogleMapsDirectionsRequest,
    GoogleMapsDirectionsResponse,
    ItinerarySuggestionRequest,
    ItinerarySuggestionResponse,
    ItineraryMapViewResponse,
    GuestItineraryMapViewResponse,
    GuestItineraryMapViewLocation,
    GuestActivityCheckInResponse,
    ItineraryRoutePointsReorderResponse,
    ItineraryOptimizeRouteResponse,
    ItineraryMapViewLocation,
    ItineraryMapViewRoute,
    ItineraryMapViewCenter,
    ItineraryMapViewBounds,
    LLMItineraryDayPlan,
    LLMItineraryPlanResult,
)

from .recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationType,
    WeatherContext,
    RecommendationRequestAPI,
    CROATIAN_SEASONAL_FACTORS
)

from .settings import (
    HostSettings,
    SystemSettings,
    APIKeyTemplate,
    SettingsCategory,
    HostSettingsCreate,
    HostSettingsUpdate,
    HostSettingsResponse,
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyResponse,
    SystemSettingsResponse
)

from .content_source import (
    ContentSource,
    ContentSourceBase,
    ContentSourceCreate,
    ContentSourceResponse,
    CROATIAN_TOURISM_SOURCES,
    QUALITY_KEYWORDS
) 