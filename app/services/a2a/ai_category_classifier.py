"""
AI-powered category and Google Places type classifier.
Uses DeepSeek to intelligently classify guest messages into
categories AND specific Google Place Types — no hardcoded mappings.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Available Google Place Types (subset most relevant to tourism) ──────────
# Full list: https://developers.google.com/maps/documentation/places/web-service/place-types
_GOOGLE_PLACE_TYPES = [
    "grocery_or_supermarket", "supermarket", "convenience_store", "bakery",
    "liquor_store", "shopping_mall", "store", "market",
    "pharmacy", "bank", "atm", "post_office", "hospital",
    "bus_station", "train_station", "taxi_stand", "parking", "car_rental",
    "gas_station", "airport", "ferry_terminal",
    "restaurant", "cafe", "bar", "wine_bar", "night_club",
    "spa", "beauty_salon", "hair_care", "gym",
    "museum", "art_gallery", "church", "mosque", "synagogue", "hindu_temple",
    "park", "tourist_attraction", "zoo", "aquarium", "amusement_park",
    "beach", "campground", "rv_park",
    "lodging", "hotel", "motel",
]

_VALID_INFO_INTENTS = frozenset({
    "wifi", "checkin", "checkout", "rules", "parking", "beach", "shopping", "weather", "general",
})

_VALID_PREFERENCE_TAGS = frozenset({
    "wine", "food", "beach", "culture", "nature", "family", "children",
    "nightlife", "animals", "relaxation", "general",
})

_VALID_FOOD_TYPES = frozenset({
    "burger", "pizza", "seafood", "steak", "pasta", "sushi", "kebab",
    "ice_cream", "general",
})

_VALID_AMBIANCE = frozenset({
    "seaside", "terrace", "romantic", "family", "casual", "fine_dining",
    "garden", "view",
})

_VALID_PRICE_PREFERENCES = frozenset({"budget", "moderate", "premium"})

_VALID_CUISINES = frozenset({
    "mediterranean", "italian", "american", "asian", "barbecue", "croatian", "general",
})

_FOOD_TYPE_SEARCH_TERMS: Dict[str, List[str]] = {
    "burger": ["burger", "hamburger"],
    "pizza": ["pizza"],
    "seafood": ["seafood", "riba", "fish", "riba"],
    "steak": ["steak", "meso", "beef"],
    "pasta": ["pasta", "tjestenina"],
    "sushi": ["sushi"],
    "kebab": ["kebab", "cevap", "ćevap"],
    "ice_cream": ["ice cream", "sladoled", "gelato"],
}

CATEGORY_SYSTEM_PROMPT = f"""You are a smart concierge classifier for food, dining, and tourism queries.
Given a guest's message, return a JSON object with ALL of these fields:

- "food_type": one of burger|pizza|seafood|steak|pasta|sushi|kebab|ice_cream|general|null
  Set when the guest mentions a specific food. null if not a food query.
- "ambiance": one of seaside|terrace|romantic|family|casual|fine_dining|garden|view|null
  Use compound values with "+" when multiple apply (e.g. "romantic+view", "seaside+terrace").
- "price_preference": one of budget|moderate|premium|null
  budget = cheap/jeftino/günstig/billig; moderate = good/fair/dobar; premium = romantic/fine/luxury.
- "cuisine": one of mediterranean|italian|american|asian|barbecue|croatian|general|null
- "categories": list of 1-3 general categories from [dining, beach, cultural, sightseeing, nature, activity, relaxation, wine, shopping, services, transport]
- "google_place_types": list of 1-3 SPECIFIC Google Place Types from: {', '.join(_GOOGLE_PLACE_TYPES)}
- "max_price_level": integer 0 (free) to 4 (very expensive), or null. Set 1 only for explicit budget/cheap requests.
- "query_terms": array of 1-4 FOOD/PLACE keywords in Croatian + English. ONLY food names, NO price words (jeftino, budget, cheap) and NO ambiance words. E.g. "ribice": ["riba", "riblji", "fish", "seafood"]. "hal": ["hal", "riba", "fish"]. "hamburger": ["hamburger", "burger"]. null if not applicable.
- "confidence": float 0.0-1.0

Examples:
- "dobar hamburger uz more" → food_type="burger", ambiance="seaside", price_preference="moderate", cuisine="american", categories=["dining","beach"], google_place_types=["restaurant"], query_terms="hamburger"
- "jeftina pizza s terasom" → food_type="pizza", ambiance="terrace", price_preference="budget", cuisine="italian", max_price_level=1, query_terms=["pizza","pizzeria","pizze"]
- "romantična večera s pogledom" → food_type=null, ambiance="romantic+view", price_preference="premium", cuisine="mediterranean", categories=["dining"], google_place_types=["restaurant"]
- "riba na plaži" → food_type="seafood", ambiance="seaside", price_preference=null, cuisine="mediterranean", categories=["dining","beach"], query_terms="seafood"
- "muzej prirode" → food_type=null, ambiance=null, price_preference=null, categories=["cultural","nature"], google_place_types=["museum","park"], query_terms=["priroda","nature"]
- "Supermarkt" → categories=["shopping"], google_place_types=["grocery_or_supermarket"], food_type=null, query_terms=null

Rules:
- Map guest INTENT to the most specific Google Place Types.
- Non-food queries: set food_type, cuisine, query_terms to null.
- Return ONLY valid JSON. No explanation."""

INFO_INTENT_SYSTEM_PROMPT = """You classify guest messages about their vacation rental stay.
Return JSON with:
- "intent": one of wifi, checkin, checkout, rules, parking, beach, shopping, weather, general
- "confidence": float 0.0-1.0

Interpret natural language in any language. Return ONLY valid JSON."""

PREFERENCE_SYSTEM_PROMPT = """You extract vacation preference tags from a guest onboarding message.
Return JSON with:
- "tags": list of 1-4 tags from [wine, food, beach, culture, nature, family, children, nightlife, animals, relaxation, general]
- "confidence": float 0.0-1.0

Interpret natural language and emoji context. Return ONLY valid JSON."""


class FoodClassifierResult(BaseModel):
    """Multi-dimensional food/dining classification from guest queries."""

    food_type: Optional[str] = None
    ambiance: Optional[str] = None
    price_preference: Optional[str] = None
    cuisine: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    google_place_types: List[str] = Field(default_factory=list)
    max_price_level: Optional[int] = None
    query_terms: Optional[object] = None  # str or List[str] from AI
    confidence: float = 0.5

    @classmethod
    def empty(cls) -> "FoodClassifierResult":
        return cls()

    @classmethod
    def from_ai_payload(cls, data: Dict[str, Any]) -> "FoodClassifierResult":
        """Normalize raw AI JSON into validated fields."""
        food_type = _normalize_enum(data.get("food_type"), _VALID_FOOD_TYPES)
        if food_type == "general":
            food_type = None

        ambiance = data.get("ambiance")
        if ambiance is not None:
            ambiance = str(ambiance).strip().lower() or None

        price_pref = _normalize_enum(data.get("price_preference"), _VALID_PRICE_PREFERENCES)

        cuisine = _normalize_enum(data.get("cuisine"), _VALID_CUISINES)
        if cuisine == "general":
            cuisine = None

        categories = [
            str(c).strip().lower()
            for c in (data.get("categories") or [])
            if str(c).strip()
        ]

        google_types = [
            str(t).strip().lower()
            for t in (data.get("google_place_types") or [])
            if str(t).strip()
        ]

        max_price = data.get("max_price_level")
        if max_price is not None:
            try:
                max_price = int(max_price)
                if max_price < 0 or max_price > 4:
                    max_price = None
            except (TypeError, ValueError):
                max_price = None

        raw_qt = data.get("query_terms")
        query_terms = None
        if raw_qt is not None:
            if isinstance(raw_qt, list):
                cleaned = [str(t).strip() for t in raw_qt if t and str(t).strip()]
                query_terms = cleaned if cleaned else None
            elif isinstance(raw_qt, str) and raw_qt.strip():
                query_terms = raw_qt.strip()

        confidence = data.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5

        return cls(
            food_type=food_type,
            ambiance=ambiance,
            price_preference=price_pref,
            cuisine=cuisine,
            categories=categories,
            google_place_types=google_types,
            max_price_level=max_price,
            query_terms=query_terms,
            confidence=confidence,
        )

    def resolved_max_price_level(self) -> Optional[int]:
        if self.max_price_level is not None:
            return self.max_price_level
        if self.price_preference == "budget":
            return 1
        return None

    def partner_search_terms(self) -> List[str]:
        """AI provides multilingual query_terms array or string."""
        terms: List[str] = []
        if self.query_terms:
            if isinstance(self.query_terms, list):
                for t in self.query_terms:
                    if t and str(t).strip():
                        terms.append(str(t).strip().lower())
            else:
                terms.append(str(self.query_terms).strip().lower())
        return terms


def _normalize_enum(value: Any, valid: frozenset) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "null":
        return None
    return normalized if normalized in valid else None


async def _chat_json(system: str, user: str, *, max_tokens: int = 120) -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("OPENAI_MODEL", "deepseek-chat")
    if not api_key:
        return None

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as exc:
        logger.warning("AI JSON classification failed: %s", exc)
        return None


async def ai_classify_categories(
    message: str, preferred_language: str = "hr"
) -> FoodClassifierResult:
    """
    AI-powered multi-dimensional classifier for guest concierge queries.
    Returns FoodClassifierResult with categories, google types, and food dimensions.
    """
    data = await _chat_json(
        CATEGORY_SYSTEM_PROMPT,
        f"Message: {message}\nPreferred language hint: {preferred_language}",
        max_tokens=220,
    )
    if not data:
        return _keyword_fallback(message)

    result = FoodClassifierResult.from_ai_payload(data)
    logger.info(
        "AI classified: food=%s ambiance=%s price=%s cats=%s types=%s query=%s (%.2f)",
        result.food_type,
        result.ambiance,
        result.price_preference,
        result.categories,
        result.google_place_types,
        result.query_terms,
        result.confidence,
    )
    return result


def _keyword_fallback(message: str) -> FoodClassifierResult:
    """Empty fallback — AI is the only classifier."""
    return FoodClassifierResult.empty()


async def ai_classify_info_intent(message: str) -> str:
    """Classify guest stay-info intent for GuestInfoAgent routing."""
    data = await _chat_json(
        INFO_INTENT_SYSTEM_PROMPT,
        f"Message: {message}",
        max_tokens=80,
    )
    if not data:
        return "general"

    intent = str(data.get("intent") or "general").strip().lower()
    if intent in _VALID_INFO_INTENTS:
        return intent
    return "general"


async def ai_classify_preference_tags(message: str) -> List[str]:
    """Extract preference tags from a guest onboarding message via AI."""
    data = await _chat_json(
        PREFERENCE_SYSTEM_PROMPT,
        f"Message: {message}",
        max_tokens=100,
    )
    if not data:
        return []

    tags: List[str] = []
    for tag in data.get("tags") or []:
        normalized = str(tag).strip().lower()
        if normalized in _VALID_PREFERENCE_TAGS and normalized not in tags:
            tags.append(normalized)
    return tags
