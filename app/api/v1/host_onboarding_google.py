"""
Google Places integration for host onboarding.

Handles Google Places API calls for location verification and nearby attractions.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
import httpx

from app.api.v1.host_onboarding_models import (
    GooglePlacesResponse,
    GooglePlaceInfo,
    GooglePlaceLocation
)

logger = logging.getLogger(__name__)


GOOGLE_PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


async def _get_google_places_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    status_value = data.get("status")
    if status_value not in (None, "OK", "ZERO_RESULTS"):
        raise RuntimeError(data.get("error_message") or f"Google Places returned {status_value}")
    return data


async def get_google_places_info(place_name: str) -> GooglePlacesResponse:
    """
    Get Google Places information for a place name.
    
    Args:
        place_name: Name of the place to search
        
    Returns:
        GooglePlacesResponse with place information
    """
    try:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            return GooglePlacesResponse(
                success=False,
                error="Google Places API not configured"
            )

        places_result = await _get_google_places_json(
            GOOGLE_PLACES_TEXTSEARCH_URL,
            {"query": place_name, "language": "en", "key": api_key},
        )
        
        if not places_result.get('results'):
            return GooglePlacesResponse(
                success=False,
                error="Place not found"
            )
        
        # Get first result
        place = places_result['results'][0]
        geometry = place.get('geometry', {})
        location = geometry.get('location', {})
        
        place_info = GooglePlaceInfo(
            place_id=place.get('place_id'),
            name=place.get('name'),
            rating=place.get('rating'),
            types=place.get('types', []),
            vicinity=place.get('vicinity'),
            location=GooglePlaceLocation(
                lat=location.get('lat'),
                lng=location.get('lng')
            )
        )
        
        # Get nearby attractions (next 5 results)
        nearby_attractions = [
            {
                "name": nearby.get('name'),
                "rating": nearby.get('rating'),
                "types": nearby.get('types', []),
                "place_id": nearby.get('place_id'),
                "vicinity": nearby.get('vicinity')
            }
            for nearby in places_result['results'][1:6]
        ]
        
        return GooglePlacesResponse(
            success=True,
            place_info=place_info,
            nearby_attractions=nearby_attractions
        )
        
    except Exception as e:
        logger.error(f"Google Places API error: {e}")
        return GooglePlacesResponse(
            success=False,
            error=f"Failed to fetch location information: {str(e)}"
        )


async def get_nearby_google_places(
    lat: float,
    lng: float,
    radius: int = 5000,
    place_type: str = "tourist_attraction"
) -> Dict[str, Any]:
    """
    Get nearby attractions from Google Places API.
    
    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        radius: Search radius in meters
        place_type: Type of place to search for
        
    Returns:
        Dictionary with nearby places information
    """
    try:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Places API not configured"
            )

        nearby_results = await _get_google_places_json(
            GOOGLE_PLACES_NEARBY_URL,
            {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "language": "en",
                "key": api_key,
            },
        )
        
        if not nearby_results.get('results'):
            return {
                "success": False,
                "error": "No nearby places found",
                "nearby_places": []
            }
        
        # Process and return nearby places
        nearby_places = []
        for place in nearby_results['results'][:10]:  # Limit to top 10
            geometry = place.get('geometry', {})
            location = geometry.get('location', {})
            
            nearby_places.append({
                "name": place.get('name'),
                "place_id": place.get('place_id'),
                "rating": place.get('rating'),
                "types": place.get('types', []),
                "vicinity": place.get('vicinity'),
                "location": {
                    "lat": location.get('lat'),
                    "lng": location.get('lng')
                },
                "price_level": place.get('price_level'),
                "photos": [
                    {
                        "photo_reference": photo.get('photo_reference'),
                        "width": photo.get('width'),
                        "height": photo.get('height')
                    }
                    for photo in place.get('photos', [])[:1]  # Limit to 1 photo per place
                ]
            })
        
        return {
            "success": True,
            "nearby_places": nearby_places,
            "total_found": len(nearby_places),
            "search_location": {"lat": lat, "lng": lng},
            "search_radius": radius
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google Places nearby search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search nearby places: {str(e)}"
        )

