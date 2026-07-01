"""
OSRM (OpenStreetMap) routing service for realistic walking/driving distances.
Free, no API key required. Falls back to Haversine on failure.
"""
import aiohttp
import asyncio
import logging
from typing import Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)

OSRM_BASE = "https://router.project-osrm.org"

PROFILES = {
    "walking": f"{OSRM_BASE}/route/v1/walking",
    "driving": f"{OSRM_BASE}/route/v1/driving",
}

_CACHE: dict = {}  # Simple in-memory cache: "lat1,lng1-lat2,lng2-profile" -> (meters, seconds)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Fallback: great-circle distance in km."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def _cache_key(lat1, lon1, lat2, lon2, profile):
    return f"{lat1:.4f},{lon1:.4f}-{lat2:.4f},{lon2:.4f}-{profile}"


async def osrm_route(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    profile: str = "walking"
) -> Tuple[float, float]:
    """
    Get route distance (meters) and duration (seconds) from OSRM.
    
    Args:
        lat1, lon1: Starting coordinates
        lat2, lon2: Destination coordinates  
        profile: 'walking' or 'driving'
    
    Returns:
        (distance_meters, duration_seconds)
        Falls back to Haversine * 1.5 for walking, * 1.3 for driving on failure.
    """
    key = _cache_key(lat1, lon1, lat2, lon2, profile)
    if key in _CACHE:
        return _CACHE[key]
    
    url = f"{PROFILES.get(profile, PROFILES['walking'])}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    routes = data.get("routes", [])
                    if routes:
                        route = routes[0]
                        result = (route["distance"], route["duration"])
                        _CACHE[key] = result
                        return result
    except Exception as e:
        logger.debug(f"OSRM routing failed for {key}: {e}")
    
    # Fallback: Haversine with terrain factor
    km = haversine_km(lat1, lon1, lat2, lon2)
    factor = 1.5 if profile == "walking" else 1.3
    meters = km * 1000 * factor
    speed_ms = 1.4 if profile == "walking" else 13.9  # 5 km/h walk, 50 km/h drive
    seconds = meters / speed_ms
    result = (int(meters), int(seconds))
    _CACHE[key] = result
    return result


def osrm_route_sync(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    profile: str = "walking"
) -> Tuple[float, float]:
    """Synchronous wrapper for osrm_route."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            future = concurrent.futures.Future()
            async def _run():
                result = await osrm_route(lat1, lon1, lat2, lon2, profile)
                future.set_result(result)
            loop.create_task(_run())
            return future.result(timeout=10)
        return asyncio.run(osrm_route(lat1, lon1, lat2, lon2, profile))
    except Exception as e:
        logger.debug(f"Sync OSRM failed: {e}")
        km = haversine_km(lat1, lon1, lat2, lon2)
        factor = 1.5 if profile == "walking" else 1.3
        return (int(km * 1000 * factor), int(km * 1000 * factor / (1.4 if profile == "walking" else 13.9)))


def format_duration(seconds: int) -> str:
    """Human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    mins = seconds // 60
    if mins < 60:
        return f"{mins} min"
    hours = mins // 60
    mins = mins % 60
    return f"{hours}h {mins}min" if mins else f"{hours}h"


def format_distance(meters: float) -> str:
    """Human-readable distance."""
    if meters < 1000:
        return f"{int(meters)}m"
    return f"{meters/1000:.1f}km"
