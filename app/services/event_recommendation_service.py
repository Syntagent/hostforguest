"""
Personalized event recommendations for guest stays.

Scores tourism feed items and host seasonal events using guest preferences,
stay timing, geography, distance from the property, and pragmatic signals.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import SeasonalEvent
from app.models.content_source import ContentType
from app.models.guest_group import GuestGroup, GuestPreference
from app.models.host import Host, HostProfile
from app.services.event_geo_utils import (
    CITY_CENTROIDS,
    nearby_feed_cities as _nearby_feed_cities,
    normalize_match_text as _normalize_match_text,
    reference_points_for_event_cities,
    resolve_city_coords as _resolve_city_coords,
    resolve_event_location_coords,
)
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

INTEREST_EVENT_HINTS: Dict[str, Tuple[str, ...]] = {
    "food": ("food", "wine", "gastro", "market", "cherry", "črešnj", "cresnj", "cresnja", "marun", "truffle", "tasting", "restaurant", "seafood"),
    "nature": ("sea", "regatta", "hiking", "park", "beach", "outdoor", "lungomare", "priroda"),
    "culture": ("festival", "concert", "music", "heritage", "art", "cultural", "kultura", "izložb", "exhibition"),
    "history": ("historic", "heritage", "museum", "old town", "povijest", "grada"),
    "adventure": ("regatta", "sailing", "sport", "active", "trka"),
    "music": ("concert", "music", "open-air", "blues", "festival", "glazb"),
    "wine": ("wine", "cellar", "tasting", "gastro", "vino"),
    "seafood": ("seafood", "fish", "rib", "plava", "gastro"),
}

NON_GUEST_EVENT_PATTERNS = (
    "qa event",
    "test seasonal event",
    "ben qa",
    "events qa",
)

MIN_EVENTS_SKIP_BOOTSTRAP = 8
_RECOMMENDATION_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SEC = 120


@dataclass
class GuestEventContext:
    stay_city: str
    feed_cities: List[str]
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
    preferred_radius_km: float = 35.0
    inferred_stay_window: bool = False


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
    venue_lat: Optional[float] = None
    venue_lng: Optional[float] = None
    venue_name: Optional[str] = None
    quality_score: float = 0.5
    relevance_score: float = 0.5
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    date_certainty: str = "unknown"
    scraped_at: Optional[datetime] = None


def _city_name_ok(name: Optional[str]) -> bool:
    if not name or not str(name).strip():
        return False
    return not re.search(r"\s\d{1,4}[a-zA-Z]?$", str(name).strip())


def _dedupe_cities(names: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for raw in names:
        c = str(raw).strip()
        if not c or not _city_name_ok(c):
            continue
        key = _normalize_match_text(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def resolve_event_feed_cities(offerings: Dict[str, Any], fallback: str = "Lovran") -> List[str]:
    """Cities used to load event candidates (settlement + municipality + region hubs)."""
    hi = offerings.get("host_info") or {}
    si = offerings.get("stay_info") or {}
    li = offerings.get("location_info") or {}
    return _dedupe_cities(
        [
            si.get("city"),
            hi.get("broader_city"),
            li.get("city"),
            hi.get("city"),
            fallback,
        ]
    ) or [fallback]


def resolve_event_city_from_offerings(offerings: Dict[str, Any], fallback: str = "Lovran") -> str:
    """Primary guest-facing city label for event copy (prefer property settlement)."""
    cities = resolve_event_feed_cities(offerings, fallback)
    return cities[0] if cities else fallback


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


def _is_guest_visible_event(title: str, body: str = "") -> bool:
    """Keep automated QA/test content out of guest-facing recommendations."""
    blob = f"{title} {body}".lower()
    return not any(pattern in blob for pattern in NON_GUEST_EVENT_PATTERNS)


class EventRecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.feed = EventsFeedService(db)

    def _cache_key(
        self,
        access_code: str,
        check_in: Optional[date],
        check_out: Optional[date],
        limit: int,
        interest_sig: str,
    ) -> str:
        return f"{access_code}:{check_in}:{check_out}:{limit}:{interest_sig}"

    def _parse_iso_date(self, value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    async def get_recommendations_for_access_code(
        self,
        guest_group: GuestGroup,
        host: Host,
        profile: Optional[HostProfile],
        preferences: List[GuestPreference],
        *,
        limit: int = 15,
        bootstrap_if_empty: bool = True,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        offerings = build_host_offerings_payload(host, profile, "")
        access_code = getattr(guest_group, "access_code", None) or offerings.get("metadata", {}).get("access_code") or ""
        city = resolve_event_city_from_offerings(offerings)
        ctx = self._build_context(guest_group, preferences, offerings, city, host, profile)

        interest_sig = ",".join(sorted(ctx.interests))[:120]
        cache_key = self._cache_key(access_code, ctx.check_in, ctx.check_out, limit, interest_sig)
        if refresh and access_code:
            _RECOMMENDATION_CACHE.pop(cache_key, None)
        elif access_code:
            cached = _RECOMMENDATION_CACHE.get(cache_key)
            if cached and (time.time() - cached[0]) < CACHE_TTL_SEC:
                return cached[1]

        if bootstrap_if_empty and ctx.feed_cities:
            existing = await self.feed.count_active_local_events(
                cities=ctx.feed_cities,
                region=ctx.region,
            )
            if existing < MIN_EVENTS_SKIP_BOOTSTRAP:
                await self.feed.bootstrap_feed(city=ctx.feed_cities[0])

        candidates = await self._load_candidates(ctx)
        scored = [self._score(c, ctx) for c in candidates]
        if ctx.check_in or ctx.check_out:
            scored = [
                s
                for s in scored
                if s.get("start_date")
                and s.get("timing_status") in ("during_stay", "near_stay", "upcoming")
            ]
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        top = scored[: max(1, min(limit, 30))]

        payload = {
            "success": True,
            "city": city,
            "stay_window": {
                "check_in": ctx.check_in.isoformat() if ctx.check_in else None,
                "check_out": ctx.check_out.isoformat() if ctx.check_out else None,
                "inferred": ctx.inferred_stay_window,
            },
            "personalization": {
                "interests": sorted(ctx.interests),
                "keyword_count": len(ctx.keywords),
                "budget_level": ctx.budget_level,
                "travel_style": ctx.travel_style,
                "mobility_limited": ctx.mobility_limited,
                "preferred_radius_km": ctx.preferred_radius_km,
                "feed_cities": ctx.feed_cities,
            },
            "recommendations": top,
            "total_candidates": len(candidates),
        }
        if access_code:
            _RECOMMENDATION_CACHE[cache_key] = (time.time(), payload)
        return payload

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
        inferred_stay = False
        if not check_in and not check_out:
            today = date.today()
            duration = (
                getattr(group, "typical_stay_duration", None)
                or getattr(host, "typical_stay_duration", None)
                or 7
            )
            try:
                duration = max(1, min(int(duration), 30))
            except (TypeError, ValueError):
                duration = 7
            check_in = today
            check_out = today + timedelta(days=duration - 1)
            inferred_stay = True
        elif check_in and not check_out:
            duration = getattr(host, "typical_stay_duration", None) or 7
            try:
                duration = max(1, min(int(duration), 30))
            except (TypeError, ValueError):
                duration = 7
            check_out = check_in + timedelta(days=duration - 1)
            inferred_stay = True

        feed_cities = _dedupe_cities(
            resolve_event_feed_cities(offerings, city)
            + _nearby_feed_cities(
                float(lat) if lat is not None else None,
                float(lng) if lng is not None else None,
                35.0,
            )
        )

        return GuestEventContext(
            stay_city=city,
            feed_cities=feed_cities or [city],
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
            preferred_radius_km=35.0,
            inferred_stay_window=inferred_stay,
        )

    async def _load_candidates(self, ctx: GuestEventContext) -> List[EventCandidate]:
        out: List[EventCandidate] = []
        seen_ids: Set[str] = set()

        feed_rows = await self.feed.get_local_events_batch(
            cities=ctx.feed_cities,
            region=ctx.region,
            hours=24 * 180,
            limit=150,
            stay_start=ctx.check_in,
            stay_end=ctx.check_out,
        )
        if not feed_rows:
            feed_rows = await self.feed.get_updates(
                city=ctx.feed_cities[0] if ctx.feed_cities else None,
                content_types=[ContentType.EVENTS],
                hours=24 * 180,
                limit=80,
            )

        for row in feed_rows:
            row_id = str(row["id"])
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            candidate = self._feed_row_to_candidate(row, ctx)
            if candidate:
                out.append(candidate)

        seasonal_rows = await self._load_seasonal_rows(ctx)
        for ev in seasonal_rows:
            ev_id = str(ev.id)
            if ev_id in seen_ids:
                continue
            seen_ids.add(ev_id)
            candidate = self._seasonal_to_candidate(ev)
            if candidate and self._guest_visible_candidate(candidate, ctx):
                out.append(candidate)

        return out

    def _guest_visible_candidate(self, c: EventCandidate, ctx: GuestEventContext) -> bool:
        from app.services.event_timing_utils import should_include_event_for_guest

        include, certainty = should_include_event_for_guest(
            start_at=c.start_at,
            end_at=c.end_at,
            start_date=c.start_date,
            end_date=c.end_date,
            title=c.title,
            description=c.description,
            scraped_at=c.scraped_at,
            check_in=ctx.check_in,
            check_out=ctx.check_out,
        )
        if include:
            c.date_certainty = certainty
        return include

    def _feed_row_to_candidate(
        self, row: Dict[str, Any], ctx: Optional[GuestEventContext] = None
    ) -> Optional[EventCandidate]:
        cities = [str(c) for c in (row.get("relevant_cities") or [])]
        regions = [str(r) for r in (row.get("relevant_regions") or [])]
        kw = [str(k) for k in (row.get("keywords") or [])]
        title = row.get("title") or ""
        content = row.get("content") or row.get("description") or ""
        if not _is_guest_visible_event(title, content):
            return None
        lat = row.get("lat")
        lng = row.get("lng")
        if lat is None or lng is None:
            clat, clng = resolve_event_location_coords(
                cities[0] if cities else None,
                venue_name=row.get("venue_name"),
                title=title,
                allow_geocode=False,
            )
            if clat is not None and clng is not None:
                lat, lng = clat, clng
            else:
                for city_name in cities:
                    clat, clng = _resolve_city_coords(city_name)
                    if clat is not None and clng is not None:
                        lat, lng = clat, clng
                        break
        start_at = self._parse_iso_datetime(row.get("start_at"))
        end_at = self._parse_iso_datetime(row.get("end_at"))
        scraped_at = self._parse_iso_datetime(row.get("created_at"))
        from app.services.event_timing_utils import effective_event_window

        start_date, end_date, start_at, end_at, certainty = effective_event_window(
            start_at=start_at,
            end_at=end_at,
            start_date=self._parse_iso_date(row.get("start_at")),
            end_date=self._parse_iso_date(row.get("end_at")),
            title=title,
            description=content,
        )
        candidate = EventCandidate(
            id=str(row["id"]),
            source="feed",
            title=title,
            description=content,
            search_blob=_normalize_match_text(f"{title} {content} {' '.join(kw)}"),
            keywords=kw,
            cities=cities,
            regions=regions,
            url=row.get("url"),
            start_date=start_date,
            end_date=end_date,
            event_type=row.get("content_type"),
            booking_required=False,
            admission_info=None,
            host_curated=False,
            venue_lat=float(lat) if lat is not None else None,
            venue_lng=float(lng) if lng is not None else None,
            venue_name=row.get("venue_name"),
            quality_score=float(row.get("quality_score") or 0.5),
            relevance_score=float(row.get("relevance_score") or 0.5),
            start_at=start_at,
            end_at=end_at,
            date_certainty=certainty,
            scraped_at=scraped_at,
        )
        if ctx and not self._guest_visible_candidate(candidate, ctx):
            return None
        return candidate

    def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    async def _load_seasonal_rows(self, ctx: GuestEventContext) -> List[SeasonalEvent]:
        stmt = select(SeasonalEvent).where(SeasonalEvent.is_active.is_(True))
        city_filters = []
        for city in ctx.feed_cities[:8]:
            c = str(city).strip()
            if c:
                city_filters.append(SeasonalEvent.city.ilike(f"%{c}%"))
        if city_filters:
            stmt = stmt.where(or_(*city_filters))
        if ctx.check_in and ctx.check_out:
            stmt = stmt.where(
                or_(
                    SeasonalEvent.start_date.is_(None),
                    and_(
                        SeasonalEvent.start_date <= ctx.check_out + timedelta(days=21),
                        or_(
                            SeasonalEvent.end_date.is_(None),
                            SeasonalEvent.end_date >= ctx.check_in - timedelta(days=7),
                        ),
                    ),
                )
            )
        stmt = stmt.order_by(SeasonalEvent.start_date.asc().nullslast()).limit(40)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _seasonal_to_candidate(self, ev: SeasonalEvent) -> Optional[EventCandidate]:
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
            return None
        return EventCandidate(
            id=str(ev.id),
            source="seasonal",
            title=ev.name,
            description=body or ev.description,
            search_blob=_normalize_match_text(f"{ev.name} {body} {ev.event_type} {ev.city}"),
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
        )

    def _score(self, c: EventCandidate, ctx: GuestEventContext) -> Dict[str, Any]:
        from app.services.event_timing_utils import classify_stay_timing

        timing_score, timing_status = classify_stay_timing(
            c.start_date,
            c.end_date or c.start_date,
            ctx.check_in,
            ctx.check_out,
        )
        if not c.start_date and not c.end_date:
            timing_score = 0.25
            timing_status = "unknown"

        scores = {
            "preference": self._preference_score(c, ctx),
            "timing": timing_score,
            "geographic": self._geographic_score(c, ctx),
            "distance": self._distance_score(c, ctx),
            "pragmatic": self._pragmatic_score(c, ctx),
            "host_curated": 1.0 if c.host_curated else 0.35,
        }
        feed_boost = min(0.08, (c.quality_score + c.relevance_score) * 0.04)
        total = sum(scores[k] * EVENT_RECOMMENDATION_WEIGHTS[k] for k in EVENT_RECOMMENDATION_WEIGHTS)
        total = min(1.0, total + feed_boost)

        dist_km = self._min_distance_km(c, ctx)
        travel_hint = None
        if dist_km is not None and ctx.stay_lat is not None and ctx.stay_lng is not None:
            dest_lat, dest_lng = c.venue_lat, c.venue_lng
            if dest_lat is None or dest_lng is None:
                city_key = c.cities[0] if c.cities else ctx.stay_city
                dest_lat, dest_lng = _resolve_city_coords(city_key)
            if dest_lat is not None and dest_lng is not None:
                from app.services.event_travel_hint import road_travel_hint

                travel_hint = road_travel_hint(
                    ctx.stay_lat, ctx.stay_lng, dest_lat, dest_lng, dist_km
                )
        plan_hint = self._plan_hint(c, ctx, dist_km, travel_hint)

        from app.services.event_timing_utils import format_event_schedule_label

        schedule_label = format_event_schedule_label(
            start_at=c.start_at,
            end_at=c.end_at,
            start_date=c.start_date,
            end_date=c.end_date,
            title=c.title,
            description=c.description,
        )
        start_time = None
        end_time = None
        if c.start_at and (c.start_at.hour or c.start_at.minute):
            start_time = c.start_at.strftime("%H:%M")
        if c.end_at and (c.end_at.hour or c.end_at.minute):
            end_time = c.end_at.strftime("%H:%M")

        why = self._why_recommended(c, ctx, scores, timing_status=timing_status)

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
            "start_time": start_time,
            "end_time": end_time,
            "schedule_label": schedule_label,
            "date_certainty": c.date_certainty,
            "timing_status": timing_status,
            "booking_required": c.booking_required,
            "admission_info": c.admission_info,
            "distance_km": round(dist_km, 1) if dist_km is not None else None,
            "venue_name": c.venue_name,
            "relevance_score": round(total, 3),
            "priority": "high" if total >= 0.72 else "medium" if total >= 0.5 else "low",
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "why_recommended": why,
            "plan_hint": plan_hint,
        }

    def _preference_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        if not ctx.keywords and not ctx.interests:
            return 0.45
        blob = c.search_blob
        hit_scores: List[float] = []

        for kw in ctx.keywords:
            nk = _normalize_match_text(kw)
            if len(nk) < 2:
                continue
            if nk in blob:
                hit_scores.append(1.0)
                continue
            if any(nk in _normalize_match_text(k) for k in c.keywords):
                hit_scores.append(0.9)
                continue
            hints = INTEREST_EVENT_HINTS.get(nk, (nk,))
            if any(_normalize_match_text(h) in blob for h in hints):
                hit_scores.append(0.85)

        for interest in ctx.interests:
            hints = INTEREST_EVENT_HINTS.get(interest.lower(), (interest.lower(),))
            if any(_normalize_match_text(h) in blob for h in hints):
                hit_scores.append(1.0)
            elif _normalize_match_text(interest) in blob:
                hit_scores.append(0.75)

        if not hit_scores:
            return 0.32
        hit_scores.sort(reverse=True)
        top = hit_scores[:4]
        return min(1.0, 0.3 + (sum(top) / len(top)) * 0.7)

    def _timing_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        from app.services.event_timing_utils import classify_stay_timing

        if not c.start_date and not c.end_date:
            return 0.25
        score, _ = classify_stay_timing(
            c.start_date,
            c.end_date or c.start_date,
            ctx.check_in,
            ctx.check_out,
        )
        return score

    def _geographic_score(self, c: EventCandidate, ctx: GuestEventContext) -> float:
        cities_l = [_normalize_match_text(x) for x in c.cities]
        stay = _normalize_match_text(ctx.stay_city)
        feed = [_normalize_match_text(x) for x in ctx.feed_cities]
        broader = _normalize_match_text(ctx.broader_city or "")
        if stay and stay in cities_l:
            return 1.0
        if any(fc in cities_l for fc in feed):
            return 0.95
        if broader and broader in cities_l:
            return 0.88
        if ctx.region and any(_normalize_match_text(ctx.region) in _normalize_match_text(r) for r in c.regions):
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
        if c.venue_lat is not None and c.venue_lng is not None:
            return haversine_km(ctx.stay_lat, ctx.stay_lng, c.venue_lat, c.venue_lng)
        best: Optional[float] = None
        for lat, lng in reference_points_for_event_cities(c.cities):
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
        if c.admission_info and "free" in _normalize_match_text(c.admission_info or ""):
            score += 0.1
        if c.booking_required and ctx.travel_style == "relaxed":
            score -= 0.12
        if ctx.mobility_limited and any(x in blob for x in ("hiking", "regatta", "steep")):
            score -= 0.15
        if ctx.mobility_limited and any(x in blob for x in ("concert", "market", "old town")):
            score += 0.08
        return min(1.0, max(0.0, score))

    def _why_recommended(self, c: EventCandidate, ctx: GuestEventContext, scores: Dict[str, float], *, timing_status: str = "unknown") -> str:
        parts: List[str] = []
        if scores["preference"] >= 0.6 and ctx.interests:
            matched = next(
                (i for i in ctx.interests if any(h in c.search_blob for h in INTEREST_EVENT_HINTS.get(i, (i,)))),
                None,
            )
            if matched:
                parts.append(f"Matches your interest in {matched}")
        if timing_status == "during_stay" and ctx.check_in:
            if ctx.inferred_stay_window:
                parts.append("Likely during your upcoming stay (dates estimated)")
            else:
                parts.append("Fits your stay dates")
        elif timing_status == "near_stay" and ctx.check_in:
            parts.append("Just before or after your stay — good if you arrive early or stay on")
        elif timing_status == "outside_stay" or scores["timing"] < 0.3:
            parts.append("May be outside your stay window — confirm dates with your host")
        if scores["geographic"] >= 0.9:
            parts.append(f"Near {ctx.stay_city}")
        if c.host_curated:
            parts.append("Highlighted by your host")
        if not parts:
            parts.append("Worth exploring to enrich your time in the area")
        return " · ".join(parts)

    def _plan_hint(
        self,
        c: EventCandidate,
        ctx: GuestEventContext,
        dist_km: Optional[float],
        travel_hint: Optional[str] = None,
    ) -> str:
        travel_suffix = f" ({travel_hint})" if travel_hint else ""
        if c.host_curated and c.booking_required:
            return "Ask your host to help with booking — good for a planned half-day."
        if dist_km is not None and dist_km <= 3:
            return f"Short trip from your stay (~{dist_km:.1f} km){travel_suffix} — easy for an evening or quick outing."
        if dist_km is not None and dist_km <= 5:
            return f"Easy outing from your stay (~{dist_km:.1f} km){travel_suffix} — pair with lunch or a coastal walk."
        if dist_km is not None and dist_km <= 8:
            return f"Half-day outing (~{dist_km:.0f} km){travel_suffix} — allow time for parking and a stroll afterward."
        if dist_km is not None and dist_km <= 25:
            city = c.cities[0] if c.cities else ctx.stay_city
            return f"Plan a half-day trip to {city} (~{dist_km:.0f} km from your stay){travel_suffix}."
        if any(x in c.search_blob for x in ("festival", "concert", "marunada")):
            return "Check the official link for times — popular events fill up on weekends."
        if "wine" in c.search_blob or "gastro" in c.search_blob:
            return "Combine with a local restaurant from Discover for a full food & culture day."
        return "Add to your itinerary as a flexible option and message your host for local tips."
