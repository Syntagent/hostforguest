"""Optional road-travel hints for event plan copy (Google Directions)."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_CACHE: dict[str, Tuple[float, Optional[str]]] = {}
_CACHE_TTL_SEC = 6 * 3600


def _cache_key(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> str:
    return f"{origin_lat:.4f},{origin_lng:.4f}->{dest_lat:.4f},{dest_lng:.4f}"


def road_travel_hint(
    origin_lat: Optional[float],
    origin_lng: Optional[float],
    dest_lat: Optional[float],
    dest_lng: Optional[float],
    straight_km: Optional[float],
) -> Optional[str]:
    """
    Return a short driving hint like "~12 min drive" when Google Directions is available.
    Falls back to None — callers keep straight-line copy.
    """
    if straight_km is None or straight_km > 25:
        return None
    if origin_lat is None or origin_lng is None or dest_lat is None or dest_lng is None:
        return None

    api_key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    if not api_key:
        return None

    key = _cache_key(origin_lat, origin_lng, dest_lat, dest_lng)
    cached = _CACHE.get(key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SEC:
        return cached[1]

    hint: Optional[str] = None
    try:
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "mode": "driving",
            "key": api_key,
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
            data = resp.json()
        if data.get("status") == "OK":
            leg = (data.get("routes") or [{}])[0].get("legs") or [{}]
            leg0 = leg[0] if leg else {}
            duration_text = (leg0.get("duration") or {}).get("text")
            distance_text = (leg0.get("distance") or {}).get("text")
            if duration_text:
                hint = f"~{duration_text} drive"
                if distance_text and straight_km and straight_km >= 5:
                    hint = f"{hint} ({distance_text} by road)"
        _CACHE[key] = (time.time(), hint)
    except Exception as exc:
        logger.debug("Directions hint unavailable: %s", exc)

    return hint
