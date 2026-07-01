"""Guest-facing A2A agents — preference-driven concierge for Telegram guests."""

from __future__ import annotations

import copy
import logging
import uuid
from abc import ABC
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_group import GuestGroup, GuestPreference
from app.models.host import Host, HostProfile
from app.models.recommendation import RecommendationRequestAPI, GuestRecommendationItem
from app.services.a2a.agent_wrappers import BaseHFGAgent
from app.services.a2a.guest_prefs import (
    format_prefs_summary,
    get_didnt_understand,
    get_preference_prompt,
    parse_preference_message,
    preference_prompt_hr,
    prefs_to_api_categories,
    prefs_to_interests,
)
from app.services.event_discovery_service import EventDiscoveryService
from app.services.event_preference_matcher import filter_events_by_preferences
from app.services.event_recommendation_service import (
    EventRecommendationService,
    sanitize_event_recommendations_for_guest,
)
from app.services.events_feed_service import EventsFeedService
from app.services.guest_group_service import GuestGroupService
from app.services.host_offerings_for_guest import (
    build_host_offerings_payload,
    scrub_contact_from_text,
)
from app.services.host_service import HostService
from app.services.guest_weather_service import (
    fetch_guest_weather_forecast,
    weather_fallback_links,
)
from app.services.google_places_enrichment import GooglePlacesEnrichmentService
from app.services.google_maps_utils import google_maps_link
from app.services.maintenance_service import haversine_km
from app.services.recommendation_service import RecommendationService
from app.services.partner_service import PartnerService
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.services.a2a.ai_category_classifier import (
    FoodClassifierResult,
    ai_classify_categories,
    ai_classify_info_intent,
)
from app.services.a2a.ai_response_generator import (
    generate_concierge_intro,
    generate_event_header,
)

logger = logging.getLogger(__name__)

_CONTACT_REMOVED = "[contact removed]"
_TOURIST_GOOGLE_TYPES = {"restaurant","cafe","bar","beach","park","museum","art_gallery","church","tourist_attraction","zoo","aquarium","amusement_park","wine_bar","night_club","casino","bowling_alley","stadium","movie_theater","spa","gym"}

_MAP_LINK_LABELS: Dict[str, str] = {
    "hr": "Otvori kartu",
    "de": "Karte öffnen",
    "en": "Open map",
    "it": "Apri mappa",
    "hu": "Térkép megnyitása",
    "pl": "Otwórz mapę",
}

_NO_DATA_MSG: Dict[str, str] = {
    "hr": (
        "Trenutno nemam dovoljno podataka za *{city}*. "
        "Pitajte domaćina ili pokušajte drugu kategoriju (npr. plaže, restorani)."
    ),
    "de": (
        "Für *{city}* habe ich derzeit nicht genug Daten. "
        "Fragen Sie den Gastgeber oder versuchen Sie eine andere Kategorie."
    ),
    "en": (
        "I don't have enough data for *{city}* right now. "
        "Ask your host or try another category (e.g. beaches, restaurants)."
    ),
    "it": (
        "Al momento non ho abbastanza dati per *{city}*. "
        "Chiedete al padrone di casa o provate un'altra categoria."
    ),
    "hu": (
        "Jelenleg nincs elég adatom *{city}* területére. "
        "Kérdezze a házigazdát, vagy próbáljon más kategóriát."
    ),
    "pl": (
        "Nie mam wystarczających danych dla *{city}*. "
        "Zapytaj gospodarza lub spróbuj innej kategorii."
    ),
}


def _detect_max_price_level(message: str) -> Optional[int]:
    """Legacy budget keyword detector (superseded by AI classifier)."""
    text = (message or "").lower()
    budget_words = (
        "jeftin", "cheap", "budget", "günstig", "gunstig", "billig", "economico",
        "low cost", "affordable", "povoljn",
    )
    if any(w in text for w in budget_words):
        return 1
    return None


def _get_language(context: Dict[str, Any]) -> str:
    lang = (context.get("language") or context.get("preferred_language") or "hr").strip().lower()
    if lang not in ("hr", "de", "en", "it", "hu", "pl"):
        lang = "en"
    return lang


def _guest_safe_city_label(raw: Optional[str], fallback: str = "Lovran") -> str:
    """Scrub inline contact from city labels before display or URL interpolation."""
    cleaned = scrub_contact_from_text(str(raw or "").strip()) or ""
    if not cleaned or cleaned.strip() == _CONTACT_REMOVED:
        return fallback
    return cleaned


def _resolve_guest_coordinates(
    context: Dict[str, Any],
    profile: Optional[HostProfile],
    host: Host,
) -> tuple[Optional[float], Optional[float]]:
    """Best-effort stay coordinates for nearby Google Places search."""
    lat = context.get("latitude") or context.get("lat")
    lng = context.get("longitude") or context.get("lng")
    if lat is not None and lng is not None:
        return float(lat), float(lng)
    if profile is not None:
        if profile.latitude is not None and profile.longitude is not None:
            return float(profile.latitude), float(profile.longitude)
    if host.latitude is not None and host.longitude is not None:
        return float(host.latitude), float(host.longitude)
    return None, None



def _format_distance_m(distance_m: float) -> str:
    if distance_m < 1000:
        return f"{int(round(distance_m))}m"
    return f"{distance_m / 1000:.1f}km"




def _format_google_price_indicator(price_level: Optional[int]) -> str:
    if price_level is None:
        return ""
    if price_level <= 0:
        return "Free"
    return "$" * min(price_level, 4)


def _emoji_for_rec(title: str, prefs: Dict[str, Any]) -> str:
    t = title.lower()
    tags = set(prefs.get("tags") or [])
    if "beach" in tags or "plaž" in t or "plaz" in t:
        return "🏖️"
    if "animals" in tags or "zoo" in t:
        return "🦁"
    if "family" in tags or prefs.get("has_children"):
        return "👨‍👩‍👧"
    if "wine" in tags or "vino" in t:
        return "🍷"
    if "park" in t or "nature" in tags:
        return "🌳"
    return "📍"


def _format_concierge_rec_line(
    index: int,
    item: GuestRecommendationItem,
    emoji: str,
    lang: str,
    desc_limit: int = 120,
) -> str:
    """Format one concierge recommendation with Google Places metadata."""
    title = item.title or (item.attraction.name if item.attraction else "Place")
    desc = (item.description or "")[:desc_limit]
    att = item.attraction
    meta_parts: List[str] = []

    if att:
        rating = att.google_rating if att.google_rating is not None else att.average_rating
        reviews = (
            att.google_user_ratings_total
            if att.google_user_ratings_total is not None
            else att.review_count
        )
        if rating is not None:
            rating_txt = f"⭐{rating:.1f}"
            if reviews:
                rating_txt += f" ({reviews:,})"
            meta_parts.append(rating_txt)

        maps_url = att.google_maps_url
        if maps_url:
            map_label = _MAP_LINK_LABELS.get(lang, _MAP_LINK_LABELS["en"])
            meta_parts.append(f"[📍 {map_label}]({maps_url})")

        price_indicator = _format_google_price_indicator(att.google_price_level)
        if price_indicator:
            meta_parts.append(f"💰{price_indicator}")

        website = att.google_website
        if website:
            meta_parts.append(f"[🌐 Web]({website})")

    meta = f" {' · '.join(meta_parts)}" if meta_parts else ""
    return f"{index}. **{title}** {emoji}{meta}\n   _{desc}_"


def _format_google_places_results(
    places: List[Dict[str, Any]],
    language: str,
    intro: str,
    origin_lat: float,
    origin_lng: float,
) -> str:
    """Format Google Places nearby results as numbered concierge recommendations."""
    lang = _get_language({"language": language})
    map_label = _MAP_LINK_LABELS.get(lang, _MAP_LINK_LABELS["en"])
    lines = [intro, ""]
    for i, place in enumerate(places, 1):
        name = place.get("name") or "Place"
        rating = place.get("rating")
        reviews = place.get("user_ratings_total")
        vicinity = (place.get("vicinity") or "").strip()
        plat = place.get("latitude")
        plng = place.get("longitude")
        distance_txt = ""
        if plat is not None and plng is not None:
            km = haversine_km(origin_lat, origin_lng, float(plat), float(plng))
            distance_txt = f" · {_format_distance_m(km * 1000)}"
        rating_txt = ""
        if rating is not None:
            rating_txt = f" ⭐{rating:.1f}"
            if reviews:
                rating_txt += f" ({reviews})"
        maps_url = google_maps_link(plat, plng, name=name) or ""
        maps_line = f"\n   🗺️ [{map_label}]({maps_url})" if maps_url else ""
        desc = f"\n   _{vicinity}_" if vicinity else ""
        lines.append(f"{i}. **{name}**{rating_txt}{distance_txt}{desc}{maps_line}")
    return "\n\n".join(lines)

# Nearest major hospitals by common stay cities (real public numbers)
_HOSPITAL_BY_CITY: Dict[str, tuple[str, str]] = {
    "lovran": ("KBC Rijeka", "051 658 000"),
    "opatija": ("KBC Rijeka", "051 658 000"),
    "rijeka": ("KBC Rijeka", "051 658 000"),
    "pula": ("Opća bolnica Pula", "052 505 500"),
    "default": ("Hitna pomoć — najbliža bolnica u regiji", "112"),
}


def _parse_start_ticket(message: str) -> Optional[str]:
    text = (message or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if payload.lower().startswith("ticket_"):
        return payload[7:].strip()
    return payload


async def resolve_ticket_to_group(
    db: AsyncSession,
    ticket: str,
) -> Optional[GuestGroup]:
    """Resolve ticket payload (UUID or access code) to a guest group."""
    svc = GuestGroupService(db)
    ticket = (ticket or "").strip()
    if not ticket:
        return None

    try:
        gid = uuid.UUID(ticket)
        return await svc.get_guest_group_by_id(gid)
    except ValueError:
        pass

    group = await svc.validate_access_code(ticket.upper())
    return group


def _apply_prefs_to_group(group: GuestGroup, guest_prefs: Optional[Dict[str, Any]]) -> GuestGroup:
    """Return a copy of guest group with session preferences merged into interests."""
    if not guest_prefs:
        return group
    patched = copy.copy(group)
    merged = list(group.interests or [])
    for tag in prefs_to_interests(guest_prefs):
        if tag not in merged:
            merged.append(tag)
    patched.interests = merged
    if guest_prefs.get("has_children") and "family_friendly" not in merged:
        patched.interests = merged + ["family_friendly"]
    raw = (guest_prefs.get("raw_text") or "").strip()
    if raw:
        notes = list(group.preferred_activities or [])
        if raw not in notes:
            notes.append(raw[:200])
        patched.preferred_activities = notes
    return patched


class BaseGuestAgent(BaseHFGAgent, ABC):
    """Shared helpers for guest session agents."""

    _skip_reply_scrub: bool = False

    def _ok(self, text: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._skip_reply_scrub:
            text = scrub_contact_from_text(text) or text
        return super()._ok(text, data)

    def _error(self, text: str) -> Dict[str, Any]:
        if not self._skip_reply_scrub:
            text = scrub_contact_from_text(text) or text
        return super()._error(text)

    async def _load_bundle(
        self,
        context: Dict[str, Any],
    ) -> Optional[tuple[GuestGroup, Host, Optional[HostProfile], Dict[str, Any]]]:
        if not self.db:
            return None
        gid_raw = context.get("guest_group_id")
        if not gid_raw:
            return None
        try:
            gid = uuid.UUID(str(gid_raw))
        except ValueError:
            return None

        gg_svc = GuestGroupService(self.db)
        host_svc = HostService(self.db)
        group = await gg_svc.get_guest_group_by_id(gid)
        if not group:
            return None
        host = await host_svc.get_host_by_id(group.host_id)
        if not host:
            return None
        profile = await host_svc.get_host_profile(group.host_id)
        prefs = context.get("guest_prefs")
        patched = _apply_prefs_to_group(group, prefs)
        return patched, host, profile, context

    def _require_prefs(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not context.get("prefs_captured") or not context.get("guest_prefs"):
            return self._ok(
                "Prije preporuka, recite mi što vas zanima na odmoru.\n\n"
                + preference_prompt_hr()
            )
        return None


class GuestWelcomeAgent(BaseGuestAgent):
    agent_id = "guest-welcome-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db:
            return self._error("Baza podataka nije dostupna.")

        text = (message or "").strip()
        lang = _get_language(context)

        welcome_msg = {
            "hr": (
                "🌿 **Dobro došli u {property_name}!**\n\n"
                "📅 Boravak: {cin} – {cout}\n"
                "👤 Domaćin: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
            "de": (
                "🌿 **Willkommen in {property_name}!**\n\n"
                "📅 Aufenthalt: {cin} – {cout}\n"
                "👤 Gastgeber: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
            "en": (
                "🌿 **Welcome to {property_name}!**\n\n"
                "📅 Stay: {cin} – {cout}\n"
                "👤 Host: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
            "it": (
                "🌿 **Benvenuti a {property_name}!**\n\n"
                "📅 Soggiorno: {cin} – {cout}\n"
                "👤 Ospite: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
            "hu": (
                "🌿 **Üdvözöljük a(z) {property_name} szállásán!**\n\n"
                "📅 Tartózkodás: {cin} – {cout}\n"
                "👤 Házigazda: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
            "pl": (
                "🌿 **Witamy w {property_name}!**\n\n"
                "📅 Pobyt: {cin} – {cout}\n"
                "👤 Gospodarz: *{host_name}*\n"
                "📍 {city}\n\n"
            ),
        }
        captured = {
            "hr": (
                "✅ **Zabilježeno:** {summary}\n\n"
                "Od sada su sve preporuke personalizirane. Evo nekoliko ideja za početak:\n\n"
            ),
            "de": (
                "✅ **Notiert:** {summary}\n\n"
                "Ab jetzt sind alle Empfehlungen personalisiert. Hier ein paar Ideen zum Start:\n\n"
            ),
            "en": (
                "✅ **Recorded:** {summary}\n\n"
                "From now on all recommendations are personalized. Here are a few ideas to start:\n\n"
            ),
            "it": (
                "✅ **Registrato:** {summary}\n\n"
                "Da ora tutte le raccomandazioni sono personalizzate. Ecco alcune idee per iniziare:\n\n"
            ),
            "hu": (
                "✅ **Rögzítve:** {summary}\n\n"
                "Mostantól minden ajánlás személyre szabott. Íme néhány ötlet a kezdéshez:\n\n"
            ),
            "pl": (
                "✅ **Zapisano:** {summary}\n\n"
                "Od teraz wszystkie rekomendacje są spersonalizowane. Oto kilka pomysłów na start:\n\n"
            ),
        }
        already_captured = {
            "hr": (
                "Vaše preferencije: *{summary}*\n\n"
                "Pitajte me što posjetiti, gdje jesti ili što se događa — "
                "sve preporuke prilagođavam vašem odmoru."
            ),
            "de": (
                "Ihre Vorlieben: *{summary}*\n\n"
                "Fragen Sie mich, was Sie besuchen, wo essen oder was los ist — "
                "alle Empfehlungen passe ich an Ihren Urlaub an."
            ),
            "en": (
                "Your preferences: *{summary}*\n\n"
                "Ask me what to visit, where to eat or what's on — "
                "I tailor all recommendations to your vacation."
            ),
            "it": (
                "Le vostre preferenze: *{summary}*\n\n"
                "Chiedetemi cosa visitare, dove mangiare o cosa succede — "
                "adatto tutte le raccomandazioni al vostro soggiorno."
            ),
            "hu": (
                "Az Ön preferenciái: *{summary}*\n\n"
                "Kérdezzen bármit: mit látogasson meg, hol egyen vagy mi történik — "
                "minden ajánlást az Ön nyaralásához igazítok."
            ),
            "pl": (
                "Wasze preferencje: *{summary}*\n\n"
                "Pytajcie o to, co odwiedzić, gdzie zjeść lub co się dzieje — "
                "dopasowuję wszystkie rekomendacje do Waszych wakacji."
            ),
        }

        if text.lower().startswith("/start"):
            ticket = _parse_start_ticket(text)
            if not ticket:
                return self._error(
                    "Skenirajte QR kod s ulaznicom ili otvorite link "
                    "`t.me/HostForGuestBot?start=ticket_<ID>`."
                )
            group = await resolve_ticket_to_group(self.db, ticket)
            if not group:
                return self._error("Ulaznica nije valjana ili je istekla. Kontaktirajte domaćina.")

            host_svc = HostService(self.db)
            host = await host_svc.get_host_by_id(group.host_id)
            profile = await host_svc.get_host_profile(group.host_id)
            if not host:
                return self._error("Domaćin nije pronađen.")

            raw_property_name = (
                (profile.property_name if profile else None) or host.business_name or "Smještaj"
            )
            property_name = scrub_contact_from_text(raw_property_name) or raw_property_name
            raw_host_name = f"{host.first_name} {host.last_name}".strip()
            host_name = scrub_contact_from_text(raw_host_name) or raw_host_name
            cin = group.check_in_date.strftime("%d.%m.%Y") if group.check_in_date else "—"
            cout = group.check_out_date.strftime("%d.%m.%Y") if group.check_out_date else "—"
            city = (profile.city if profile else None) or host.city or "Kvarner"

            context["role"] = "guest"
            context["guest_group_id"] = str(group.id)
            context["telegram_id"] = context.get("telegram_id")
            context["property_name"] = property_name
            context["host_name"] = host_name
            context["host_phone"] = host.phone or ""
            context["city"] = city
            context["check_in"] = cin
            context["check_out"] = cout
            context["prefs_captured"] = False
            context["guest_prefs"] = {}

            context["last_command"] = "guest_welcome"
            return self._ok(
                welcome_msg.get(lang, welcome_msg["en"]).format(
                    property_name=property_name,
                    cin=cin,
                    cout=cout,
                    host_name=host_name,
                    city=city,
                )
                + get_preference_prompt(lang),
                {"guest_group_id": str(group.id), "awaiting_prefs": True},
            )

        if not context.get("guest_group_id"):
            return self._error("Skenirajte QR kod za pristup concierge usluzi.")

        if context.get("prefs_captured"):
            bundle = await self._load_bundle(context)
            if not bundle:
                return self._error("Sesija istekla. Skenirajte QR ponovo.")
            group, host, profile, ctx = bundle
            summary = format_prefs_summary(ctx.get("guest_prefs") or {}, lang)
            return self._ok(
                already_captured.get(lang, already_captured["en"]).format(summary=summary)
            )

        parsed = await parse_preference_message(text)
        if not parsed:
            return self._ok(
                get_didnt_understand(lang) + get_preference_prompt(lang)
            )

        context["guest_prefs"] = parsed
        context["prefs_captured"] = True
        context["last_command"] = "capture_prefs"

        summary = format_prefs_summary(parsed, lang)
        initial = await self._initial_recommendations(context)
        body = captured.get(lang, captured["en"]).format(summary=summary) + initial
        return self._ok(body, {"guest_prefs": parsed})

    async def _initial_recommendations(self, context: Dict[str, Any]) -> str:
        bundle = await self._load_bundle(context)
        if not bundle:
            return "_Pitajte me npr. „što posjetiti“ za personalizirane prijedloge._"
        group, host, profile, ctx = bundle
        rec_svc = RecommendationService(self.db)
        lang = _get_language(ctx)
        cats = prefs_to_api_categories(ctx.get("guest_prefs")) or ["activity", "dining"]
        batch = await rec_svc.get_personalized_recommendations(
            group.id,
            RecommendationRequestAPI(
                max_recommendations=3,
                language=lang,
                preferred_categories=cats,
            ),
        )
        guest_batch = await rec_svc.enrich_batch_for_guest(
            batch, group.id, viewer_host_id=group.host_id
        )

        if not guest_batch.recommendations:
            return "_Pitajte me npr. „što posjetiti“ ili „gdje jesti“ — koristim lokalne podatke i partnere._"
        lines: List[str] = []
        for i, r in enumerate(guest_batch.recommendations, 1):
            emoji = _emoji_for_rec(r.title or "", ctx.get("guest_prefs") or {})
            lines.append(_format_concierge_rec_line(i, r, emoji, lang, desc_limit=100))
        return "\n\n".join(lines)



class GuestConciergeAgent(BaseGuestAgent):
    agent_id = "guest-concierge-hfg"

    async def _fallback_recommendations(self, city: str, prefs: dict, message: str, categories: list = None) -> list:
        from sqlalchemy import text
        from app.services.rls_service import RLSService
        try:
            await RLSService(self.db).set_bypass("worker")
        except Exception:
            pass
        
        items = []
        try:
            cats = categories or []
            tags = set(prefs.get("tags") or [])
            has_kids = prefs.get("has_children") or "family" in tags or "kids" in tags or "djeca" in tags
            likes_wine = "wine" in tags or "vino" in tags or "gastro" in tags
            
            # Search ALL known towns — distance filtering happens via Haversine
            cities = ["Lovran", "Opatija", "Ika", "Ičići", "Medveja", "Mošćenička Draga"]
            
            # Category-aware querying
            if any(c in cats for c in ("dining", "food", "wine", "restaurant")):
                ptypes = ["restaurant", "wine_bar", "cafe"]
                order = "CASE WHEN partner_type='wine_bar' THEN 0 ELSE 1 END" if likes_wine else "RANDOM()"
                result = await self.db.execute(
                    text(f"SELECT name, description, city, average_rating, total_reviews, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM partners WHERE city = ANY(:cities) AND status='active' AND partner_type = ANY(:ptypes) ORDER BY {order} LIMIT 5"),
                    {"cities": cities, "ptypes": ptypes}
                )
            elif any(c in cats for c in ("beach",)):
                if has_kids:
                    result = await self.db.execute(
                        text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' AND attraction_type='beach' ORDER BY guest_rating DESC NULLS LAST LIMIT 5"),
                        {"cities": cities}
                    )
                else:
                    result = await self.db.execute(
                        text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' AND attraction_type='beach' AND name NOT ILIKE '%djecja%' AND name NOT ILIKE '%cipera%' LIMIT 5"),
                        {"cities": cities}
                    )
            elif any(c in cats for c in ("cultural", "sightseeing")):
                result = await self.db.execute(
                    text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' AND attraction_type IN ('cultural','sightseeing') ORDER BY guest_rating DESC NULLS LAST LIMIT 5"),
                    {"cities": cities}
                )
            elif any(c in cats for c in ("nature", "activity")):
                result = await self.db.execute(
                    text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' AND attraction_type IN ('nature','sightseeing') ORDER BY guest_rating DESC NULLS LAST LIMIT 5"),
                    {"cities": cities}
                )
            else:
                if has_kids:
                    result = await self.db.execute(
                        text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' ORDER BY guest_rating DESC NULLS LAST LIMIT 5"),
                        {"cities": cities}
                    )
                else:
                    result = await self.db.execute(
                        text("SELECT name, description, city, google_rating, google_user_ratings_total, google_website, latitude, longitude FROM attractions WHERE city = ANY(:cities) AND status='approved' AND name NOT ILIKE '%djecja%' LIMIT 5"),
                        {"cities": cities}
                    )
            for row in result.fetchall():
                maps_url = None
                lat, lng = None, None
                rating = None
                reviews = None
                website = None
                n = len(row)
                # Partner rows (10 cols): name, desc, city, avg_rating, total_reviews, google_rating, google_reviews, google_website, lat, lng
                # Attraction rows (8 cols): name, desc, city, google_rating, google_reviews, google_website, lat, lng
                if n >= 10:
                    # Partner row
                    rating = row[5]  # google_rating
                    reviews = row[6]  # google_user_ratings_total
                    website = row[7]  # google_website
                    lat = row[8]
                    lng = row[9]
                    # Fall back to average_rating if no google_rating
                    if rating is None:
                        rating = row[3]  # average_rating
                    if reviews is None:
                        reviews = row[4]  # total_reviews
                elif n >= 8:
                    # Attraction row
                    rating = row[3]  # google_rating
                    reviews = row[4]  # google_user_ratings_total
                    website = row[5]  # google_website
                    lat = row[6]
                    lng = row[7]
                if maps_url is None and lat is not None and lng is not None:
                    maps_url = f"https://maps.google.com/?q={lat},{lng}"
                
                item = {"title": row[0], "desc": (row[1] or "")[:150]}
                if rating is not None or maps_url:
                    item["rating"] = rating
                    item["reviews"] = reviews
                    item["maps_url"] = maps_url
                    item["website"] = website
                items.append(item)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Fallback query failed: {e}")
        import logging
        logging.getLogger(__name__).info(f"Fallback for city={city} returned {len(items)} items (kids={has_kids}, wine={likes_wine})")
        return items

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        need = self._require_prefs(context)
        if need:
            return need

        bundle = await self._load_bundle(context)
        if not bundle:
            return self._error("Sesija nije aktivna. Skenirajte QR kod s ulaznice.")

        group, host, profile, ctx = bundle
        prefs = ctx.get("guest_prefs") or {}
        rec_svc = RecommendationService(self.db)
        cats = prefs_to_api_categories(ctx.get("guest_prefs")) or ["activity", "dining", "cultural"]
        lang = _get_language(ctx)
        # AI-powered multi-dimensional category classification
        ai_google_types: list = []
        max_price_level: Optional[int] = None
        food_type: Optional[str] = None
        query_terms: Optional[str] = None
        try:
            classification = await ai_classify_categories(message, preferred_language=lang)
            if classification.categories:
                cats = classification.categories
            ai_google_types = classification.google_place_types
            max_price_level = classification.resolved_max_price_level()
            food_type = classification.food_type
            query_terms = classification.query_terms
        except Exception:
            pass  # fall back to preference-based categories
        _is_practical = bool(ai_google_types) and not any(t in _TOURIST_GOOGLE_TYPES for t in ai_google_types)
        batch = await rec_svc.get_personalized_recommendations(
            group.id,
            RecommendationRequestAPI(
                max_recommendations=5,
                language=lang,
                preferred_categories=cats,
                max_price_level=max_price_level,
                food_type=food_type,
                query_terms=" ".join(query_terms) if isinstance(query_terms, list) else query_terms,
            ),
        )
        guest_batch = await rec_svc.enrich_batch_for_guest(
            batch, group.id, viewer_host_id=group.host_id
        )

        city = ctx.get("city") or host.city or "regiji"
        intro = await self._personalized_intro(prefs, message, lang, city)
        
        # Google Places search using AI-classified place types (no hardcoded mapping)
        google_lines = []
        google_count = 0
        # Filter Google types to tourist-relevant only
        ai_google_types = [t for t in ai_google_types if t in _TOURIST_GOOGLE_TYPES]
        if ai_google_types:
            try:
                google_body, google_count = await self._try_google_places_fallback(
                    ai_google_types, '', lang, message, prefs, city, profile, host, ctx,
                    keyword=" ".join(query_terms) if isinstance(query_terms, list) else (query_terms or None),
                )
                if google_body:
                    google_lines = ['', google_body]
                    self._skip_reply_scrub = True  # Google Places URLs have coords
            except Exception:
                pass
        
        if _is_practical and google_lines:
            body = "\n\n".join([l for l in google_lines if l])
            return self._ok(body, {"count": google_count, "source": "google_places"})

        if not guest_batch.recommendations:
            items = await self._fallback_recommendations(city, prefs, message, cats)
            if items:
                lines = [intro, ""]
                for i, item in enumerate(items, 1):
                    meta = ""
                    rating = item.get("rating")
                    if rating is not None:
                        meta += f" ⭐{rating:.1f}"
                        revs = item.get("reviews")
                        if revs:
                            meta += f" ({revs:,})"
                    maps_url = item.get("maps_url")
                    if maps_url:
                        label = _MAP_LINK_LABELS.get(lang, _MAP_LINK_LABELS["en"])
                        meta += f" · [📍 {label}]({maps_url})"
                    lines.append(f"{i}. **{item['title']}**{meta}\n   _{item['desc']}_")
                return self._ok("\n\n".join(lines), {"count": len(items), "source": "direct"})

            google_body, google_count = await self._try_google_places_fallback(
                ai_google_types or cats, intro, lang, message, prefs, city, profile, host, ctx,
                keyword=" ".join(query_terms) if isinstance(query_terms, list) else (query_terms or None),
            )
            if google_body:
                context["last_command"] = "guest_concierge"
                return self._ok(
                    google_body,
                    {"count": google_count, "source": "google_places"},
                )

            no_data = _NO_DATA_MSG.get(lang, _NO_DATA_MSG["en"]).format(city=city)
            return self._ok(f"{intro}\n\n{no_data}")

        lines = [intro]
        for i, r in enumerate(guest_batch.recommendations, 1):
            emoji = self._emoji_for_rec(r.title or "", prefs)
            lines.append(_format_concierge_rec_line(i, r, emoji, lang))
        if google_lines:
            lines.extend(google_lines)

        if any(
            r.attraction and r.attraction.google_maps_url
            for r in guest_batch.recommendations
        ):
            self._skip_reply_scrub = True

        context["last_command"] = "guest_concierge"
        return self._ok("\n\n".join(lines), {"count": len(guest_batch.recommendations)})

    async def _try_google_places_fallback(
        self,
        place_types: list,
        intro: str,
        lang: str,
        message: str,
        prefs: Dict[str, Any],
        city: str,
        profile: Optional[HostProfile],
        host: Host,
        ctx: Dict[str, Any],
        *,
        keyword: Optional[str] = None,
    ) -> tuple[Optional[str], int]:
        """Google Places nearby search when local DB has no matches."""
        logger.info(f"GP_FALLBACK: place_types={place_types!r} keyword={keyword!r}")
        if not place_types and not keyword:
            logger.info("GP_FALLBACK: empty types+keyword, skipping")
            return None, 0

        # Convert list to pipe-separated string for Google Places API
        if isinstance(place_types, list):
            place_types = '|'.join(place_types) if place_types else ''

        lat, lng = _resolve_guest_coordinates(ctx, profile, host)
        if lat is None or lng is None:
            logger.info(f"GP_FALLBACK: no coords (lat={lat}, lng={lng})")
            return None, 0

        svc = GooglePlacesEnrichmentService()
        if not svc.is_configured:
            logger.info("GP_FALLBACK: Google Places not configured")
            return None, 0

        try:
            logger.info(f"GP_FALLBACK: searching lat={lat},{lng} radius=20000 types={place_types!r} kw={keyword!r}")
            places = await svc.search_nearby(
                lat, lng, place_types, radius=20000, limit=5, keyword=keyword
            )
            logger.info(f"GP_FALLBACK: got {len(places)} places")
        except Exception as exc:
            logger.warning("Google Places fallback failed: %s", exc)
            return None, 0

        if not places:
            return None, 0

        try:
            partner_svc = PartnerService(self.db)
            vector_svc = VectorService(self.db, AIService())
            await partner_svc.persist_google_places_results(
                places,
                city=city,
                vector_service=vector_svc,
                google_svc=svc,
            )
        except Exception as exc:
            logger.warning("Failed to persist Google Places partners: %s", exc)

        google_intro = await generate_concierge_intro(prefs, message, lang, city)
        body = _format_google_places_results(places, lang, google_intro, lat, lng)
        return body, len(places)

    async def _personalized_intro(
        self,
        prefs: Dict[str, Any],
        message: str,
        language: str,
        city: str,
    ) -> str:
        return await generate_concierge_intro(prefs, message, language, city)

    @staticmethod
    def _emoji_for_rec(title: str, prefs: Dict[str, Any]) -> str:
        return _emoji_for_rec(title, prefs)


class GuestEventsAgent(BaseGuestAgent):
    agent_id = "guest-events-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        need = self._require_prefs(context)
        if need:
            return need

        if not self.db:
            return self._error("Baza podataka nije dostupna.")

        bundle = await self._load_bundle(context)
        if not bundle:
            return self._error("Sesija nije aktivna.")

        group, host, profile, ctx = bundle
        lang = _get_language(ctx)
        city = ctx.get("city") or (profile.city if profile else host.city) or "Kvarner"

        discovery = EventDiscoveryService(self.db)
        fresh = await discovery.ensure_fresh_events(
            city,
            region=profile.county if profile else None,
            host_id=str(host.id) if host else None,
            trigger_if_stale=True,
        )

        stmt = select(GuestPreference).where(GuestPreference.guest_group_id == group.id)
        result = await self.db.execute(stmt)
        db_prefs = list(result.scalars().all())

        ev_svc = EventRecommendationService(self.db)
        payload = await ev_svc.get_recommendations_for_access_code(
            group,
            host,
            profile,
            db_prefs,
            limit=8,
            bootstrap_if_empty=False,
        )
        payload = sanitize_event_recommendations_for_guest(payload)
        recs = payload.get("recommendations") or []

        if not recs:
            feed = EventsFeedService(self.db)
            check_in = group.check_in_date.date() if group.check_in_date else None
            check_out = group.check_out_date.date() if group.check_out_date else None
            events = await feed.get_local_events_batch(
                cities=[city],
                limit=10,
                stay_start=check_in,
                stay_end=check_out,
            )
            recs = sanitize_event_recommendations_for_guest(
                {"recommendations": events}
            ).get("recommendations") or []

        guest_tags = set(prefs_to_interests(ctx.get("guest_prefs")))
        check_in = group.check_in_date.date() if group.check_in_date else None
        check_out = group.check_out_date.date() if group.check_out_date else None

        if recs:
            recs = filter_events_by_preferences(
                recs,
                guest_text=message,
                guest_tags=guest_tags,
                check_in=check_in,
                check_out=check_out,
                city=city,
            )

        if not recs and fresh.get("discovery_triggered"):
            return self._ok(
                f"🔍 **Tražim događaje za {city}...**\n\n"
                "Provjeravam turističke izvore za vaš boravak.\n"
                "_Javit ćemo se uskoro s rezultatima — pokušajte ponovo za nekoliko minuta._"
            )

        if not recs:
            return self._ok(
                f"🎉 **Događaji — {city}**\n\n"
                "Trenutno nema događaja u bazi za vaš boravak.\n"
                "_Pokušajte kasnije ili pitajte domaćina._"
            )

        header = await generate_event_header(lang, city, len(recs[:8]))
        lines = [f"{header}\n"]
        for i, ev in enumerate(recs[:8], 1):
            if isinstance(ev, dict):
                title = ev.get("title") or ev.get("name") or "Događaj"
                loc = ev.get("city") or ev.get("location") or city
                start = ev.get("start_at") or ev.get("start_date") or ev.get("date") or ""
                desc = (ev.get("description") or ev.get("summary") or "")[:80]
                link = ev.get("url") or ev.get("source_url") or ""
                etype = ev.get("event_type") or ""
                venue = ev.get("venue_name") or ""
            else:
                title, loc, start, desc, link = "Događaj", city, "", "", ""
                etype, venue = "", ""

            if start and len(str(start)) > 10:
                start = str(start)[:10]
            link_line = f"\n   [Više info]({link})" if link else ""
            desc_line = f"\n   _{desc}_" if desc else ""
            type_line = f" | 🏷 {etype}" if etype else ""
            venue_line = f"\n   📌 {venue}" if venue else ""
            lines.append(
                f"{i}. **{title}**\n"
                f"   📍 {loc} | 📅 {start or 'uskoro'}{type_line}{desc_line}{venue_line}{link_line}"
            )

        if fresh.get("fresh_count", 0) > 0:
            lines.append(f"\n_Evo svježih događaja za {city}! 🎉_")

        context["last_command"] = "guest_events"
        return self._ok("\n\n".join(lines), {"count": len(recs), "freshness": fresh})


class GuestEmergencyAgent(BaseGuestAgent):
    agent_id = "guest-emergency-hfg"
    _skip_reply_scrub = True

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        host_phone = context.get("host_phone") or ""
        city = (context.get("city") or "default").lower()
        hospital_name, hospital_phone = _HOSPITAL_BY_CITY.get(
            city.split()[0] if city else "default",
            _HOSPITAL_BY_CITY["default"],
        )
        for key, val in _HOSPITAL_BY_CITY.items():
            if key in city:
                hospital_name, hospital_phone = val
                break

        host_name = context.get("host_name") or "domaćin"
        lines = [
            "⚠️ **Hitna pomoć i kontakti**\n",
            f"📞 **Domaćin ({host_name}):** {host_phone or '— (pitajte recepciju)'}",
            "**Hitna pomoć:** `112`",
            "**Hitna medicinska pomoć:** `194`",
            f"**Bolnica:** {hospital_name} — `{hospital_phone}`",
            (
                "\n💬 Želite poslati poruku domaćinu? "
                f"Nazovite **{host_phone or 'domaćina'}** ili napišite što ne radi — "
                "_obavijest domaćinu uskoro stiže putem aplikacije._"
            ),
        ]

        lines.append("\n_Ostanite mirni — ovi brojevi su uvijek dostupni._")
        context["last_command"] = "guest_emergency"
        return self._ok("\n".join(lines))


class GuestInfoAgent(BaseGuestAgent):
    agent_id = "guest-info-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not context.get("guest_group_id"):
            return self._error("Skenirajte QR kod s ulaznice.")

        bundle = await self._load_bundle(context)
        if not bundle:
            return self._error("Sesija nije aktivna.")

        group, host, profile, ctx = bundle
        offerings = build_host_offerings_payload(host, profile, "")
        stay = offerings.get("stay_info") or {}
        rules = stay.get("property_rules") or {}
        city = _guest_safe_city_label(stay.get("city") or host.city)

        intent = await ai_classify_info_intent(message or "")

        if intent == "wifi":
            wifi_name = rules.get("wifiName") or rules.get("wifi_name") or "—"
            wifi_pass = rules.get("wifiPassword") or rules.get("wifi_password") or "—"
            return self._ok(
                f"📶 **WiFi**\n\n"
                f"**Mreža:** `{wifi_name}`\n"
                f"**Lozinka:** `{wifi_pass}`"
            )

        if intent == "checkin":
            cin = rules.get("checkInTime") or rules.get("check_in") or "15:00"
            return self._ok(f"🕒 **Check-in:** od *{cin}*")

        if intent == "checkout":
            cout = rules.get("checkOutTime") or rules.get("check_out") or "10:00"
            return self._ok(f"🕒 **Check-out:** do *{cout}*")

        if intent == "rules":
            hr_rules = rules.get("houseRules") or rules.get("house_rules") or []
            if isinstance(hr_rules, list) and hr_rules:
                body = "\n".join(f"• {r}" for r in hr_rules)
            else:
                body = "_Nema posebnih pravila u sustavu — pitajte domaćina._"
            return self._ok(f"📋 **Kućni red**\n\n{body}")

        if intent == "parking":
            amenities = stay.get("amenities") or []
            has_parking = "parking" in [str(a).lower() for a in amenities]
            return self._ok(
                "🅿️ **Parking:** "
                + ("Dostupan kod objekta." if has_parking else "Pitajte domaćina za upute.")
            )

        if intent == "beach":
            lat = (offerings.get("location_info") or {}).get("coordinates", {}) or {}
            if lat.get("lat") and lat.get("lng"):
                maps = f"https://www.google.com/maps/search/plaža/@{lat['lat']},{lat['lng']},14z"
            else:
                maps = f"https://www.google.com/maps/search/plaža+{city.replace(' ', '+')}"
            return self._ok(
                f"🏖️ **Plaže u blizini**\n\n"
                f"[Otvori Google Maps — plaže kod {city}]({maps})"
            )

        if intent == "shopping":
            maps = f"https://www.google.com/maps/search/trgovina+{city.replace(' ', '+')}"
            return self._ok(
                f"🛒 **Najbliža trgovina**\n\n"
                f"[Google Maps — trgovine u {city}]({maps})"
            )

        if intent == "weather":
            cin = ctx.get("check_in") or "—"
            cout = ctx.get("check_out") or "—"
            loc = offerings.get("location_info") or {}
            coords = loc.get("coordinates") or {}
            lat = coords.get("lat")
            lng = coords.get("lng")
            if lat is None and profile is not None:
                lat = profile.latitude
            if lng is None and profile is not None:
                lng = profile.longitude
            if lat is None:
                lat = host.latitude
            if lng is None:
                lng = host.longitude

            forecast = await fetch_guest_weather_forecast(
                latitude=lat,
                longitude=lng,
                city=city,
            )
            if forecast:
                body = (
                    f"🌤️ **Vremenska prognoza — {city}**\n\n"
                    f"{forecast}\n\n"
                    f"Boravak: {cin} – {cout}"
                )
            else:
                body = (
                    f"🌤️ **Vremenska prognoza — {city}**\n\n"
                    f"{weather_fallback_links(city)}\n"
                    f"Boravak: {cin} – {cout}"
                )
            return self._ok(body)

        prop = stay.get("property_name") or ctx.get("property_name") or "Smještaj"
        raw_addr = stay.get("address") or host.address or city
        addr = scrub_contact_from_text(raw_addr) or raw_addr
        cin_t = rules.get("checkInTime") or "15:00"
        cout_t = rules.get("checkOutTime") or "10:00"
        context["last_command"] = "guest_info"
        return self._ok(
            f"ℹ️ **{prop}**\n\n"
            f"📍 {addr}, {city}\n"
            f"🕒 Check-in: *{cin_t}* | Check-out: *{cout_t}*\n\n"
            "Pitajte: *WiFi*, *parking*, *kućni red*, *kako do plaže*, *trgovina*, *vrijeme*."
        )


def build_all_guest_agents(db: Optional[AsyncSession]) -> List[BaseHFGAgent]:
    return [
        GuestWelcomeAgent(db),
        GuestConciergeAgent(db),
        GuestEventsAgent(db),
        GuestEmergencyAgent(db),
        GuestInfoAgent(db),
    ]
