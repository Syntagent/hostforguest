"""
Google Maps URL helpers for attractions and recommendations.

Generates link and static-map image URLs without calling external APIs.
"""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import quote


def google_maps_link(
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    name: Optional[str] = None,
) -> Optional[str]:
    """Return a Google Maps search link for coordinates or a place name."""
    if latitude is not None and longitude is not None:
        return f"https://maps.google.com/?q={latitude},{longitude}"
    if name:
        return f"https://www.google.com/maps/search/?api=1&query={quote(name)}"
    return None


def static_map_image_url(
    latitude: float,
    longitude: float,
    *,
    api_key: Optional[str] = None,
    zoom: int = 14,
    width: int = 600,
    height: int = 400,
    marker: bool = True,
) -> Optional[str]:
    """Return a Google Static Maps image URL (requires API key at render time)."""
    key = (api_key or os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
    if not key:
        return None
    center = f"{latitude},{longitude}"
    params = [
        f"center={center}",
        f"zoom={zoom}",
        f"size={width}x{height}",
        "maptype=roadmap",
        f"key={key}",
    ]
    if marker:
        params.append(f"markers=color:red%7C{center}")
    return "https://maps.googleapis.com/maps/api/staticmap?" + "&".join(params)


def place_photo_url(
    photo_reference: str,
    *,
    api_key: Optional[str] = None,
    maxwidth: int = 800,
) -> str:
    """Build a Place Photo URL from a photo reference (key required to fetch)."""
    key = (api_key or os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
    base = (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={maxwidth}&photo_reference={quote(photo_reference, safe='')}"
    )
    if key:
        return f"{base}&key={key}"
    return base
