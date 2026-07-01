"""
Location caching service for Google Maps integration.

Provides intelligent caching of Google Places data and integration
with the existing attraction database for optimal performance.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.attraction import Attraction, AttractionStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.google_maps_utils import google_maps_link, place_photo_url

logger = logging.getLogger(__name__)

_PRICE_LEVEL_LABELS = {0: "Free", 1: "€", 2: "€€", 3: "€€€", 4: "€€€€"}


class LocationCacheService:
    """
    Service for caching and managing location data from Google Places API.
    
    Integrates with the existing attraction database to provide
    a seamless experience between host-contributed attractions and
    Google Places data.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=24)  # Cache for 24 hours
    
    async def get_cached_locations_for_guest_group(
        self, 
        guest_group_id: UUID,
        include_google_places: bool = True,
        include_host_attractions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get cached locations for a guest group, combining database attractions
        and Google Places data.
        
        Args:
            guest_group_id: Guest group UUID
            include_google_places: Whether to include Google Places data
            include_host_attractions: Whether to include host-contributed attractions
            
        Returns:
            List of location objects with coordinates and metadata
        """
        locations = []
        
        guest_group_result = await self.db.execute(
            select(GuestGroup).where(GuestGroup.id == guest_group_id)
        )
        guest_group = guest_group_result.scalar_one_or_none()

        if not guest_group:
            return locations

        host_result = await self.db.execute(
            select(Host).where(Host.id == guest_group.host_id)
        )
        host = host_result.scalar_one_or_none()
        if not host:
            return locations
        
        # 1. Get host-contributed attractions from database
        if include_host_attractions:
            db_attractions = await self._get_host_attractions(host.id)
            locations.extend(db_attractions)
        
        # 2. Get Google Places data (cached)
        if include_google_places:
            google_places = await self._get_cached_google_places(
                host.city, 
                host.latitude, 
                host.longitude
            )
            locations.extend(google_places)
        
        # 3. Remove duplicates and sort by relevance
        unique_locations = self._deduplicate_locations(locations)
        sorted_locations = self._sort_by_relevance(unique_locations, guest_group)
        
        return sorted_locations
    
    async def _get_host_attractions(self, host_id: UUID) -> List[Dict[str, Any]]:
        """Get attractions contributed by the host from database."""
        query = select(Attraction).where(
            and_(
                Attraction.created_by_host_id == host_id,
                Attraction.status == AttractionStatus.APPROVED,
                Attraction.latitude.is_not(None),
                Attraction.longitude.is_not(None)
            )
        )
        
        result = await self.db.execute(query)
        attractions = result.scalars().all()
        
        return [
            {
                "id": str(attraction.id),
                "title": attraction.name,
                "description": attraction.description,
                "category": attraction.attraction_type,
                "location": attraction.city,
                "rating": attraction.google_rating or attraction.guest_rating or 4.0,
                "price": self._price_label(attraction),
                "coordinates": {
                    "lat": attraction.latitude,
                    "lng": attraction.longitude
                },
                "hostTip": attraction.host_personal_tip,
                "weatherDependent": self._is_weather_dependent(attraction),
                "source": "database",
                "attraction_id": str(attraction.id),
                "image": attraction.featured_image_url,
                "opening_hours": attraction.opening_hours,
                "contact_info": attraction.contact_info,
                "difficulty_level": attraction.difficulty_level,
                "duration_hours": attraction.duration_hours,
                "accessibility_info": attraction.accessibility_info,
                "seasonal_availability": attraction.seasonal_availability,
                "best_months": attraction.best_months,
                "google_place_id": attraction.google_place_id,
                "google_photos": list(attraction.google_photos or []),
                "google_website": attraction.google_website,
                "google_phone": attraction.google_phone,
                "google_maps_url": google_maps_link(
                    attraction.latitude, attraction.longitude, name=attraction.name
                ),
            }
            for attraction in attractions
        ]

    @staticmethod
    def _price_label(attraction: Attraction) -> str:
        if attraction.admission_fee:
            return attraction.admission_fee
        level = attraction.google_price_level
        if level is not None:
            return _PRICE_LEVEL_LABELS.get(level, "€€")
        return "Free"
    
    async def _get_cached_google_places(
        self, 
        city: str, 
        latitude: Optional[float], 
        longitude: Optional[float]
    ) -> List[Dict[str, Any]]:
        """
        Get cached Google Places data for the host's city (24h in-memory TTL).
        """
        lat = latitude if latitude is not None else 45.1
        lng = longitude if longitude is not None else 14.27
        cache_key = f"google_places_{city.lower()}_{round(lat, 3)}_{round(lng, 3)}"
        
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.now() - cached_data["cached_at"] < self._cache_ttl:
                return cached_data["locations"]
        
        places = await self._fetch_nearby_google_places(city, lat, lng)
        
        self._cache[cache_key] = {
            "locations": places,
            "cached_at": datetime.now()
        }
        
        return places

    async def _fetch_nearby_google_places(
        self,
        city: str,
        latitude: float,
        longitude: float,
    ) -> List[Dict[str, Any]]:
        """Call Google Places nearby search once per cache window."""
        api_key = (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
        if not api_key:
            logger.debug("GOOGLE_MAPS_API_KEY missing; skipping nearby places fetch")
            return []

        try:
            import googlemaps

            client = googlemaps.Client(key=api_key)

            def _search():
                return client.places_nearby(
                    location=(latitude, longitude),
                    radius=5000,
                    language="en",
                )

            result = await asyncio.to_thread(_search)
        except Exception as exc:
            logger.warning("Nearby Google Places failed for %s: %s", city, exc)
            return []

        formatted: List[Dict[str, Any]] = []
        for place in (result or {}).get("results") or []:
            loc = (place.get("geometry") or {}).get("location") or {}
            lat = loc.get("lat")
            lng = loc.get("lng")
            if lat is None or lng is None:
                continue
            photos = place.get("photos") or []
            photo_url = None
            if photos and photos[0].get("photo_reference"):
                photo_url = place_photo_url(photos[0]["photo_reference"], maxwidth=400)
            price_level = place.get("price_level")
            formatted.append(
                {
                    "id": f"google_{place.get('place_id', '')}",
                    "title": place.get("name") or "Place",
                    "description": place.get("vicinity") or city,
                    "category": (place.get("types") or ["point_of_interest"])[0],
                    "location": city,
                    "rating": place.get("rating") or 4.0,
                    "price": _PRICE_LEVEL_LABELS.get(price_level, "€€") if price_level is not None else "€€",
                    "coordinates": {"lat": lat, "lng": lng},
                    "hostTip": None,
                    "weatherDependent": False,
                    "source": "google_places",
                    "place_id": place.get("place_id"),
                    "opening_hours": {"open_now": (place.get("opening_hours") or {}).get("open_now")},
                    "contact_info": {},
                    "website": None,
                    "image": photo_url,
                    "google_maps_url": google_maps_link(lat, lng, name=place.get("name")),
                }
            )
        return formatted[:20]
    
    def _is_weather_dependent(self, attraction: Attraction) -> bool:
        """Determine if an attraction is weather dependent."""
        outdoor_tags = ["outdoor", "hiking", "beach", "park", "garden"]
        return any(tag in attraction.category_tags for tag in outdoor_tags)
    
    def _deduplicate_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate locations based on coordinates."""
        seen_coordinates = set()
        unique_locations = []
        
        for location in locations:
            coords = (location["coordinates"]["lat"], location["coordinates"]["lng"])
            if coords not in seen_coordinates:
                seen_coordinates.add(coords)
                unique_locations.append(location)
        
        return unique_locations
    
    def _sort_by_relevance(
        self, 
        locations: List[Dict[str, Any]], 
        guest_group: GuestGroup
    ) -> List[Dict[str, Any]]:
        """Sort locations by relevance to the guest group."""
        # In a real implementation, this would use guest preferences
        # For now, prioritize database attractions over Google Places
        return sorted(locations, key=lambda x: x.get("source") == "database", reverse=True)
    
    async def cache_google_places_data(
        self, 
        query: str, 
        latitude: float, 
        longitude: float,
        places_data: List[Dict[str, Any]]
    ) -> None:
        """
        Cache Google Places API data for future use.
        
        Args:
            query: Search query used
            latitude: Center latitude
            longitude: Center longitude
            places_data: Raw Google Places API response
        """
        cache_key = f"google_places_{query}_{latitude}_{longitude}"
        
        self._cache[cache_key] = {
            "locations": places_data,
            "cached_at": datetime.now(),
            "query": query,
            "coordinates": {"lat": latitude, "lng": longitude}
        }
        
        logger.info(f"Cached {len(places_data)} places for query: {query}")
    
    async def get_location_details(
        self, 
        location_id: str, 
        source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific location.
        
        Args:
            location_id: Location ID (attraction ID or Google Place ID)
            source: Source of the location ("database" or "google_places")
            
        Returns:
            Detailed location information or None if not found
        """
        if source == "database":
            return await self._get_attraction_details(location_id)
        elif source == "google_places":
            return await self._get_google_place_details(location_id)
        
        return None
    
    async def _get_attraction_details(self, attraction_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed attraction information from database."""
        query = select(Attraction).where(Attraction.id == attraction_id)
        result = await self.db.execute(query)
        attraction = result.scalar_one_or_none()
        
        if not attraction:
            return None
        
        return {
            "id": str(attraction.id),
            "title": attraction.name,
            "description": attraction.description,
            "category": attraction.attraction_type,
            "location": attraction.city,
            "rating": attraction.guest_rating or 4.0,
            "price": attraction.admission_fee or "Free",
            "coordinates": {
                "lat": attraction.latitude,
                "lng": attraction.longitude
            },
            "hostTip": attraction.host_personal_tip,
            "weatherDependent": self._is_weather_dependent(attraction),
            "source": "database",
            "image": attraction.featured_image_url,
            "opening_hours": attraction.opening_hours,
            "contact_info": attraction.contact_info,
            "difficulty_level": attraction.difficulty_level,
            "duration_hours": attraction.duration_hours,
            "accessibility_info": attraction.accessibility_info,
            "seasonal_availability": attraction.seasonal_availability,
            "best_months": attraction.best_months,
            "host_story": attraction.host_story,
            "host_insider_info": attraction.host_insider_info,
            "host_favorite_time": attraction.host_favorite_time,
            "host_recommended_duration": attraction.host_recommended_duration
        }
    
    async def _get_google_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed Google Place information."""
        # In a real implementation, this would call Google Places API
        # For now, return sample data
        return {
            "id": place_id,
            "title": f"Google Place {place_id}",
            "description": "Detailed information from Google Places API",
            "category": "Google Place",
            "location": "Unknown",
            "rating": 4.0,
            "price": "€€",
            "coordinates": {"lat": 45.1, "lng": 15.2},
            "hostTip": "This is a Google Places result",
            "weatherDependent": False,
            "source": "google_places",
            "place_id": place_id
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Location cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_cached_queries": len(self._cache),
            "cache_size": sum(len(str(v)) for v in self._cache.values()),
            "oldest_entry": min(
                (entry["cached_at"] for entry in self._cache.values()),
                default=None
            ),
            "newest_entry": max(
                (entry["cached_at"] for entry in self._cache.values()),
                default=None
            )
        }
