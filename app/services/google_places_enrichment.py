"""
Google Places enrichment for attractions.

Fetches place_id + details once per attraction and stores all fields locally.
Re-fetches only when google_data_fetched_at is older than 30 days.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import googlemaps
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import Attraction, AttractionStatus
from app.services.google_maps_utils import google_maps_link, place_photo_url

logger = logging.getLogger(__name__)

REFRESH_AFTER_DAYS = 30
RATE_LIMIT_SECONDS = 1.0
NEARBY_CACHE_TTL = timedelta(hours=24)

PLACE_DETAIL_FIELDS = [
    "place_id",
    "rating",
    "user_ratings_total",
    "price_level",
    "opening_hours",
    "website",
    "formatted_phone_number",
    "photo",
    "url",
]


class GooglePlacesEnrichmentService:
    """Enrich attractions with Google Places data and persist locally."""

    _nearby_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
        self._client_instance = None
        self._last_call_monotonic: float = 0.0

    @property
    def _client(self):
        if self._client_instance is None and self.api_key:
            try:
                self._client_instance = googlemaps.Client(key=self.api_key)
            except ValueError as exc:
                logger.error("Invalid GOOGLE_MAPS_API_KEY: %s", exc)
        return self._client_instance

    @_client.setter
    def _client(self, value):
        self._client_instance = value

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call_monotonic
        if elapsed < RATE_LIMIT_SECONDS:
            await asyncio.sleep(RATE_LIMIT_SECONDS - elapsed)
        self._last_call_monotonic = time.monotonic()

    async def _run_sync(self, func, *args, **kwargs):
        await self._rate_limit()
        return await asyncio.to_thread(func, *args, **kwargs)

    def _needs_refresh(self, attraction: Attraction, *, force: bool = False) -> bool:
        if force:
            return True
        if not attraction.google_place_id or not attraction.google_data_fetched_at:
            return True
        age = datetime.utcnow() - attraction.google_data_fetched_at
        return age >= timedelta(days=REFRESH_AFTER_DAYS)

    async def _find_place_id(self, attraction: Attraction) -> Optional[str]:
        if not self._client:
            return None
        query = f"{attraction.name}, {attraction.city}, Croatia"
        kwargs: Dict[str, Any] = {
            "input": query,
            "input_type": "textquery",
            "fields": ["place_id"],
        }
        if attraction.latitude is not None and attraction.longitude is not None:
            kwargs["location_bias"] = (
                f"circle:5000@{attraction.latitude},{attraction.longitude}"
            )

        def _call():
            return self._client.find_place(**kwargs)

        try:
            result = await self._run_sync(_call)
        except Exception as exc:
            logger.warning("find_place failed for %s: %s", attraction.name, exc)
            return None

        candidates = (result or {}).get("candidates") or []
        if not candidates:
            logger.info("No Google place match for %s", query)
            return None
        return candidates[0].get("place_id")

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        place_type: str,
        radius: int = 3000,
        limit: int = 5,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Nearby Google Places search with 24h in-memory cache.

        ``place_type`` may be a single type or pipe-separated types
        (e.g. ``grocery_or_supermarket|store``).
        ``keyword`` is passed to Google Places text search (e.g. "hamburger").
        """
        if not self._client:
            logger.debug("GOOGLE_MAPS_API_KEY missing; skipping nearby search")
            return []

        types = [t.strip() for t in (place_type or "").split("|") if t.strip()]
        if not types and not keyword:
            return []

        cache_key = (
            f"nearby_{round(lat, 4)}_{round(lng, 4)}_"
            f"{'|'.join(sorted(types))}_{radius}_{keyword or ''}"
        )
        cached = self._nearby_cache.get(cache_key)
        if cached:
            age = datetime.utcnow() - cached["cached_at"]
            if age < NEARBY_CACHE_TTL:
                return list(cached["places"])[:limit]

        all_places: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        search_types = types or ["restaurant"]
        for ptype in search_types:
            def _call(ptype=ptype):
                kwargs: Dict[str, Any] = {
                    "location": (lat, lng),
                    "radius": radius,
                }
                if ptype:
                    kwargs["type"] = ptype
                if keyword:
                    kwargs["keyword"] = keyword
                return self._client.places_nearby(**kwargs)

            try:
                result = await self._run_sync(_call)
            except Exception as exc:
                logger.warning("places_nearby failed for type=%s: %s", ptype, exc)
                continue

            for place in (result or {}).get("results") or []:
                pid = place.get("place_id")
                if pid and pid in seen_ids:
                    continue
                if pid:
                    seen_ids.add(pid)
                loc = (place.get("geometry") or {}).get("location") or {}
                all_places.append(
                    {
                        "name": place.get("name"),
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "vicinity": place.get("vicinity"),
                        "place_id": pid,
                        "types": place.get("types") or [],
                        "latitude": loc.get("lat"),
                        "longitude": loc.get("lng"),
                    }
                )

        all_places.sort(
            key=lambda p: (p.get("rating") or 0, p.get("user_ratings_total") or 0),
            reverse=True,
        )
        self._nearby_cache[cache_key] = {
            "places": all_places,
            "cached_at": datetime.utcnow(),
        }
        return all_places[:limit]

    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None

        def _call():
            return self._client.place(place_id, fields=PLACE_DETAIL_FIELDS)

        try:
            result = await self._run_sync(_call)
        except Exception as exc:
            logger.warning("place details failed for %s: %s", place_id, exc)
            return None
        return (result or {}).get("result")

    @staticmethod
    def _photo_reference_urls(photos: Optional[List[Dict[str, Any]]]) -> List[str]:
        urls: List[str] = []
        for photo in photos or []:
            ref = photo.get("photo_reference")
            if ref:
                urls.append(place_photo_url(ref, maxwidth=800))
        return urls[:10]

    @staticmethod
    def _merge_opening_hours(
        existing: Any, google_hours: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        base = dict(existing) if isinstance(existing, dict) else {}
        if not google_hours:
            return base
        if not base:
            return {
                "weekday_text": google_hours.get("weekday_text") or [],
                "periods": google_hours.get("periods") or [],
                "open_now": google_hours.get("open_now"),
            }
        base.setdefault("google", {})
        if isinstance(base["google"], dict):
            base["google"].update(
                {
                    "weekday_text": google_hours.get("weekday_text") or [],
                    "periods": google_hours.get("periods") or [],
                    "open_now": google_hours.get("open_now"),
                }
            )
        return base

    def _apply_details(self, attraction: Attraction, details: Dict[str, Any]) -> None:
        attraction.google_place_id = details.get("place_id") or attraction.google_place_id
        attraction.google_rating = details.get("rating")
        attraction.google_user_ratings_total = details.get("user_ratings_total")
        price = details.get("price_level")
        attraction.google_price_level = price if price is not None else None
        attraction.google_photos = self._photo_reference_urls(details.get("photo"))
        attraction.google_website = details.get("website")
        attraction.google_phone = details.get("formatted_phone_number")
        attraction.opening_hours = self._merge_opening_hours(
            attraction.opening_hours, details.get("opening_hours")
        )
        if not attraction.featured_image_url and attraction.google_photos:
            attraction.featured_image_url = attraction.google_photos[0]
        attraction.google_data_fetched_at = datetime.utcnow()

    async def enrich_attraction(
        self,
        db: AsyncSession,
        attraction: Attraction,
        *,
        force_refresh: bool = False,
    ) -> bool:
        """
        Enrich a single attraction. Returns True on success or fresh cache hit.
        """
        if not self._client:
            logger.error("GOOGLE_MAPS_API_KEY not configured")
            return bool(attraction.google_place_id)

        if not self._needs_refresh(attraction, force=force_refresh):
            logger.debug("Skipping fresh Google data for %s", attraction.name)
            return True

        place_id = attraction.google_place_id
        if not place_id or force_refresh:
            place_id = await self._find_place_id(attraction)
            if not place_id:
                return bool(attraction.google_data_fetched_at)

        details = await self._get_place_details(place_id)
        if not details:
            return bool(attraction.google_data_fetched_at)

        self._apply_details(attraction, details)
        db.add(attraction)
        await db.flush()
        try:
            await db.refresh(attraction)
        except Exception:
            pass
        logger.info("Enriched attraction with Google place %s", place_id)
        return True

    async def batch_enrich_all(
        self,
        db: AsyncSession,
        city: Optional[str] = None,
        *,
        attraction_ids: Optional[List[Any]] = None,
        host_id: Optional[Any] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Enrich approved attractions, optionally filtered by city, IDs, or host."""
        filters = [Attraction.status == AttractionStatus.APPROVED]
        if city:
            filters.append(Attraction.city.ilike(city.strip()))
        if attraction_ids:
            filters.append(Attraction.id.in_(attraction_ids))
        if host_id is not None:
            filters.append(Attraction.created_by_host_id == host_id)

        result = await db.execute(select(Attraction).where(and_(*filters)))
        attractions = list(result.scalars().all())

        enriched = skipped = failed = 0
        results: List[Dict[str, Any]] = []

        for attraction in attractions:
            if (
                not force_refresh
                and attraction.google_place_id
                and attraction.google_data_fetched_at
                and not self._needs_refresh(attraction)
            ):
                skipped += 1
                results.append(
                    {
                        "attraction_id": attraction.id,
                        "name": attraction.name,
                        "success": True,
                        "skipped": True,
                        "message": "Fresh cached Google data",
                    }
                )
                continue

            try:
                ok = await self.enrich_attraction(
                    db, attraction, force_refresh=force_refresh
                )
                if ok:
                    enriched += 1
                    results.append(
                        {
                            "attraction_id": attraction.id,
                            "name": attraction.name,
                            "success": True,
                            "skipped": False,
                            "message": "Enriched from Google Places",
                        }
                    )
                else:
                    failed += 1
                    results.append(
                        {
                            "attraction_id": attraction.id,
                            "name": attraction.name,
                            "success": False,
                            "skipped": False,
                            "message": "Google Places lookup failed",
                        }
                    )
            except Exception as exc:
                await db.rollback()
                failed += 1
                logger.exception("Enrichment error for %s", attraction.name)
                results.append(
                    {
                        "attraction_id": attraction.id,
                        "name": attraction.name,
                        "success": False,
                        "skipped": False,
                        "message": str(exc),
                    }
                )

        return {
            "total": len(attractions),
            "enriched": enriched,
            "skipped": skipped,
            "failed": failed,
            "results": results,
        }

    @staticmethod
    def enrichment_status(attraction: Attraction) -> Dict[str, Any]:
        """Build enrichment status payload for API responses."""
        fetched_at = attraction.google_data_fetched_at
        days_since: Optional[int] = None
        needs_refresh = True
        if fetched_at:
            days_since = (datetime.utcnow() - fetched_at).days
            needs_refresh = days_since >= REFRESH_AFTER_DAYS

        photos = attraction.google_photos if isinstance(attraction.google_photos, list) else []
        maps_url = google_maps_link(attraction.latitude, attraction.longitude, name=attraction.name)

        return {
            "attraction_id": attraction.id,
            "name": attraction.name,
            "is_enriched": bool(attraction.google_place_id and fetched_at),
            "google_place_id": attraction.google_place_id,
            "google_data_fetched_at": fetched_at,
            "days_since_fetch": days_since,
            "needs_refresh": needs_refresh,
            "google_rating": attraction.google_rating,
            "google_user_ratings_total": attraction.google_user_ratings_total,
            "google_price_level": attraction.google_price_level,
            "google_photos_count": len(photos),
            "has_website": bool(attraction.google_website),
            "has_phone": bool(attraction.google_phone),
            "google_maps_url": maps_url,
        }

    @staticmethod
    def computed_maps_fields(attraction: Attraction) -> Dict[str, Optional[str]]:
        """Derived map URLs for API responses (not stored in DB)."""
        from app.services.google_maps_utils import static_map_image_url

        maps_url = google_maps_link(
            attraction.latitude, attraction.longitude, name=attraction.name
        )
        static_url = None
        if attraction.latitude is not None and attraction.longitude is not None:
            static_url = static_map_image_url(attraction.latitude, attraction.longitude)
        return {"google_maps_url": maps_url, "static_map_image_url": static_url}

    @staticmethod
    def guest_attraction_google_extras(attraction: Attraction) -> Dict[str, Any]:
        """Google Places fields for GuestAttractionSummary (with scrubbing applied by caller)."""
        maps_fields = GooglePlacesEnrichmentService.computed_maps_fields(attraction)
        google_photos = (
            list(attraction.google_photos or [])
            if isinstance(attraction.google_photos, list)
            else []
        )
        google_rating = attraction.google_rating
        avg_rating = google_rating if google_rating is not None else attraction.guest_rating
        review_count = (
            int(attraction.google_user_ratings_total or 0)
            if attraction.google_user_ratings_total
            else int(attraction.total_ratings or 0)
        )
        return {
            "featured_image_url_fallback": google_photos[0] if google_photos else None,
            "image_gallery_fallback": google_photos,
            "average_rating": avg_rating,
            "review_count": review_count,
            "google_place_id": attraction.google_place_id,
            "google_rating": google_rating,
            "google_user_ratings_total": attraction.google_user_ratings_total,
            "google_price_level": attraction.google_price_level,
            "google_photos_raw": google_photos,
            "google_website_raw": attraction.google_website,
            "google_phone_raw": attraction.google_phone,
            **maps_fields,
        }
