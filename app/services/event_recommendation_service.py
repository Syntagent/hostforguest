"""
Personalized event recommendations for guest stays.

Scores tourism feed items and host seasonal events using guest preferences,
stay timing, geography, distance from the property, and pragmatic signals.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import SeasonalEvent
from app.models.content_source import ContentType
from app.models.guest_group import GuestGroup, GuestPreference
from app.models.host import Host, HostProfile
from app.services.attraction_service import AttractionService
from app.services.events_feed_service import EventsFeedService
from app.services.host_offerings_for_guest import (
    build_host_offerings_payload,
    resolve_guest_stay_coordinates,
)
from app.services.maintenance_service import haversine_km

logger = logging.getLogger(__name__)

EVENT_RECOMMENDATION_WEIGHTS = {
    "preference": 0.30,
    "timing": 0.18,
    "geographic": 0.22,
    "distance": 0.15,
    "pragmatic": 0.10,
    "host_curated": 0.05,
}

# Approximate centroids for Kvarner / Istria event cities (lat, lng)
CITY_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "lovran": (45.168, 14.274),
    "opatija": (45.335, 14.305),
    "rijeka": (45.327, 14.442),
    "pula": (44.866, 13.849),
    "zagreb": (45.815, 15.982),
    "split": (43.508, 16.440),
    "zadar": (44.119, 15.231),
    "osijek": (45.555, 18.695),
}

INTEREST_EVENT_HINTS: Dict[str, Tuple[str, ...]] = {
    "food": ("food", "wine", "gastro", "market", "cherry", "truffle", "tasting", "restaurant"),
    "nature": ("sea", "regatta", "hiking", "park", "beach", "outdoor", "lungomare"),
    "culture": ("festival", "concert", "music", "heritage", "art", "cultural"),
    "history": ("historic", "heritage", "museum", "old town"),
    "adventure": ("regatta", "sailing", "sport", "active"),
    "music": ("concert", "music", "open-air"),
    "wine": ("wine", "cellar", "tasting", "gastro"),
}

NON_GUEST_EVENT_PATTERNS = (
    "qa event",
    "test seasonal event",
    "ben qa",
    "events qa",
)


@dataclass
class GuestEventContext:
    stay_city: str
    broader_city: Optional[str]
    region: Optional[str]
    stay_lat: Optional[float]
    stay_lng: Optional[float]
    check_in: Optional[date]
    check_out: Optional[date]
    keywords: Set[str] = field(default_factory=set)
    interests: Set[str] = field(default_factory=set)
    budget_level: str = "moderate"
    travel_style: str = "balanced"
    mobility_limited: bool = False
    preferred_radius_km: float = 25.0


@dataclass
class EventCandidate:
    id: str
    source: str  # feed | seasonal
    title: str
    description: str
    search_blob: str
    keywords: List[str]
    cities: List[str]
    regions: List[str]
    url: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    event_type: Optional[str]
    booking_required: bool
    admission_info: Optional[str]
    host_curated: bool
    quality_score: float = 0.5
    relevance_score: float = 0.5


def _norm_tokens(values: Any) -> Set[str]:
    out: Set[str] = set()
    if not values:
        return out
    items = values.values() if isinstance(values, dict) else values
    if not isinstance(items, (list, tuple)):
        items = [items]
    for x in items:
        for part in re.split(r"[,;/|]+", str(x).lower()):
            t = part.strip()
            if len(t) >= 2:
                out.add(t)
    return out


def _parse_budget_from_notes(notes: Optional[str]) -> Optional[str]:
    if not notes:
        return None
    m = re.search(r"budget:\s*(\w+)", notes.lower())
    return m.group(1) if m else None


def resolve_event_city_from_offerings(offerings: Dict[str, Any], fallback: str = "Lovran") -> str:
    hi = offerings.get("host_info") or {}
    si = offerings.get("stay_info") or {}
    li = offerings.get("location_info") or {}

    def ok(name: Optional[str]) -> bool:
        if not name or not str(name).strip():
            return False
        return not re.search(r"\s\d{1,4}[a-zA-Z]?$", str(name).strip())

    for c in (hi.get("broader_city"), li.get("city"), hi.get("city"), si.get("city"), fallback):
        if c and ok(str(c)):
            return str(c).strip()
    return fallback


def _is_guest_visible_event(title: str, body: str = "") -> bool:
    """Keep automated QA/test content out of guest-facing recommendations."""
    blob = f"{title} {body}".lower()
    return not any(pattern in blob for pattern in NON_GUEST_EVENT_PATTERNS)


class EventRecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.feed = EventsFeedService(db)

    async def get_recommendations_for_access_code(
        self,
        guest_group: GuestGroup,
        host: Host,
        profile: Optional[HostProfile],
        preferences: List[GuestPreference],
        *,
        limit: int = 15,
        bootstrap_if_empty: bool = True,
    ) -> Dict[str, Any]:
        offerings = build_host_offerings_payload(host, profile, "")
        city = resolve_event_city_from_offerings(offerings)
        ctx = self._build_context(guest_group, preferences, offerings, city, host, profile)

        if bootstrap_if_empty:
            await self.feed.bootstrap_feed(city=city)

        candidates = await self._load_candidates(city)
        scored = [self._score(c, ctx) for c in candidates]
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        top = scored[: max(1, min(limit, 30))]

        return {
            "success": True,
            "city": city,
            "stay_window": {
                "check_in": ctx.check_in.isoformat() if ctx.check_in else None,
                "check_out": ctx.check_out.isoformat() if ctx.check_out else None,
            },
            "personalization": {
                "interests": sorted(ctx.interests),
                "keyword_count": len(ctx.keywords),
                "budget_level": ctx.budget_level,
                "travel_style": ctx.travel_style,
                "mobility_limited": ctx.mobility_limited,
                "preferred_radius_km": ctx.preferred_radius_km,
            },
            "recommendations": top,
            "total_candidates": len(candidates),
        }

    def _build_context(
        self,
        group: GuestGroup,
        preferences: List[GuestPreference],
        offerings: Dict[str, Any],
        city: str,
        host: Host,
        profile: Optional[HostProfile],
    ) -> GuestEventContext:
        hi = offerings.get("host_info") or {}
        li = offerings.get("location_info") or {}
        coords = li.get("coordinates") or {}
        lat = coords.get("lat")
        lng = coords.get("lng")
        if lat is None or lng is None:
            lat, lng = resolve_guest_stay_coordinates(host, profile)

        keywords: Set[str] = set()
        keywords |= _norm_tokens(group.interests)
        keywords |= _norm_tokens(group.preferred_activities)
        keywords |= _norm_tokens(group.interested_regions)
        interests: Set[str] = set(group.interests or [])

        mobility_limited = False
        budget = (group.budget_level or "moderate").lower()

        for p in preferences:
            keywords |= _norm_tokens(p.personal_interests)
            keywords |= _norm_tokens(p.cultural_interests)
            keywords |= _norm_tokens(p.food_interests)
            interests |= _norm_tokens(p.personal_interests)
            interests |= _norm_tokens(p.cultural_interests)
            interests |= _norm_tokens(p.food_interests)
            notes = (p.mobility_notes or "").lower()
            if any(x in notes for x in ("wheelchair", "limited", "low mobility", "mobility: low")):
                mobility_limited = True
            b = _parse_budget_from_notes(p.mobility_notes)
            if b:
                budget = b

        check_in = group.check_in_date.date() if group.check_in_date else None
        check_out = group.check_out_date.date() if group.check_out_date else None

        return GuestEventContext(
            stay_city=city,
            broader_city=hi.get("broader_city"),
            region=li.get("region") or offerings.get("stay_info", {}).get("region"),
            stay_lat=float(lat) if lat is not None else None,
            stay_lng=float(lng) if lng is not None else None,
            check_in=check_in,
            check_out=check_out,
            keywords=keywords,
            interests=interests,
            budget_level=budget,
            travel_style=(group.travel_style or "balanced").lower(),
            mobility_limited=mobility_limited,
            preferred_radius_km=25.0,
        )

    async def _load_candidates(self, city: str) -> List[EventCandidate]:
        out: List[EventCandidate] = []
        feed_rows = await self.feed.get_updates(
            city=city,
            content_types=[ContentType.EVENTS],
            hours=24 * 90,
            limit=40,
        )
        for row in feed_rows:
            cities = [str(c) for c in (row.get("relevant_cities") or [])]
            regions = [str(r) for r in (row.get("relevant_regions") or [])]
            kw = [str(k) for k in (row.get("keywords") or [])]
            title = row.get("title") or ""
            content = row.get("content") or row.get("description") or ""
            if not _is_guest_visible_event(title, content):
                continue
            out.append(
                EventCandidate(
                    id=str(row["id"]),
                    source="feed",
                    title=title,
                    description=content,
                    search_blob=f"{title} {content} {' '.join(kw)}".lower(),
                    keywords=kw,
                    cities=cities,
                    regions=regions,
                    url=row.get("url"),
                    start_date=None,
                    end_date=None,
                    event_type=row.get("content_type"),
                    booking_required=False,
                    admission_info=None,
                    host_curated=False,
                    quality_score=float(row.get("quality_score") or 0.5),
                    relevance_score=float(row.get("relevance_score") or 0.5),
                )
            )

        svc = AttractionService(self.db)
        seasonal = await svc.get_seasonal_events(city=city, active_only=True)
        for ev in seasonal:
            sd = ev.start_date if isinstance(ev.start_date, date) else (
                ev.start_date.date() if ev.start_date else None
            )
            ed = ev.end_date if isinstance(ev.end_date, date) else (
                ev.end_date.date() if ev.end_date else None
            )
            body = " ".join(
                filter(
                    None,
                    [
                        ev.description,
                        ev.host_recommendation,
                        ev.best_time_to_visit,
                        ev.what_to_expect,
                    ],
                )
            )
            if not _is_guest_visible_event(ev.name, body):
                continue
            out.append(
                EventCandidate(
                    id=str(ev.id),
                    source="seasonal",
                    title=ev.name,
                    description=body or ev.description,
                    search_blob=f"{ev.name} {body} {ev.event_type} {ev.city}".lower(),
                    keywords=[ev.event_type],
                    cities=[ev.city] if ev.city else [],
                    regions=[],
                    url=None,
                    start_date=sd,
                    end_date=ed,
                    event_type=ev.event_type,
                    booking_required=bool(ev.booking_required),
                    admission_info=ev.admission_info,
                    host_curated=True,
                    quality_score=0.85,
                    relevance_score=0.8,
                )
            )
        return out

    def _score(self, c: EventCandidate, ctx: GuestEventContext) -> Dict[str, Any]:
        scores = {
            "preference": self._preference_score(c, ctx),
            "timing": self._timing_score(c, ctx),
            "geographic": self._geographic_score(c, ctx),
            "distance": self._distance_score(c, ctx),
            "pragmatic": self._pragmatic_score(c, ctx),
            "host_curated": 1.0 if c.host_curated else 0.35,
        }
        feed_boost = min(0.08, (c.quality_score + c.relevance_score) * 0.04)
        total = sum(scores[k] * EVENT_RECOMMENDATION_WEIGHTS[k] for k in EVENT_RECOMMENDATION_WEIGHTS)
        total = min(1.0, total + feed_boost)

        dist_km = self._min_distance_km(c, ctx)
        why = self._why_recommended(c, ctx, scores)
        plan_hint = self._plan_hint(c, ctx, dist_km)

        return {
            "id": c.id,
            "source": c.source,
            "title": c.title,
            "description": c.description,
            "url": c.url,
            "event_type": c.event_type,
            "cities": c.cities,
            "regions": c.regions,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "booking_required": c.booking_required,
            "admission_info": c.admission_info,
            "distance_km": round(dist_km, 1) if dist_km is not None else None,
            "relevance_score": round(total, 3),
            "priority": "high" if total >= 0.72 else "medium" if total >= 0.5 else "low",
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "why_recommended": why,
            "plan_hint": plan_hint,
        }

    def _preference_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        if not ctx.keywords and not ctx.interests:
            return 0.45
        hits = 0
        checked = 0
        for kw in ctx.keywords:
            checked += 1
            if kw in c.search_blob or any(kw in k.lower() for k in c.keywords):
                hits += 1
        for interest in ctx.interests:
            checked += 1
            hints = INTEREST_EVENT_HINTS.get(interest.lower(), (interest.lower(),))
            if any(h in c.search_blob for h in hints):
                hits += 1
        if checked == 0:
            return 0.45
        return min(1.0, 0.25 + (hits / checked) * 0.75)

    def _timing_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        if not ctx.check_in and not ctx.check_out:
            return 0.55 if c.start_date else 0.5
        if not c.start_date and not c.end_date:
            return 0.58
        start = c.start_date
        end = c.end_date or c.start_date
        cin, cout = ctx.check_in, ctx.check_out
        if cin and cout and start and end:
            if end < cin or (start > cout):
                return 0.12
            return 1.0
        if cin and start and start >= cin - timedelta(days=14):
            return 0.85
        return 0.5

    def _geographic_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        cities_l = [x.lower() for x in c.cities]
        stay = ctx.stay_city.lower()
        broader = (ctx.broader_city or "").lower()
        if stay in cities_l or (broader and broader in cities_l):
            return 1.0
        if ctx.region and any(ctx.region.lower() in r.lower() for r in c.regions):
            return 0.82
        if cities_l:
            return 0.55
        return 0.4

    def _distance_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        dist = self._min_distance_km(c, ctx)
        if dist is None:
            return self._geographic_score(c, ctx) * 0.85
        radius = ctx.preferred_radius_km
        if dist <= 5:
            return 1.0
        if dist <= radius:
            return max(0.35, 1.0 - (dist - 5) / max(radius, 1))
        return max(0.15, 0.35 - (dist - radius) / 60)

    def _min_distance_km(self, c: EventCandidate, ctx: GuestEventContext) -> Optional[float]:
        if ctx.stay_lat is None or ctx.stay_lng is None:
            return None
        best: Optional[float] = None
        names = [x.lower() for x in c.cities]
        if ctx.stay_city:
            names.append(ctx.stay_city.lower())
        for name in names:
            key = name.strip().lower()
            if key in CITY_CENTROIDS:
                lat, lng = CITY_CENTROIDS[key]
                d = haversine_km(ctx.stay_lat, ctx.stay_lng, lat, lng)
                best = d if best is None else min(best, d)
        return best

    def _pragmatic_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        score = 0.55
        blob = c.search_blob
        budget = ctx.budget_level
        if budget == "budget" and any(x in blob for x in ("free", "gratis", "open air", "market")):
            score += 0.2
        if budget in ("luxury", "high") and any(x in blob for x in ("wine", "tasting", "gala", "premium")):
            score += 0.15
        if c.admission_info and "free" in (c.admission_info or "").lower():
            score += 0.1
        if c.booking_required and ctx.travel_style == "relaxed":
            score -= 0.12
        if ctx.mobility_limited and any(x in blob for x in ("hiking", "regatta", "steep")):
            score -= 0.15
        if ctx.mobility_limited and any(x in blob for x in ("concert", "market", "old town")):
            score += 0.08
        return min(1.0, max(0.0, score))

    def _why_recommended(self, c: EventCandidate, ctx: GuestEventContext, scores: Dict[str, float]) -> str:
        parts: List[str] = []
        if scores["preference"] >= 0.6 and ctx.interests:
            matched = next(
                (i for i in ctx.interests if any(h in c.search_blob for h in INTEREST_EVENT_HINTS.get(i, (i,)))),
                None,
            )
            if matched:
                parts.append(f"Matches your interest in {matched}")
        if scores["timing"] >= 0.85 and ctx.check_in:
            parts.append("Fits your stay dates")
        elif scores["timing"] < 0.3:
            parts.append("May be outside your stay window — confirm dates with your host")
        if scores["geographic"] >= 0.9:
            parts.append(f"Near {ctx.stay_city}")
        if c.host_curated:
            parts.append("Highlighted by your host")
        if not parts:
            parts.append("Worth exploring to enrich your time in the area")
        return " · ".join(parts)

    def _plan_hint(self, c: EventCandidate, ctx: GuestEventContext, dist_km: Optional[float]) -> str:
        if c.host_curated and c.booking_required:
            return "Ask your host to help with booking — good for a planned half-day."
        if dist_km is not None and dist_km <= 8:
            return f"Easy outing (~{dist_km:.0f} km) — pair with lunch or a coastal walk."
        if dist_km is not None and dist_km <= 25:
            city = c.cities[0] if c.cities else ctx.stay_city
            return f"Plan a half-day trip to {city} (~{dist_km:.0f} km from your stay)."
        if any(x in c.search_blob for x in ("festival", "concert", "marunada")):
            return "Check the official link for times — popular events fill up on weekends."
        if "wine" in c.search_blob or "gastro" in c.search_blob:
            return "Combine with a local restaurant from Discover for a full food & culture day."
        return "Add to your itinerary as a flexible option and message your host for local tips."
