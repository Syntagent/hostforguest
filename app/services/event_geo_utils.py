"""Shared geography helpers for local events and guest recommendations."""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional, Set, Tuple

import requests

from app.services.maintenance_service import haversine_km

logger = logging.getLogger(__name__)

# OSM-backed settlement centroids (Kvarner / Istria)
CITY_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "lovran": (45.292, 14.276),
    "opric": (45.304, 14.270),
    "oprić": (45.304, 14.270),
    "liganj": (45.287, 14.259),
    "mošćenička draga": (45.239, 14.253),
    "moscenicka draga": (45.239, 14.253),
    "opatija": (45.335, 14.305),
    "rijeka": (45.327, 14.442),
    "pula": (44.866, 13.849),
    "zagreb": (45.815, 15.982),
    "split": (43.508, 16.440),
    "zadar": (44.119, 15.231),
    "osijek": (45.555, 18.695),
    "crikvenica": (45.177, 14.693),
    "rab": (44.757, 14.759),
    "krk": (45.027, 14.573),
}

# Previous wrong centroids — used to re-backfill stored coordinates.
STALE_CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "lovran": (45.168, 14.274),
    "liganj": (45.152, 14.268),
    "mošćenička draga": (45.238, 14.256),
    "moscenicka draga": (45.238, 14.256),
}

# Settlements treated as the same municipality for distance sanity.
MUNICIPALITY_SETTLEMENTS: Dict[str, Tuple[str, ...]] = {
    "lovran": ("opric", "oprić", "lovran", "liganj", "obrs", "lovranska draga"),
}

_GEOCODE_CACHE: Dict[str, Tuple[float, float]] = {}
_LAST_GEOCODE_AT = 0.0


def normalize_match_text(text: str) -> str:
    """Lowercase + strip Croatian diacritics for fuzzy keyword matching."""
    t = text.lower()
    for src, dst in (("č", "c"), ("ć", "c"), ("ž", "z"), ("š", "s"), ("đ", "d")):
        t = t.replace(src, dst)
    return t


def municipality_key(city: Optional[str]) -> Optional[str]:
    if not city:
        return None
    key = normalize_match_text(str(city).strip())
    for municipality, settlements in MUNICIPALITY_SETTLEMENTS.items():
        if key == municipality or key in settlements:
            return municipality
    return None


def same_municipality(city_a: Optional[str], city_b: Optional[str]) -> bool:
    a = municipality_key(city_a)
    b = municipality_key(city_b)
    return a is not None and a == b


def resolve_city_coords(city: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not city or not str(city).strip():
        return None, None
    key = normalize_match_text(str(city).strip())
    if key in CITY_CENTROIDS:
        return CITY_CENTROIDS[key]
    for name, coords in CITY_CENTROIDS.items():
        if name in key or key in name:
            return coords
    return None, None


def coords_match_stale_centroid(
    city: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
    *,
    tolerance_km: float = 1.5,
) -> bool:
    if lat is None or lng is None or not city:
        return False
    stale = STALE_CITY_COORDS.get(normalize_match_text(str(city).strip()))
    if not stale:
        return False
    return haversine_km(lat, lng, stale[0], stale[1]) <= tolerance_km


def _build_geocode_query(*parts: Optional[str]) -> Optional[str]:
    cleaned = [str(p).strip() for p in parts if p and str(p).strip()]
    if not cleaned:
        return None
    query = ", ".join(cleaned)
    if "croatia" not in query.lower() and "hrvatska" not in query.lower():
        query = f"{query}, Croatia"
    return query


def geocode_place(query: str, *, use_cache: bool = True) -> Tuple[Optional[float], Optional[float]]:
    """Best-effort geocode via Nominatim (cached, rate-limited)."""
    global _LAST_GEOCODE_AT
    normalized = query.strip().lower()
    if not normalized:
        return None, None
    if use_cache and normalized in _GEOCODE_CACHE:
        cached = _GEOCODE_CACHE[normalized]
        return cached

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if api_key:
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": query, "key": api_key},
                timeout=8,
            )
            if response.status_code == 200:
                results = (response.json().get("results") or [])
                if results:
                    loc = (results[0].get("geometry") or {}).get("location") or {}
                    lat, lng = loc.get("lat"), loc.get("lng")
                    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                        coords = (float(lat), float(lng))
                        _GEOCODE_CACHE[normalized] = coords
                        return coords
        except Exception as exc:
            logger.debug("Google geocode failed for %s: %s", query, exc)

    elapsed = time.time() - _LAST_GEOCODE_AT
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "hr",
            },
            headers={"User-Agent": "HostForGuest/1.0 (event geo backfill)"},
            timeout=10,
        )
        _LAST_GEOCODE_AT = time.time()
        if response.status_code != 200:
            return None, None
        payload = response.json()
        if not payload:
            return None, None
        first = payload[0]
        coords = (float(first["lat"]), float(first["lon"]))
        _GEOCODE_CACHE[normalized] = coords
        return coords
    except Exception as exc:
        logger.debug("Nominatim geocode failed for %s: %s", query, exc)
        return None, None


def resolve_event_location_coords(
    city: Optional[str],
    *,
    venue_name: Optional[str] = None,
    title: Optional[str] = None,
    allow_geocode: bool = True,
) -> Tuple[Optional[float], Optional[float]]:
    """Resolve event coordinates: venue geocode, then city centroid."""
    if allow_geocode and venue_name:
        query = _build_geocode_query(venue_name, city, "Primorsko-goranska")
        if query:
            coords = geocode_place(query)
            if coords:
                return coords

    city_coords = resolve_city_coords(city)
    if city_coords[0] is not None:
        return city_coords

    if allow_geocode and title and city:
        query = _build_geocode_query(title, city)
        if query:
            return geocode_place(query)
    return None, None


def reference_points_for_event_cities(cities: List[str]) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    seen: Set[str] = set()
    for raw in cities:
        key = normalize_match_text(str(raw).strip())
        if not key or key in seen:
            continue
        seen.add(key)
        coords = resolve_city_coords(raw)
        if coords[0] is not None:
            points.append(coords)
        municipality = municipality_key(raw)
        if municipality:
            for settlement in MUNICIPALITY_SETTLEMENTS.get(municipality, ()):
                if settlement in seen:
                    continue
                sc = CITY_CENTROIDS.get(settlement)
                if sc:
                    seen.add(settlement)
                    points.append(sc)
    return points


def nearby_feed_cities(lat: Optional[float], lng: Optional[float], radius_km: float) -> List[str]:
    if lat is None or lng is None:
        return []
    out: List[str] = []
    seen: set[str] = set()
    for name, (clat, clng) in CITY_CENTROIDS.items():
        if haversine_km(lat, lng, clat, clng) > radius_km:
            continue
        label = name.title() if name.islower() else name
        if name in ("opric", "oprić"):
            label = "Oprić"
        norm = normalize_match_text(label)
        if norm in seen:
            continue
        seen.add(norm)
        out.append(label)
    return out
