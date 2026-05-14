"""
Location caching service for Google Maps integration.

Provides intelligent caching of Google Places data and integration
with the existing attraction database for optimal performance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.attraction import Attraction, AttractionStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host

logger = logging.getLogger(__name__)


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
        
        # Get guest group and host information
        guest_group_query = select(GuestGroup).options(
            selectinload(GuestGroup.host)
        ).where(GuestGroup.id == guest_group_id)
        
        guest_group_result = await self.db.execute(guest_group_query)
        guest_group = guest_group_result.scalar_one_or_none()
        
        if not guest_group:
            return locations
        
        host = guest_group.host
        
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
                "rating": attraction.guest_rating or 4.0,
                "price": attraction.admission_fee or "Free",
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
                "best_months": attraction.best_months
            }
            for attraction in attractions
        ]
    
    async def _get_cached_google_places(
        self, 
        city: str, 
        latitude: Optional[float], 
        longitude: Optional[float]
    ) -> List[Dict[str, Any]]:
        """
        Get cached Google Places data for the host's city.
        
        In a real implementation, this would:
        1. Check cache for existing data
        2. If cache miss, call Google Places API
        3. Store results in cache
        4. Return formatted data
        """
        cache_key = f"google_places_{city.lower()}"
        
        # Check if we have cached data
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.now() - cached_data["cached_at"] < self._cache_ttl:
                return cached_data["locations"]
        
        # In a real implementation, this would call Google Places API
        # For now, return sample data
        sample_places = await self._get_sample_google_places(city, latitude, longitude)
        
        # Cache the results
        self._cache[cache_key] = {
            "locations": sample_places,
            "cached_at": datetime.now()
        }
        
        return sample_places
    
    async def _get_sample_google_places(
        self, 
        city: str, 
        latitude: Optional[float], 
        longitude: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Get sample Google Places data for development."""
        # This would be replaced with actual Google Places API calls
        sample_places = [
            {
                "id": f"google_place_1_{city}",
                "title": f"Popular Restaurant in {city}",
                "description": "Highly-rated local restaurant with traditional Croatian cuisine",
                "category": "Food & Wine",
                "location": city,
                "rating": 4.5,
                "price": "€€",
                "coordinates": {
                    "lat": (latitude or 45.1) + 0.01,
                    "lng": (longitude or 15.2) + 0.01
                },
                "hostTip": "Try the local seafood specialties!",
                "weatherDependent": False,
                "source": "google_places",
                "place_id": f"google_place_id_1_{city}",
                "opening_hours": {"open_now": True},
                "contact_info": {"phone": "+385 1 234 567"},
                "website": f"https://example-restaurant-{city}.com"
            },
            {
                "id": f"google_place_2_{city}",
                "title": f"Historic Site in {city}",
                "description": "Important historical landmark with guided tours available",
                "category": "Culture & History",
                "location": city,
                "rating": 4.7,
                "price": "€5-10",
                "coordinates": {
                    "lat": (latitude or 45.1) - 0.01,
                    "lng": (longitude or 15.2) - 0.01
                },
                "hostTip": "Visit early morning to avoid crowds",
                "weatherDependent": False,
                "source": "google_places",
                "place_id": f"google_place_id_2_{city}",
                "opening_hours": {"open_now": True},
                "contact_info": {"phone": "+385 1 234 568"}
            }
        ]
        
        return sample_places
    
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
