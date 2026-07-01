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
    AttractionAnalyticsFeedbackItem,
    AttractionAnalyticsResponse,
    AttractionPublicResponse,
    AttractionReviewCreate,
    AttractionReviewResponse,
    AttractionReviewPublicResponse,
    AttractionReviewGuestSubmitResponse,
    AttractionReviewUpdate,
    ReviewModerationRequest,
    ReviewModerationResponse,
    ReviewAnalytics,
    HostReviewStats,
    ReviewHelpfulnessVote,
    ReviewHelpfulnessVoteResponse,
    GuestReviewSubmission,
    ReviewSearchRequest,
    ReviewSearchResponse,
    SeasonalEventCreate,
    SeasonalEventResponse,
    SeasonalEventPublicResponse,
    HostContributionStats,
    HostContributionCreate,
    HostContributionResponse,
    HostContributionPublicResponse,
    AttractionSearchRequest,
    AttractionSearchResponse,
    AttractionEnrichRequest,
    AttractionEnrichResponse,
    AttractionEnrichResultItem,
    AttractionEnrichmentStatusResponse,
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
    DayPlanGuestResponse,
    DayPlanGuestWithActivities,
    ActivityBase,
    ActivityCreate,
    ActivityUpdate,
    ItineraryUpdate,
    RoutePointCreate,
    RoutePointReorder,
    RoutePointResponse,
    ActivityGuestResponse,
    ActivityResponse,
    ActivityVoteCreate,
    ActivityVoteResponse,
    ActivityVoteGuestResponse,
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