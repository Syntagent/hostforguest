"""
Guest-facing host offerings payload: use property/stay location, not only Host.city.

Hosts often set business or registered city (e.g. Rijeka) while the accommodation is
in a nearby settlement (e.g. Oprić). Guest copy should prefer HostProfile location fields.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from app.models.host import Host, HostProfile

_COUNTRY_TOKENS = frozenset(
    {"croatia", "hrvatska", "hr", "slovenia", "slovenija", "italy", "italija", "austria"}
)


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


# DB migrations may force NOT NULL with sentinel values — treat as "no real address".
_PROFILE_ADDRESS_PLACEHOLDERS = frozenset(
    {
        "address not specified",
        "address not set",
        "unknown",
        "n/a",
        "na",
        "tbd",
        "-",
        "—",
    }
)


def _effective_property_address_line(
    profile: Optional[HostProfile], host: Host
) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (profile_line_or_none, fallback_host_line) for parsing stay settlement and display.

    Skips migration/default placeholders on host_profiles.address so Host.address or blobs can win.
    """
    pa = _norm(profile.address) if profile else None
    if pa and pa.casefold() in _PROFILE_ADDRESS_PLACEHOLDERS:
        pa = None
    ha = _norm(host.address)
    return pa, ha


def _strip_trailing_country_token(s: str) -> str:
    """Remove trailing country name from a single segment (e.g. 'Oprić Croatia' -> 'Oprić')."""
    t = s.strip().rstrip(",.")
    if not t:
        return t
    parts = t.rsplit(None, 1)
    if len(parts) == 2 and parts[1].strip().lower().rstrip(".") in _COUNTRY_TOKENS:
        return parts[0].strip().rstrip(",")
    low = t.lower().rstrip(".")
    for c in _COUNTRY_TOKENS:
        suf = f", {c}"
        if low.endswith(suf):
            return t[: -len(suf)].strip().rstrip(",")
        suf2 = f" {c}"
        if low.endswith(suf2):
            return t[: -len(suf2)].strip().rstrip(",")
    return t


def _settlement_from_hr_postal_anywhere(text: str) -> Optional[str]:
    """
    Croatian postal codes are 5 digits, often 51xxx / 52xxx on the coast.
    Match '51415 Oprić' or '51415 Oprić, Croatia' inside a longer string.
    """
    m = re.search(
        r"\b(5\d{4})\s+([A-Za-zČčĆćĐđŠšŽž][A-Za-zČčĆćĐđŠšŽža-zčćđšž\s-]{1,80}?)"
        r"(?=\s*(?:,|\s+(?:Croatia|Hrvatska|HR)\b)|\s*$)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    town = _strip_trailing_country_token(m.group(2).strip())
    return _norm(town)


def _settlement_from_comma_segments(raw: str) -> Optional[str]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    while parts and parts[-1].strip().lower() in _COUNTRY_TOKENS:
        parts.pop()
    if not parts:
        return None

    candidates: list[str] = []
    for p in parts:
        pl = p.strip()
        low = pl.lower()
        if not low:
            continue
        if low.isdigit():
            continue
        if re.fullmatch(r"\d{5}", low):
            continue
        m = re.match(r"^\d{5}\s+(.+)$", pl)
        if m:
            rest = _strip_trailing_country_token(m.group(1).strip())
            candidates.append(rest)
            continue
        candidates.append(pl)

    if not candidates:
        return None
    last = _norm(candidates[-1])
    if not last:
        return None
    # "71 Oprić" (house number + settlement, no postal) as a single comma segment
    m_house = re.match(r"^(\d{1,4}|[Bb]{1,2})\s+(.+)$", last)
    if m_house:
        inner = _norm(m_house.group(2))
        if inner and not inner[0].isdigit():
            return inner
    return last


def settlement_from_property_address(address: Optional[str]) -> Optional[str]:
    """
    Guest-facing settlement from property address lines.

    Examples:
    - "71, 51415, Oprić, Croatia" -> "Oprić"
    - "51415 Oprić Croatia" (no commas) -> "Oprić"
    - "Line 1\\n51415 Oprić, Croatia" -> "Oprić"

    Profile "City" may still be the municipality (e.g. Lovran) — use broader_city separately.
    """
    raw = _norm(address)
    if not raw:
        return None
    # Multiple lines often used for property address; scan full text for HR postal + settlement first.
    flat = re.sub(r"[\n\r]+", " ", raw.strip())
    from_postal = _settlement_from_hr_postal_anywhere(flat)
    if from_postal:
        return from_postal
    return _settlement_from_comma_segments(flat)


def _text_likely_has_address_cues(text: str) -> bool:
    """Skip marketing blurbs; keep lines that look like postal / multi-part addresses."""
    t = text.strip()
    if re.search(r"\b5\d{4}\b", t):
        return True
    if t.count(",") >= 2:
        return True
    return False


def align_guest_welcome_opening_line(
    welcome: Optional[str],
    stay_city: Optional[str],
    host_city: Optional[str],
) -> Optional[str]:
    """
    If the host wrote 'Welcome to Rijeka!' but resolved stay is Oprić, fix the opening line for guests only.
    """
    w = _norm(welcome)
    if not w or not stay_city or not host_city:
        return w
    if stay_city.casefold() == host_city.casefold():
        return w
    m = re.match(r"(?is)^(\s*welcome\s+to\s+)([^!\n]+)(!)", w)
    if not m:
        return w
    inner = m.group(2).strip()
    if inner.casefold() != host_city.casefold():
        return w
    rest = w[m.end() :]
    return f"{m.group(1)}{stay_city}{m.group(3)}{rest}"


def resolve_guest_stay_city(host: Host, profile: Optional[HostProfile]) -> Optional[str]:
    """
    Where guests physically stay: parse profile address first, then other fields that often
    hide '51415 Oprić' (location_story, welcome_message, host description), then cities.
    """
    profile_addr, host_addr = _effective_property_address_line(profile, host)
    if profile_addr:
        s = settlement_from_property_address(profile_addr)
        if s:
            return s
    # Host.address is often a short label ("Rijeka HQ"); only parse when it looks like a property line.
    if host_addr and _text_likely_has_address_cues(host_addr):
        s = settlement_from_property_address(host_addr)
        if s:
            return s
    if profile_addr and host_addr and profile_addr != host_addr:
        combo = f"{profile_addr}, {host_addr}"
        s = settlement_from_property_address(combo)
        if s:
            return s

    extra_blobs: list[Optional[str]] = []
    if profile:
        extra_blobs.append(_norm(getattr(profile, "location_story", None)))
    extra_blobs.append(host_addr)
    extra_blobs.append(_norm(host.welcome_message))
    extra_blobs.append(_norm(getattr(host, "description", None)))

    for t in extra_blobs:
        if not t or t == profile_addr:
            continue
        if not _text_likely_has_address_cues(t):
            continue
        s = settlement_from_property_address(t)
        if s:
            return s

    # Legacy: property line only on Host.address while profile.address is empty/placeholder.
    if not profile_addr:
        ha = host_addr
        if ha and ("," in ha or re.search(r"\b5\d{4}\b", ha)):
            from_host_addr = settlement_from_property_address(ha)
            if from_host_addr:
                hc = (_norm(host.city) or "").casefold()
                if not hc or from_host_addr.casefold() != hc:
                    return from_host_addr

    pc = _norm(profile.city) if profile else None
    if pc:
        return pc
    return _norm(host.city)


def resolve_guest_stay_coordinates(
    host: Host, profile: Optional[HostProfile]
) -> Tuple[Optional[float], Optional[float]]:
    """Property pins on map: prefer profile coordinates when present."""
    if profile is not None and profile.latitude is not None and profile.longitude is not None:
        return profile.latitude, profile.longitude
    return host.latitude, host.longitude


def build_host_offerings_payload(
    host: Host,
    profile: Optional[HostProfile],
    access_code: str,
) -> Dict[str, Any]:
    """
    Same shape for GET guest-groups/.../host-offerings and onboarding guest-access.
    """
    stay_city = resolve_guest_stay_city(host, profile)
    profile_city = _norm(profile.city) if profile else None
    region = _norm(profile.county) if profile and profile.county else _norm(host.county)
    lat, lng = resolve_guest_stay_coordinates(host, profile)
    host_city = _norm(host.city)
    # Municipality / admin city when it differs from the address settlement (e.g. Lovran vs Oprić).
    broader_city = None
    if stay_city:
        if profile_city and profile_city.casefold() != stay_city.casefold():
            broader_city = profile_city
        elif (
            host_city
            and host_city.casefold() != stay_city.casefold()
            and (not profile_city or profile_city.casefold() == stay_city.casefold())
        ):
            broader_city = host_city

    welcome = _norm(host.welcome_message)
    welcome = align_guest_welcome_opening_line(welcome, stay_city, host_city)
    property_name = _norm(profile.property_name) if profile else None
    _pa, _ha = _effective_property_address_line(profile, host)
    property_address = _pa or _ha
    if not welcome:
        if property_name and stay_city:
            welcome = f"Welcome to {property_name} in {stay_city}!"
        elif property_name:
            welcome = f"Welcome to {property_name}!"
        elif stay_city:
            welcome = f"Welcome to {stay_city}!"
        else:
            welcome = "Welcome! I'm excited to help you discover the best of our area."

    amenities: list = []
    if profile and profile.amenities:
        amenities = list(profile.amenities) if isinstance(profile.amenities, list) else []

    max_guests_stay = None
    if profile and profile.max_guests is not None:
        max_guests_stay = profile.max_guests
    elif host.max_group_size is not None:
        max_guests_stay = host.max_group_size

    property_rules: Dict[str, Any] = {}
    if profile and getattr(profile, "property_rules", None):
        raw_rules = profile.property_rules
        if isinstance(raw_rules, dict):
            property_rules = raw_rules

    gallery_images: list = []
    if profile and profile.gallery_images:
        gallery_images = list(profile.gallery_images) if isinstance(profile.gallery_images, list) else []

    services_offered: list = []
    if profile and profile.services_offered:
        services_offered = list(profile.services_offered) if isinstance(profile.services_offered, list) else []

    trusted_partners: list = []
    if profile and profile.trusted_partners:
        trusted_partners = list(profile.trusted_partners) if isinstance(profile.trusted_partners, list) else []

    special_offers: list = []
    if profile and profile.special_offers:
        special_offers = list(profile.special_offers) if isinstance(profile.special_offers, list) else []

    host_offerings: Dict[str, Any] = {
        "stay_info": {
            "property_name": property_name,
            "property_type": getattr(profile, "property_type", None) if profile else None,
            "number_of_rooms": getattr(profile, "number_of_rooms", None) if profile else None,
            "address": property_address,
            "city": stay_city or host_city,
            "region": region,
            "amenities": amenities,
            "services_offered": services_offered,
            "gallery_images": gallery_images,
            "property_rules": property_rules,
            "max_guests": max_guests_stay,
        },
        "host_info": {
            "name": f"{host.first_name or ''} {host.last_name or ''}".strip() or "Your host",
            "city": stay_city or host_city,
            "broader_city": broader_city,
            "welcome_message": welcome,
            "languages": host.languages,
            "local_specialties": host.local_specialties or [],
            "business_type": host.business_type,
        },
        "location_info": {
            "city": stay_city or host_city,
            "region": region,
            "coordinates": (
                {"lat": lat, "lng": lng}
                if lat is not None and lng is not None
                else None
            ),
            "verified_location": lat is not None and lng is not None,
        },
        "recommendations": {
            "attractions": profile.favorite_local_spots if profile and profile.favorite_local_spots else [],
            "expertise_areas": profile.expertise_areas if profile and profile.expertise_areas else [],
            "local_tips": host.local_tips or [],
        },
        "guest_services": {
            "max_group_size": host.max_group_size,
            "typical_stay_duration": host.typical_stay_duration,
            "supported_languages": host.languages,
            "ai_powered": True,
            "personalized_recommendations": True,
        },
        "contact": {
            "can_message_host": True,
            "response_time": "Usually within 2 hours",
            "ai_assistant_available": True,
        },
        "metadata": {
            "access_code": access_code,
            "last_updated": profile.updated_at.isoformat() if profile and profile.updated_at else None,
            "profile_completed": bool(profile and getattr(profile, "onboarding_completed", False)),
        },
    }
    if profile:
        host_offerings["profile_extras"] = {
            "property_name": getattr(profile, "property_name", None),
            "location_story": getattr(profile, "location_story", None),
            "guest_testimonials": getattr(profile, "guest_testimonials", None) or [],
            "profile_image_url": getattr(profile, "profile_image_url", None),
        }
    if trusted_partners:
        host_offerings["trusted_partners"] = trusted_partners
    if special_offers:
        host_offerings["special_offers"] = special_offers
    return host_offerings
