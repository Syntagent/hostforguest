"""AI-generated concierge copy with multilingual fallbacks."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from openai import AsyncOpenAI

from app.services.a2a.guest_prefs import format_prefs_summary

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "hr": "Croatian",
    "de": "German",
    "en": "English",
    "it": "Italian",
    "hu": "Hungarian",
    "pl": "Polish",
}

_CONCIERGE_TOPICS: Dict[str, Dict[str, str]] = {
    "hr": {
        "dining": "gdje jesti",
        "beach": "koje plaže posjetiti",
        "shopping": "gdje kupovati",
        "services": "usluge u blizini",
        "transport": "prijevoz u blizini",
        "default": "što posjetiti",
    },
    "de": {
        "dining": "wo essen",
        "beach": "welche Strände besuchen",
        "shopping": "wo einkaufen",
        "services": "Dienstleistungen in der Nähe",
        "transport": "Transport in der Nähe",
        "default": "was besuchen",
    },
    "en": {
        "dining": "where to eat",
        "beach": "which beaches to visit",
        "shopping": "where to shop",
        "services": "nearby services",
        "transport": "nearby transport",
        "default": "what to visit",
    },
    "it": {
        "dining": "dove mangiare",
        "beach": "quali spiagge visitare",
        "shopping": "dove fare la spesa",
        "services": "servizi nelle vicinanze",
        "transport": "trasporti nelle vicinanze",
        "default": "cosa visitare",
    },
    "hu": {
        "dining": "hol egyenek",
        "beach": "mely strandokat látogassák meg",
        "shopping": "hol vásároljanak",
        "services": "közeli szolgáltatások",
        "transport": "közlekedés a közelben",
        "default": "mit látogassanak meg",
    },
    "pl": {
        "dining": "gdzie zjeść",
        "beach": "które plaże odwiedzić",
        "shopping": "gdzie zrobić zakupy",
        "services": "usługi w okolicy",
        "transport": "transport w okolicy",
        "default": "co odwiedzić",
    },
}

_CONCIERGE_FALLBACKS: Dict[str, Dict[str, str]] = {
    "hr": {
        "children_ages": "S djecom od {ages} godina, za *{topic}* preporučujem:",
        "children": "Za obiteljski odmor (*{topic}*), s obzirom na *{summary}*, preporučujem:",
        "default": "Na temelju vaših interesa (*{summary}*), za *{topic}* preporučujem:",
    },
    "de": {
        "children_ages": "Mit Kindern im Alter von {ages} Jahren, für *{topic}* empfehle ich:",
        "children": "Für einen Familienurlaub (*{topic}*), basierend auf *{summary}*, empfehle ich:",
        "default": "Basierend auf Ihren Interessen (*{summary}*), für *{topic}* empfehle ich:",
    },
    "en": {
        "children_ages": "With children aged {ages}, for *{topic}* I recommend:",
        "children": "For a family vacation (*{topic}*), based on *{summary}*, I recommend:",
        "default": "Based on your interests (*{summary}*), for *{topic}* I recommend:",
    },
    "it": {
        "children_ages": "Con bambini di {ages} anni, per *{topic}* consiglio:",
        "children": "Per una vacanza in famiglia (*{topic}*), in base a *{summary}*, consiglio:",
        "default": "In base ai vostri interessi (*{summary}*), per *{topic}* consiglio:",
    },
    "hu": {
        "children_ages": "{ages} éves gyerekekkel, *{topic}* témában ajánlom:",
        "children": "Családi nyaraláshoz (*{topic}*), *{summary}* alapján ajánlom:",
        "default": "Az Ön érdeklődése (*{summary}*) alapján, *{topic}* témában ajánlom:",
    },
    "pl": {
        "children_ages": "Z dziećmi w wieku {ages} lat, dla *{topic}* polecam:",
        "children": "Na rodzinne wakacje (*{topic}*), biorąc pod uwagę *{summary}*, polecam:",
        "default": "Na podstawie Waszych zainteresowań (*{summary}*), dla *{topic}* polecam:",
    },
}

_EVENT_HEADER_FALLBACKS: Dict[str, str] = {
    "hr": "🎉 **Događaji — {city}** (personalizirano)",
    "de": "🎉 **Veranstaltungen — {city}** (personalisiert)",
    "en": "🎉 **Events — {city}** (personalized)",
    "it": "🎉 **Eventi — {city}** (personalizzato)",
    "hu": "🎉 **Események — {city}** (személyre szabva)",
    "pl": "🎉 **Wydarzenia — {city}** (spersonalizowane)",
}


def _normalize_language(language: str) -> str:
    lang = (language or "hr").strip().lower()
    if lang not in LANGUAGE_NAMES:
        return "en"
    return lang


def _detect_topic(message: str, language: str) -> str:
    topics = _CONCIERGE_TOPICS.get(language, _CONCIERGE_TOPICS["en"])
    return topics["default"]


def _concierge_intro_fallback(
    prefs: Dict[str, Any],
    message: str,
    language: str,
) -> str:
    lang = _normalize_language(language)
    summary = format_prefs_summary(prefs, lang)
    topic = _detect_topic(message, lang)
    templates = _CONCIERGE_FALLBACKS.get(lang, _CONCIERGE_FALLBACKS["en"])

    if prefs.get("has_children"):
        ages = prefs.get("kids_ages") or []
        if ages:
            age_txt = " i ".join(str(a) for a in ages) if lang == "hr" else ", ".join(str(a) for a in ages)
            return templates["children_ages"].format(ages=age_txt, topic=topic)
        return templates["children"].format(summary=summary, topic=topic)
    return templates["default"].format(summary=summary, topic=topic)


def _event_header_fallback(language: str, city: str) -> str:
    lang = _normalize_language(language)
    template = _EVENT_HEADER_FALLBACKS.get(lang, _EVENT_HEADER_FALLBACKS["en"])
    return template.format(city=city)


async def generate_concierge_intro(
    prefs: Dict[str, Any],
    message: str,
    language: str,
    city: str,
) -> str:
    """Generate a warm, personalized concierge intro in the guest's language."""
    lang = _normalize_language(language)
    preferences_summary = format_prefs_summary(prefs, lang)
    lang_name = LANGUAGE_NAMES[lang]

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("OPENAI_MODEL", "deepseek-chat")

    if not api_key:
        return _concierge_intro_fallback(prefs, message, lang)

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a friendly hotel concierge. "
                        f"Always respond in {lang_name} only — never use Croatian unless the guest language is Croatian. "
                        f"Write only the intro text — no bullet lists, no numbering."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"You are a friendly hotel concierge in {city}, Croatia. "
                        f"A guest who loves {preferences_summary} is asking: '{message}'. "
                        f"Respond in {lang_name} with a warm, 1-2 sentence personalized intro."
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            logger.info("AI concierge intro generated for lang=%s city=%s", lang, city)
            return text
    except Exception as exc:
        logger.warning("AI concierge intro failed: %s", exc)

    return _concierge_intro_fallback(prefs, message, lang)


async def generate_event_header(
    language: str,
    city: str,
    event_count: int,
) -> str:
    """Generate an enthusiastic events section header in the guest's language."""
    lang = _normalize_language(language)
    lang_name = LANGUAGE_NAMES[lang]

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("OPENAI_MODEL", "deepseek-chat")

    if not api_key:
        return _event_header_fallback(lang, city)

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a local events guide. "
                        "Write only a short header line — no bullet lists."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"You are a local events guide. Tell a guest in {lang_name} about "
                        f"{event_count} upcoming events in {city}. "
                        "Keep it 1 sentence, enthusiastic. "
                        "You may use one emoji at the start."
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            logger.info("AI event header generated for lang=%s city=%s", lang, city)
            return text
    except Exception as exc:
        logger.warning("AI event header failed: %s", exc)

    return _event_header_fallback(lang, city)
