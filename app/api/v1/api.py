"""
Main API router for HostForGuest v1.

Includes all API endpoints for the Croatian tourist host platform.
"""

from fastapi import APIRouter

from app.api.v1 import (
    hosts,
    maintenance,
    adaptation,
    guest_groups,
    attractions,
    recommendations,
    settings,
    itineraries,
    host_onboarding,
    realtime_data,
    locations,
    vector,
    partners,
    cleaning,
    content_generation,
    analytics,
    communications,
    reviews,
    bookings,
    subscriptions,
    bi,
    audit,
    performance,
    channel_integrations,
    channel_webhooks,
)

api_router = APIRouter()

# Include all endpoint modules
api_router.include_router(hosts.router, prefix="/hosts", tags=["hosts"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(adaptation.router, prefix="/adaptation", tags=["adaptation"])
api_router.include_router(guest_groups.router, prefix="/guest-groups", tags=["guest-groups"])
api_router.include_router(attractions.router, prefix="/attractions", tags=["attractions"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(itineraries.router, prefix="/itineraries", tags=["itineraries"])
api_router.include_router(host_onboarding.router, prefix="/onboarding", tags=["host-onboarding"])

# Real-time data endpoints
api_router.include_router(realtime_data.router, prefix="/realtime", tags=["real-time-data"])

# Location endpoints (Google Maps integration)
api_router.include_router(locations.router)

# Vector search endpoints
api_router.include_router(vector.router, prefix="/vector", tags=["vector-search"])

# Partner endpoints
api_router.include_router(partners.router, prefix="/partners", tags=["partners"])
api_router.include_router(cleaning.router, prefix="/cleaning", tags=["cleaning"])

# Content generation endpoints
api_router.include_router(content_generation.router, prefix="/content-generation", tags=["content-generation"])

# Analytics endpoints
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Communication endpoints
api_router.include_router(communications.router, prefix="/communications", tags=["communications"])

# Review endpoints
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])

# Booking endpoints
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])

# Subscription endpoints
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])

# Business Intelligence endpoints
api_router.include_router(bi.router, prefix="/bi", tags=["business-intelligence"])

# Audit logging endpoints
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])

# Performance optimization endpoints
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])

# OTA / channel integrations (Booking.com)
api_router.include_router(
    channel_integrations.router,
    prefix="/channel-integrations",
    tags=["channel-integrations"],
)
api_router.include_router(
    channel_webhooks.router,
    prefix="/channel-webhooks",
    tags=["channel-webhooks"],
)