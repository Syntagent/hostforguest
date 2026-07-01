"""
Location API endpoints for Google Maps integration.

Provides cached location data combining host-contributed attractions
and Google Places data for optimal guest experience.
"""

import secrets
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import (
    optional_host_session,
    require_host_or_maintenance_job_secret,
    require_maintenance_job_secret_only,
)
from app.api.v1.hosts import get_current_host
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.geocoding_service import GeocodingService
from app.services.host_offerings_for_guest import scrub_contact_from_text
from app.services.location_cache_service import LocationCacheService
from app.models.guest_group import GuestGroup
from app.models.host import Host

router = APIRouter(prefix="/locations", tags=["locations"])


def _is_maintenance_request(request: Request) -> bool:
    configured = (settings.maintenance_job_secret or "").strip()
    provided = (request.headers.get("X-Maintenance-Job-Secret") or "").strip()
    return bool(
        configured and provided and secrets.compare_digest(provided, configured)
    )


class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    formatted_address: str
    precision: str = Field(description="address | city | approximate")
    matched_query: str


class CachedLocationCoordinates(BaseModel):
    lat: float
    lng: float


class CachedLocationSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    coordinates: CachedLocationCoordinates
    source: str


class GuestGroupLocationsResponse(BaseModel):
    success: bool = True
    locations: List[Dict[str, Any]]
    count: int
    guest_group_id: str
    include_google_places: bool
    include_host_attractions: bool


class LocationDetailsResponse(BaseModel):
    success: bool = True
    location: Dict[str, Any]
    source: str


class CacheGooglePlacesResponse(BaseModel):
    success: bool = True
    message: str
    cached_at: str


class LocationCacheStatsResponse(BaseModel):
    success: bool = True
    cache_stats: Dict[str, Any]


class CacheClearResponse(BaseModel):
    success: bool = True
    message: str


class NearbyLocationItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    name: str
    city: Optional[str] = None
    description: Optional[str] = None
    attraction_type: Optional[str] = None


class NearbyHostLocation(BaseModel):
    city: Optional[str] = None
    coordinates: CachedLocationCoordinates


class NearbyLocationsResponse(BaseModel):
    success: bool = True
    locations: List[NearbyLocationItem]
    count: int
    host_location: NearbyHostLocation
    search_radius_km: float


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    address: str = Query(..., min_length=2, description="Street address or place name"),
    city: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
):
    """
    Resolve WGS84 coordinates from a Croatian address (Nominatim via GeocodingService).

    Public endpoint for onboarding and forms before session is established.
    """
    result = GeocodingService.geocode(address=address, city=city, county=county)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Could not verify this address. Add city and county, then try again.",
        )
    formatted = scrub_contact_from_text(result.matched_query)
    return GeocodeResponse(
        lat=result.latitude,
        lng=result.longitude,
        formatted_address=formatted,
        precision=result.precision,
        matched_query=formatted,
    )


@router.get("/guest-group/{guest_group_id}", response_model=GuestGroupLocationsResponse)
async def get_locations_for_guest_group(
    guest_group_id: UUID,
    include_google_places: bool = Query(True, description="Include Google Places data"),
    include_host_attractions: bool = Query(True, description="Include host-contributed attractions"),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cached locations for a guest group.
    
    Combines host-contributed attractions from the database with
    cached Google Places data for a comprehensive location experience.
    """
    try:
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.get_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=404,
                detail="Guest group not found",
            )

        cache_service = LocationCacheService(db)
        
        locations = await cache_service.get_cached_locations_for_guest_group(
            guest_group_id=guest_group_id,
            include_google_places=include_google_places,
            include_host_attractions=include_host_attractions
        )
        
        return GuestGroupLocationsResponse(
            success=True,
            locations=locations,
            count=len(locations),
            guest_group_id=str(guest_group_id),
            include_google_places=include_google_places,
            include_host_attractions=include_host_attractions,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve locations: {str(e)}"
        )


@router.get("/location/{location_id}", response_model=LocationDetailsResponse)
async def get_location_details(
    request: Request,
    location_id: str,
    source: str = Query(..., description="Source of location: 'database' or 'google_places'"),
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(optional_host_session),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """
    Get detailed information for a specific location.
    
    Args:
        location_id: Location ID (attraction ID or Google Place ID)
        source: Source of the location ("database" or "google_places")
    """
    try:
        attraction = None
        if source == "database":
            from app.services.attraction_service import AttractionService

            attraction_service = AttractionService(db)
            try:
                attraction_id = uuid.UUID(location_id)
            except ValueError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Location not found: {location_id}",
                )
            attraction = await attraction_service.get_attraction_by_id(attraction_id)
            if not attraction:
                raise HTTPException(
                    status_code=404,
                    detail=f"Location not found: {location_id}",
                )
            if not _is_maintenance_request(request):
                viewer_host_id = current_host.id if current_host else None
                if not attraction_service.is_attraction_visible(
                    attraction, viewer_host_id
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Location not found: {location_id}",
                    )

        cache_service = LocationCacheService(db)
        
        location_details = await cache_service.get_location_details(
            location_id=location_id,
            source=source
        )
        
        if not location_details:
            raise HTTPException(
                status_code=404,
                detail=f"Location not found: {location_id}"
            )

        if (
            source == "database"
            and not _is_maintenance_request(request)
            and (
                not current_host
                or attraction.created_by_host_id != current_host.id
            )
        ):
            for insider_key in (
                "hostTip",
                "host_story",
                "host_insider_info",
                "host_favorite_time",
                "host_recommended_duration",
                "contact_info",
            ):
                location_details.pop(insider_key, None)
            from app.services.host_offerings_for_guest import guest_safe_location_details

            location_details = guest_safe_location_details(location_details)
        
        return LocationDetailsResponse(
            success=True,
            location=location_details,
            source=source,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve location details: {str(e)}"
        )


@router.post("/cache/google-places", response_model=CacheGooglePlacesResponse)
async def cache_google_places_data(
    query: str,
    latitude: float,
    longitude: float,
    places_data: List[dict],
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_maintenance_job_secret_only),
):
    """
    Cache Google Places API data for future use.
    
    This endpoint allows the frontend to cache Google Places data
    that it retrieves directly from the Google Places API.
    """
    try:
        cache_service = LocationCacheService(db)
        
        await cache_service.cache_google_places_data(
            query=query,
            latitude=latitude,
            longitude=longitude,
            places_data=places_data
        )
        
        return CacheGooglePlacesResponse(
            success=True,
            message=f"Cached {len(places_data)} places for query: {query}",
            cached_at="now",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cache Google Places data: {str(e)}"
        )


@router.get("/cache/stats", response_model=LocationCacheStatsResponse)
async def get_cache_stats(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """Get cache statistics for monitoring."""
    try:
        cache_service = LocationCacheService(db)
        stats = cache_service.get_cache_stats()
        
        return LocationCacheStatsResponse(success=True, cache_stats=stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cache stats: {str(e)}"
        )


@router.delete("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_maintenance_job_secret_only),
):
    """Clear all cached location data."""
    try:
        cache_service = LocationCacheService(db)
        cache_service.clear_cache()
        
        return CacheClearResponse(
            success=True,
            message="Location cache cleared successfully",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/nearby/{host_id}", response_model=NearbyLocationsResponse)
async def get_nearby_locations(
    host_id: UUID,
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    limit: int = Query(20, description="Maximum number of locations to return"),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearby locations for a host's area.
    
    This endpoint provides locations near the host's property,
    useful for guests staying at that location.
    """
    try:
        if current_host.id != host_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

        # Get host information
        from sqlalchemy import select
        host_query = select(Host).where(Host.id == host_id)
        host_result = await db.execute(host_query)
        host = host_result.scalar_one_or_none()
        
        if not host:
            raise HTTPException(
                status_code=404,
                detail=f"Host not found: {host_id}"
            )
        
        lat = host.latitude
        lng = host.longitude
        if lat is None or lng is None:
            city_key = (host.city or "").strip().lower()
            city_coords = {
                "lovran": (45.2739, 14.2711),
                "opatija": (45.3271, 14.3062),
                "rijeka": (45.3271, 14.4422),
                "pula": (44.8666, 13.8496),
                "zagreb": (45.8150, 15.9819),
            }
            fallback = city_coords.get(city_key)
            if fallback:
                lat, lng = fallback
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Host location coordinates not available",
                )
        
        from app.services.attraction_service import AttractionService

        attraction_service = AttractionService(db)
        city_attractions = await attraction_service.get_attractions_by_city(
            host.city or "Lovran",
            limit=limit,
        )
        nearby_locations = [
            {
                "type": "attraction",
                "name": a.name,
                "city": a.city,
                "description": (a.short_description or a.description or "")[:200],
                "attraction_type": a.attraction_type,
            }
            for a in city_attractions
        ]
        
        return NearbyLocationsResponse(
            success=True,
            locations=[NearbyLocationItem.model_validate(loc) for loc in nearby_locations],
            count=len(nearby_locations),
            host_location=NearbyHostLocation(
                city=host.city,
                coordinates=CachedLocationCoordinates(lat=lat, lng=lng),
            ),
            search_radius_km=radius_km,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve nearby locations: {str(e)}"
        )
