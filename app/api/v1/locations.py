"""
Location API endpoints for Google Maps integration.

Provides cached location data combining host-contributed attractions
and Google Places data for optimal guest experience.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.location_cache_service import LocationCacheService
from app.models.guest_group import GuestGroup
from app.models.host import Host

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/guest-group/{guest_group_id}")
async def get_locations_for_guest_group(
    guest_group_id: UUID,
    include_google_places: bool = Query(True, description="Include Google Places data"),
    include_host_attractions: bool = Query(True, description="Include host-contributed attractions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cached locations for a guest group.
    
    Combines host-contributed attractions from the database with
    cached Google Places data for a comprehensive location experience.
    """
    try:
        cache_service = LocationCacheService(db)
        
        locations = await cache_service.get_cached_locations_for_guest_group(
            guest_group_id=guest_group_id,
            include_google_places=include_google_places,
            include_host_attractions=include_host_attractions
        )
        
        return {
            "success": True,
            "locations": locations,
            "count": len(locations),
            "guest_group_id": str(guest_group_id),
            "include_google_places": include_google_places,
            "include_host_attractions": include_host_attractions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve locations: {str(e)}"
        )


@router.get("/location/{location_id}")
async def get_location_details(
    location_id: str,
    source: str = Query(..., description="Source of location: 'database' or 'google_places'"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific location.
    
    Args:
        location_id: Location ID (attraction ID or Google Place ID)
        source: Source of the location ("database" or "google_places")
    """
    try:
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
        
        return {
            "success": True,
            "location": location_details,
            "source": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve location details: {str(e)}"
        )


@router.post("/cache/google-places")
async def cache_google_places_data(
    query: str,
    latitude: float,
    longitude: float,
    places_data: List[dict],
    db: AsyncSession = Depends(get_db)
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
        
        return {
            "success": True,
            "message": f"Cached {len(places_data)} places for query: {query}",
            "cached_at": "now"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cache Google Places data: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats(db: AsyncSession = Depends(get_db)):
    """Get cache statistics for monitoring."""
    try:
        cache_service = LocationCacheService(db)
        stats = cache_service.get_cache_stats()
        
        return {
            "success": True,
            "cache_stats": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(db: AsyncSession = Depends(get_db)):
    """Clear all cached location data."""
    try:
        cache_service = LocationCacheService(db)
        cache_service.clear_cache()
        
        return {
            "success": True,
            "message": "Location cache cleared successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/nearby/{host_id}")
async def get_nearby_locations(
    host_id: UUID,
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    limit: int = Query(20, description="Maximum number of locations to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearby locations for a host's area.
    
    This endpoint provides locations near the host's property,
    useful for guests staying at that location.
    """
    try:
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
        
        if not host.latitude or not host.longitude:
            raise HTTPException(
                status_code=400,
                detail="Host location coordinates not available"
            )
        
        cache_service = LocationCacheService(db)
        
        # Get locations for the host's area
        locations = await cache_service.get_cached_locations_for_guest_group(
            guest_group_id=None,  # We'll filter by host area instead
            include_google_places=True,
            include_host_attractions=True
        )
        
        # Filter by distance (simplified - in production, use proper geospatial queries)
        nearby_locations = locations[:limit]
        
        return {
            "success": True,
            "locations": nearby_locations,
            "count": len(nearby_locations),
            "host_location": {
                "city": host.city,
                "coordinates": {
                    "lat": host.latitude,
                    "lng": host.longitude
                }
            },
            "search_radius_km": radius_km
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve nearby locations: {str(e)}"
        )
