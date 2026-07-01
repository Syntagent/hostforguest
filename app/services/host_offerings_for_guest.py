"""
Guest-facing host offerings payload: use property/stay location, not only Host.city.

Hosts often set business or registered city (e.g. Rijeka) while the accommodation is
in a nearby settlement (e.g. Oprić). Guest copy should prefer HostProfile location fields.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.host import Host, HostProfile

_COUNTRY_TOKENS = frozenset(
    {"croatia", "hrvatska", "hr", "slovenia", "slovenija", "italy", "italija", "austria"}
)

_TRUSTED_PARTNER_SAFE_KEYS = (
    "name",
    "title",
    "description",
    "note",
    "category",
    "partner_type",
    "service",
)

_SPECIAL_OFFER_SAFE_KEYS = (
    "name",
    "title",
    "label",
    "description",
    "note",
    "discount",
    "valid_until",
)

_FAVORITE_SPOT_SAFE_KEYS = (
    "name",
    "description",
    "type",
    "category",
    "distance_km",
)

_GUEST_TESTIMONIAL_SAFE_KEYS = (
    "quote",
    "text",
    "message",
    "body",
    "review",
    "content",
    "author",
    "name",
    "guest_name",
    "from",
    "by",
    "rating",
)

_PROPERTY_RULES_SAFE_KEYS = (
    "checkInTime",
    "checkOutTime",
    "cancellationPolicy",
    "houseRules",
    "additionalPolicies",
    "wifiName",
    "wifiPassword",
    "emergencyNote",
)

_LOCAL_TIP_SAFE_KEYS = (
    "text",
    "title",
    "tip",
    "description",
    "category",
    "name",
)

_SERVICE_OFFERED_SAFE_KEYS = (
    "name",
    "title",
    "label",
    "description",
    "service",
    "category",
)

_GALLERY_IMAGE_SAFE_KEYS = (
    "url",
    "src",
    "image_url",
    "caption",
    "alt",
    "title",
)

_AMENITY_SAFE_KEYS = (
    "name",
    "title",
    "label",
    "description",
    "category",
)

_EXPERTISE_AREA_SAFE_KEYS = (
    "name",
    "title",
    "label",
    "description",
    "category",
)

_LOCAL_SPECIALTY_SAFE_KEYS = (
    "name",
    "title",
    "label",
    "description",
    "category",
)

_HOST_MESSAGE_SAFE_KEYS = (
    "message",
    "host_name",
)

_CONTACT_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_CONTACT_PHONE_RE = re.compile(
    r"(?:"
    r"\+[\d][\d\s().-]{7,17}\d"
    r"|"
    r"(?<!\d)(?:\d[\d\s().-]{7,17}\d)(?!\d)"
    r")"
)
_CONTACT_URL_RE = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+", re.IGNORECASE)
_CONTACT_REMOVED = "[contact removed]"


def scrub_contact_from_text(text: Optional[str], *, scrub_urls: bool = False) -> Optional[str]:
    """Redact inline email and phone patterns from guest-facing free text."""
    if text is None:
        return None
    t = str(text)
    if not t.strip():
        return t
    t = _CONTACT_EMAIL_RE.sub(_CONTACT_REMOVED, t)
    t = _CONTACT_PHONE_RE.sub(_CONTACT_REMOVED, t)
    if scrub_urls:
        t = _CONTACT_URL_RE.sub(_CONTACT_REMOVED, t)
    return t


def _scrub_safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_contact_from_text(value)
    if isinstance(value, list):
        return [_scrub_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_safe_value(item) for key, item in value.items()}
    return value


def _scrub_opening_hours(opening: Any) -> Dict[str, Any]:
    if not isinstance(opening, dict):
        return {}
    scrubbed: Dict[str, Any] = {}
    for key, value in opening.items():
        clean_key = scrub_contact_from_text(str(key)) or str(key)
        clean_value = scrub_contact_from_text(str(value)) if value is not None else value
        scrubbed[clean_key] = clean_value
    return scrubbed


def _guest_safe_best_months(raw: Any) -> List[int]:
    """Guest/public month lists allow integers only; drop poisoned string JSON."""
    if not isinstance(raw, list):
        return []
    safe: List[int] = []
    for item in raw:
        if isinstance(item, int) and 1 <= item <= 12:
            safe.append(item)
    return safe


def _guest_safe_language_code(value: Any) -> str:
    """Scrub poisoned language codes; fall back to en when redaction exceeds max length."""
    if value is None:
        return "en"
    original = str(value)
    scrubbed = scrub_contact_from_text(original) or ""
    if (
        scrubbed != original
        and "[contact removed]" in scrubbed
    ) or len(scrubbed) > 10:
        return "en"
    return scrubbed or "en"


def guest_safe_attraction_review_public(review: Any):
    """Scrub inline contact from public attraction review text fields."""
    from app.models.attraction import AttractionReviewPublicResponse

    payload = AttractionReviewPublicResponse.model_validate(review)
    data = payload.model_dump()
    for key in (
        "title",
        "review_text",
        "tips_for_others",
        "response_from_host",
    ):
        data[key] = scrub_contact_from_text(data.get(key))
    data.pop("visit_duration", None)
    data["language"] = _guest_safe_language_code(data.get("language"))
    data["pros"] = _scrub_safe_value(data.get("pros") or [])
    data["cons"] = _scrub_safe_value(data.get("cons") or [])
    for internal_key in (
        "helpfulness_score",
        "helpful_votes",
        "total_votes",
        "guest_age_group",
        "guest_travel_style",
        "visit_date",
        "group_size",
        "verified_visit",
        "host_response_at",
        "created_at",
    ):
        data.pop(internal_key, None)
    return AttractionReviewPublicResponse(**data)


def guest_safe_attraction_public(attraction: Any):
    """Scrub inline contact from public attraction listing fields."""
    from app.models.attraction import AttractionPublicResponse

    if isinstance(attraction, dict):
        raw_months = attraction.get("best_months")
        validate_target = dict(attraction)
        if raw_months and any(not isinstance(m, int) for m in raw_months):
            validate_target["best_months"] = _guest_safe_best_months(raw_months)
    else:
        raw_months = getattr(attraction, "best_months", None)
        if raw_months and any(not isinstance(m, int) for m in raw_months):
            validate_target = {
                field: getattr(attraction, field)
                for field in AttractionPublicResponse.model_fields
                if hasattr(attraction, field)
            }
            validate_target["best_months"] = _guest_safe_best_months(raw_months)
        else:
            validate_target = attraction
    payload = AttractionPublicResponse.model_validate(validate_target)
    data = payload.model_dump()
    for key in (
        "name",
        "description",
        "short_description",
        "address",
        "admission_fee",
        "seasonal_notes",
        "group_size_recommendation",
        "city",
        "region",
        "county",
        "seasonal_availability",
        "attraction_type",
        "difficulty_level",
    ):
        data[key] = scrub_contact_from_text(data.get(key))
    for internal_key in (
        "status",
        "view_count",
        "recommendation_count",
        "created_at",
        "updated_at",
        "published_at",
    ):
        data.pop(internal_key, None)
    data["category_tags"] = _scrub_safe_value(data.get("category_tags") or [])
    data["best_months"] = _guest_safe_best_months(data.get("best_months") or [])
    data["featured_image_url"] = scrub_contact_from_text(
        data.get("featured_image_url"), scrub_urls=True
    )
    data["image_gallery"] = [
        scrub_contact_from_text(str(u), scrub_urls=True) or str(u)
        for u in (data.get("image_gallery") or [])
    ]
    opening = data.get("opening_hours") or {}
    if isinstance(opening, dict):
        data["opening_hours"] = _scrub_opening_hours(opening)
    return AttractionPublicResponse(**data)


def guest_safe_host_contribution_public(contribution: Any):
    """Scrub inline contact from public host contribution text fields."""
    from app.models.attraction import HostContributionPublicResponse

    payload = HostContributionPublicResponse.model_validate(contribution)
    data = payload.model_dump(exclude={"host_id"})
    for key in ("title", "content", "contribution_type"):
        data[key] = scrub_contact_from_text(data.get(key))
    data["language"] = _guest_safe_language_code(data.get("language"))
    for internal_key in ("is_public", "created_at", "updated_at"):
        data.pop(internal_key, None)
    return HostContributionPublicResponse(**data)


def guest_safe_seasonal_event_public(event: Any):
    """Scrub inline contact from public seasonal event listing fields."""
    from app.models.attraction import SeasonalEventPublicResponse

    payload = SeasonalEventPublicResponse.model_validate(event)
    data = payload.model_dump()
    for key in (
        "name",
        "description",
        "location",
        "venue_details",
        "what_to_expect",
        "admission_info",
        "time_of_day",
        "recurring_pattern",
        "city",
        "event_type",
    ):
        data[key] = scrub_contact_from_text(data.get(key))
    for internal_key in ("status", "is_active", "created_at", "updated_at"):
        data.pop(internal_key, None)
    return SeasonalEventPublicResponse(**data)


def guest_safe_host_public(host: Any):
    """Scrub inline contact from public host directory text fields."""
    from app.models.host import HostPublicResponse

    payload = HostPublicResponse.model_validate(host)
    data = payload.model_dump()
    for key in (
        "business_name",
        "description",
        "welcome_message",
        "first_name",
        "last_name",
        "city",
        "county",
        "country",
        "business_type",
    ):
        data[key] = scrub_contact_from_text(data.get(key))
    data["local_specialties"] = _scrub_safe_value(data.get("local_specialties") or [])
    data["languages"] = _scrub_safe_value(data.get("languages") or [])
    for internal_key in (
        "is_active",
        "is_verified",
        "subscription_tier",
        "total_guest_groups",
        "created_at",
        "updated_at",
    ):
        data.pop(internal_key, None)
    return HostPublicResponse(**data)


def guest_safe_realtime_update(
    row: Dict[str, Any],
    *,
    omit_internal_scores: bool = True,
) -> Dict[str, Any]:
    """Scrub inline contact from anonymous realtime tourism feed items."""
    data = dict(row)
    for key in (
        "title",
        "content",
        "description",
        "price",
        "address",
        "venue_name",
        "url",
        "city",
        "region",
        "source",
        "source_name",
        "event_type",
        "age_group",
        "content_type",
    ):
        if key in data and data[key] is not None:
            scrub_urls = key == "url"
            data[key] = scrub_contact_from_text(str(data[key]), scrub_urls=scrub_urls)
    if data.get("language") is not None:
        data["language"] = _guest_safe_language_code(data["language"])
    for key in ("relevant_cities", "relevant_regions", "keywords", "tags"):
        if key in data and data[key] is not None:
            data[key] = _scrub_safe_value(data[key])
    if data.get("recurrence") is not None:
        data["recurrence"] = _scrub_safe_value(data["recurrence"])
    if omit_internal_scores:
        for key in (
            "quality_score",
            "relevance_score",
            "is_demo_seed",
            "created_at",
            "lat",
            "lng",
            "scraped_at",
            "tags",
            "is_recurring",
            "price",
            "address",
            "city",
            "region",
            "event_type",
            "age_group",
            "language",
            "recurrence",
            "source",
            "source_name",
            "content_type",
            "description",
        ):
            data.pop(key, None)
    return data


def guest_safe_location_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub inline contact from location detail narrative fields for non-owners."""
    data = dict(details)
    for key in (
        "title",
        "description",
        "price",
        "accessibility_info",
        "seasonal_availability",
        "location",
        "category",
        "difficulty_level",
    ):
        if key in data:
            data[key] = scrub_contact_from_text(data.get(key))
    if data.get("image") is not None:
        data["image"] = scrub_contact_from_text(str(data["image"]), scrub_urls=True)
    opening = data.get("opening_hours")
    if isinstance(opening, dict):
        data["opening_hours"] = _scrub_opening_hours(opening)
    if "best_months" in data:
        data["best_months"] = _guest_safe_best_months(data.get("best_months") or [])
    return data


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _guest_safe_trusted_partner(entry: Any) -> Any:
    """Guest host-offerings: allowlist partner cards; drop contact PII."""
    if isinstance(entry, str):
        return _scrub_safe_value(entry)
    if not isinstance(entry, dict):
        return entry
    safe: Dict[str, Any] = {}
    for key in _TRUSTED_PARTNER_SAFE_KEYS:
        if key in entry and entry[key] is not None:
            safe[key] = _scrub_safe_value(entry[key])
    return safe or {"name": "Partner"}


def _guest_safe_trusted_partners(raw: list) -> list:
    return [_guest_safe_trusted_partner(item) for item in raw]


def _guest_safe_dict_entry(entry: Any, safe_keys: tuple[str, ...], fallback: Dict[str, Any]) -> Any:
    """Guest host-offerings: allowlist dict entries; drop contact PII."""
    if isinstance(entry, str):
        return _scrub_safe_value(entry)
    if not isinstance(entry, dict):
        return entry
    safe: Dict[str, Any] = {}
    for key in safe_keys:
        if key in entry and entry[key] is not None:
            safe[key] = _scrub_safe_value(entry[key])
    return safe or fallback


def _guest_safe_special_offer(entry: Any) -> Any:
    return _guest_safe_dict_entry(entry, _SPECIAL_OFFER_SAFE_KEYS, {"title": "Special offer"})


def _guest_safe_special_offers(raw: list) -> list:
    return [_guest_safe_special_offer(item) for item in raw]


def _guest_safe_favorite_spot(entry: Any) -> Any:
    return _guest_safe_dict_entry(entry, _FAVORITE_SPOT_SAFE_KEYS, {"name": "Local spot"})


def _guest_safe_favorite_spots(raw: list) -> list:
    return [_guest_safe_favorite_spot(item) for item in raw]


def _guest_safe_testimonial(entry: Any) -> Any:
    return _guest_safe_dict_entry(entry, _GUEST_TESTIMONIAL_SAFE_KEYS, {"text": "Guest review"})


def _guest_safe_testimonials(raw: list) -> list:
    return [_guest_safe_testimonial(item) for item in raw]


def _guest_safe_property_rules(raw: Any) -> Dict[str, Any]:
    """Guest host-offerings: allowlist property_rules; drop contact PII."""
    if not isinstance(raw, dict):
        return {}
    safe: Dict[str, Any] = {}
    for key in _PROPERTY_RULES_SAFE_KEYS:
        if key in raw and raw[key] is not None:
            safe[key] = _scrub_safe_value(raw[key])
    return safe


def _guest_safe_local_tip(entry: Any) -> Any:
    return _guest_safe_dict_entry(entry, _LOCAL_TIP_SAFE_KEYS, {"text": "Local tip"})


def _guest_safe_local_tips(raw: list) -> list:
    return [_guest_safe_local_tip(item) for item in raw]


def _guest_safe_service_offered(entry: Any) -> Any:
    return _guest_safe_dict_entry(entry, _SERVICE_OFFERED_SAFE_KEYS, {"title": "Service"})


def _guest_safe_services_offered(raw: list) -> list:
    return [_guest_safe_service_offered(item) for item in raw]


_GALLERY_IMAGE_URL_KEYS = frozenset({"url", "src", "image_url"})


def _guest_safe_gallery_image(entry: Any) -> Any:
    if isinstance(entry, str):
        return scrub_contact_from_text(entry, scrub_urls=True) or entry
    if not isinstance(entry, dict):
        return entry
    safe: Dict[str, Any] = {}
    for key in _GALLERY_IMAGE_SAFE_KEYS:
        if key not in entry or entry[key] is None:
            continue
        if key in _GALLERY_IMAGE_URL_KEYS:
            safe[key] = scrub_contact_from_text(str(entry[key]), scrub_urls=True) or entry[key]
        else:
            safe[key] = _scrub_safe_value(entry[key])
    return safe or {"url": "Photo"}


def _guest_safe_gallery_images(raw: list) -> list:
    return [_guest_safe_gallery_image(item) for item in raw]


def _guest_safe_amenity(entry: Any) -> Any:
    if isinstance(entry, str):
        return _scrub_safe_value(entry)
    return _guest_safe_dict_entry(entry, _AMENITY_SAFE_KEYS, {"name": "Amenity"})


def _guest_safe_amenities(raw: list) -> list:
    return [_guest_safe_amenity(item) for item in raw]


def _guest_safe_expertise_area(entry: Any) -> Any:
    if isinstance(entry, str):
        return _scrub_safe_value(entry)
    return _guest_safe_dict_entry(entry, _EXPERTISE_AREA_SAFE_KEYS, {"name": "Expertise"})


def _guest_safe_expertise_areas(raw: list) -> list:
    return [_guest_safe_expertise_area(item) for item in raw]


def _guest_safe_local_specialty(entry: Any) -> Any:
    if isinstance(entry, str):
        return _scrub_safe_value(entry)
    return _guest_safe_dict_entry(entry, _LOCAL_SPECIALTY_SAFE_KEYS, {"name": "Specialty"})


def _guest_safe_local_specialties(raw: list) -> list:
    return [_guest_safe_local_specialty(item) for item in raw]


def _guest_safe_host_message(entry: Any) -> Any:
    if isinstance(entry, str):
        return scrub_contact_from_text(entry, scrub_urls=True) or entry
    if not isinstance(entry, dict):
        return entry
    safe: Dict[str, Any] = {}
    for key in _HOST_MESSAGE_SAFE_KEYS:
        if key in entry and entry[key] is not None:
            value = entry[key]
            if key == "message":
                value = scrub_contact_from_text(str(value), scrub_urls=True)
            elif key in {"host_name", "sent_at"}:
                value = scrub_contact_from_text(str(value))
            safe[key] = value
    return safe or {"message": "Host message"}


def guest_safe_host_messages(raw: list) -> list:
    """Guest host-offerings: allowlist host broadcast cards; drop contact/tenant PII."""
    return [_guest_safe_host_message(item) for item in raw]


def attach_host_broadcast_messages(
    host_offerings: Dict[str, Any],
    seasonal_preferences: Any,
) -> None:
    """Attach sanitized host broadcast cards from guest-group seasonal_preferences."""
    if not isinstance(seasonal_preferences, dict):
        return
    host_messages = seasonal_preferences.get("host_broadcast_messages")
    if not host_messages:
        return
    message_list = list(host_messages) if isinstance(host_messages, list) else []
    host_offerings["host_messages"] = guest_safe_host_messages(message_list)


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

    welcome = scrub_contact_from_text(_norm(host.welcome_message), scrub_urls=True)
    welcome = align_guest_welcome_opening_line(welcome, stay_city, host_city)
    property_name = scrub_contact_from_text(_norm(profile.property_name) if profile else None)
    _pa, _ha = _effective_property_address_line(profile, host)
    property_address = scrub_contact_from_text(_pa or _ha)
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
        amenity_list = list(profile.amenities) if isinstance(profile.amenities, list) else []
        amenities = _guest_safe_amenities(amenity_list)

    max_guests_stay = None
    if profile and profile.max_guests is not None:
        max_guests_stay = profile.max_guests
    elif host.max_group_size is not None:
        max_guests_stay = host.max_group_size

    property_rules: Dict[str, Any] = {}
    if profile and getattr(profile, "property_rules", None):
        raw_rules = profile.property_rules
        if isinstance(raw_rules, dict):
            property_rules = _guest_safe_property_rules(raw_rules)

    gallery_images: list = []
    raw_gallery = getattr(profile, "gallery_images", None) if profile else None
    if raw_gallery:
        gallery_list = list(raw_gallery) if isinstance(raw_gallery, list) else []
        gallery_images = _guest_safe_gallery_images(gallery_list)

    services_offered: list = []
    raw_services = getattr(profile, "services_offered", None) if profile else None
    if raw_services:
        service_list = list(raw_services) if isinstance(raw_services, list) else []
        services_offered = _guest_safe_services_offered(service_list)

    trusted_partners: list = []
    raw_partners = getattr(profile, "trusted_partners", None) if profile else None
    if raw_partners:
        partner_list = list(raw_partners) if isinstance(raw_partners, list) else []
        trusted_partners = _guest_safe_trusted_partners(partner_list)

    special_offers: list = []
    raw_offers = getattr(profile, "special_offers", None) if profile else None
    if raw_offers:
        offer_list = list(raw_offers) if isinstance(raw_offers, list) else []
        special_offers = _guest_safe_special_offers(offer_list)

    display_city = scrub_contact_from_text(stay_city or host_city)
    display_region = scrub_contact_from_text(region)
    display_broader_city = scrub_contact_from_text(broader_city)
    host_display_name = (
        scrub_contact_from_text(f"{host.first_name or ''} {host.last_name or ''}".strip())
        or "Your host"
    )

    host_offerings: Dict[str, Any] = {
        "stay_info": {
            "property_name": property_name,
            "property_type": scrub_contact_from_text(
                getattr(profile, "property_type", None) if profile else None
            ),
            "number_of_rooms": getattr(profile, "number_of_rooms", None) if profile else None,
            "address": property_address,
            "city": display_city,
            "region": display_region,
            "amenities": amenities,
            "services_offered": services_offered,
            "gallery_images": gallery_images,
            "property_rules": property_rules,
            "max_guests": max_guests_stay,
        },
        "host_info": {
            "name": host_display_name,
            "city": display_city,
            "broader_city": display_broader_city,
            "welcome_message": welcome,
            "languages": _scrub_safe_value(
                list(host.languages) if isinstance(host.languages, list) else []
            ),
            "local_specialties": (
                _guest_safe_local_specialties(
                    list(host.local_specialties) if isinstance(host.local_specialties, list) else []
                )
                if host.local_specialties
                else []
            ),
            "business_type": scrub_contact_from_text(host.business_type),
        },
        "location_info": {
            "city": display_city,
            "region": display_region,
            "coordinates": (
                {"lat": lat, "lng": lng}
                if lat is not None and lng is not None
                else None
            ),
            "verified_location": lat is not None and lng is not None,
        },
        "recommendations": {
            "attractions": (
                _guest_safe_favorite_spots(
                    list(profile.favorite_local_spots)
                    if isinstance(profile.favorite_local_spots, list)
                    else []
                )
                if profile and profile.favorite_local_spots
                else []
            ),
            "expertise_areas": (
                _guest_safe_expertise_areas(
                    list(profile.expertise_areas)
                    if isinstance(profile.expertise_areas, list)
                    else []
                )
                if profile and profile.expertise_areas
                else []
            ),
            "local_tips": (
                _guest_safe_local_tips(
                    list(host.local_tips) if isinstance(host.local_tips, list) else []
                )
                if host.local_tips
                else []
            ),
        },
        "guest_services": {
            "supported_languages": _scrub_safe_value(
                list(host.languages) if isinstance(host.languages, list) else []
            ),
        },
        "contact": {
            "can_message_host": True,
        },
        "metadata": {
            "access_code": access_code,
        },
    }
    if profile:
        raw_testimonials = getattr(profile, "guest_testimonials", None) or []
        testimonial_list = (
            list(raw_testimonials) if isinstance(raw_testimonials, list) else []
        )
        host_offerings["profile_extras"] = {
            "property_name": scrub_contact_from_text(getattr(profile, "property_name", None)),
            "location_story": scrub_contact_from_text(
                getattr(profile, "location_story", None), scrub_urls=True
            ),
            "guest_testimonials": _guest_safe_testimonials(testimonial_list),
            "profile_image_url": scrub_contact_from_text(
                getattr(profile, "profile_image_url", None), scrub_urls=True
            ),
        }
    if trusted_partners:
        host_offerings["trusted_partners"] = trusted_partners
    if special_offers:
        host_offerings["special_offers"] = special_offers
    return host_offerings
