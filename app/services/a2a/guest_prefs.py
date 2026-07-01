"""
Guest preference capture and parsing.

Handles preference message parsing, preference-to-category mapping,
and multilingual preference prompts.
"""

import re
from typing import Any, Dict, List, Optional, Set

from app.services.a2a.ai_category_classifier import ai_classify_preference_tags

# ── Multilingual preference prompts ──────────────────────────────────────────

PREFERENCE_PROMPTS = {
    "hr": (
        "Kakav odmor planirate? Što vas zanima?\n\n"
        "🍷 Vino i gastro   🏖️ Plaže   🏛️ Kultura\n"
        "🌿 Priroda   👨‍👩‍👧‍👦 Obitelj   🎉 Night life\n\n"
        "_Možete odabrati gumb ili napisati slobodno, npr._ "
        "*s djecom 3 i 5 god, volimo životinje*"
    ),
    "de": (
        "Was für einen Urlaub planen Sie? Was interessiert Sie?\n\n"
        "🍷 Wein & Kulinarik   🏖️ Strände   🏛️ Kultur\n"
        "🌿 Natur   👨‍👩‍👧‍👦 Familie   🎉 Nachtleben\n\n"
        "_Tippen Sie eine Taste oder schreiben Sie frei, z.B._ "
        "*mit Kindern 3 und 5, lieben Tiere*"
    ),
    "en": (
        "What kind of vacation are you planning? What interests you?\n\n"
        "🍷 Wine & Food   🏖️ Beaches   🏛️ Culture\n"
        "🌿 Nature   👨‍👩‍👧‍👦 Family   🎉 Nightlife\n\n"
        "_Tap a button or write freely, e.g._ "
        "*with kids 3 and 5, we love animals*"
    ),
    "it": (
        "Che tipo di vacanza state pianificando? Cosa vi interessa?\n\n"
        "🍷 Vino & Gastronomia   🏖️ Spiagge   🏛️ Cultura\n"
        "🌿 Natura   👨‍👩‍👧‍👦 Famiglia   🎉 Vita notturna\n\n"
        "_Toccate un pulsante o scrivete liberamente, es._ "
        "*con bambini di 3 e 5 anni, amiamo gli animali*"
    ),
    "hu": (
        "Milyen nyaralást terveznek? Mi érdekli Önöket?\n\n"
        "🍷 Bor és gasztronómia   🏖️ Strandok   🏛️ Kultúra\n"
        "🌿 Természet   👨‍👩‍👧‍👦 Család   🎉 Éjszakai élet\n\n"
        "_Érintsenek egy gombot vagy írjanak szabadon, pl._ "
        "*3 és 5 éves gyerekekkel, szeretjük az állatokat*"
    ),
    "pl": (
        "Jakie wakacje planujecie? Co Was interesuje?\n\n"
        "🍷 Wino i kuchnia   🏖️ Plaże   🏛️ Kultura\n"
        "🌿 Natura   👨‍👩‍👧‍👦 Rodzina   🎉 Życie nocne\n\n"
        "_Dotknijcie przycisku lub napiszcie swobodnie, np._ "
        "*z dziećmi 3 i 5 lat, kochamy zwierzęta*"
    ),
}

# ── Multilingual preference labels ───────────────────────────────────────────

PREFERENCE_LABELS = {
    "hr": {
        "wine": "vino i gastro", "food": "gastro", "beach": "plaže",
        "culture": "kultura", "nature": "priroda", "family": "obitelj",
        "family_friendly": "obiteljski sadržaji", "children": "djeca",
        "nightlife": "night life", "animals": "životinje",
    },
    "de": {
        "wine": "Wein & Kulinarik", "food": "Kulinarik", "beach": "Strände",
        "culture": "Kultur", "nature": "Natur", "family": "Familie",
        "family_friendly": "Familienfreundlich", "children": "Kinder",
        "nightlife": "Nachtleben", "animals": "Tiere",
    },
    "en": {
        "wine": "wine & food", "food": "food", "beach": "beaches",
        "culture": "culture", "nature": "nature", "family": "family",
        "family_friendly": "family-friendly", "children": "children",
        "nightlife": "nightlife", "animals": "animals",
    },
    "it": {
        "wine": "vino & gastronomia", "food": "gastronomia", "beach": "spiagge",
        "culture": "cultura", "nature": "natura", "family": "famiglia",
        "family_friendly": "adatto alle famiglie", "children": "bambini",
        "nightlife": "vita notturna", "animals": "animali",
    },
    "hu": {
        "wine": "bor és gasztronómia", "food": "gasztronómia", "beach": "strandok",
        "culture": "kultúra", "nature": "természet", "family": "család",
        "family_friendly": "családbarát", "children": "gyerekek",
        "nightlife": "éjszakai élet", "animals": "állatok",
    },
    "pl": {
        "wine": "wino i kuchnia", "food": "kuchnia", "beach": "plaże",
        "culture": "kultura", "nature": "natura", "family": "rodzina",
        "family_friendly": "przyjazne rodzinom", "children": "dzieci",
        "nightlife": "życie nocne", "animals": "zwierzęta",
    },
}

# ── "Didn't understand" messages ─────────────────────────────────────────────

DIDNT_UNDERSTAND = {
    "hr": "Nisam razumio preferencije. Pokušajte ponovo:\n\n",
    "de": "Ich habe Ihre Vorlieben nicht verstanden. Versuchen Sie es erneut:\n\n",
    "en": "I didn't understand your preferences. Please try again:\n\n",
    "it": "Non ho capito le vostre preferenze. Riprovate:\n\n",
    "hu": "Nem értettem a preferenciáit. Próbálja újra:\n\n",
    "pl": "Nie zrozumiałem Waszych preferencji. Spróbujcie ponownie:\n\n",
}

# ── "No data" messages ───────────────────────────────────────────────────────

NO_DATA_MESSAGES = {
    "hr": "Trenutno nemam dovoljno podataka za *{city}*. Pokušajte drugu kategoriju (npr. plaže, restorani).",
    "de": "Ich habe derzeit nicht genug Daten für *{city}*. Versuchen Sie eine andere Kategorie (z.B. Strände, Restaurants).",
    "en": "I don't have enough data for *{city}* right now. Try another category (e.g. beaches, restaurants).",
    "it": "Al momento non ho abbastanza dati per *{city}*. Provate un'altra categoria (es. spiagge, ristoranti).",
    "hu": "Jelenleg nincs elég adatom *{city}* városról. Próbáljon másik kategóriát (pl. strandok, éttermek).",
    "pl": "Obecnie nie mam wystarczająco danych dla *{city}*. Spróbujcie innej kategorii (np. plaże, restauracje).",
}


def get_preference_prompt(language: str = "hr") -> str:
    """Return the preference capture prompt for the given language."""
    return PREFERENCE_PROMPTS.get(language, PREFERENCE_PROMPTS["en"])


def get_didnt_understand(language: str = "hr") -> str:
    """Return the 'didn't understand' message for the given language."""
    return DIDNT_UNDERSTAND.get(language, DIDNT_UNDERSTAND["en"])


def get_no_data_message(language: str, city: str) -> str:
    """Return the 'no data' message for the given language and city."""
    template = NO_DATA_MESSAGES.get(language, NO_DATA_MESSAGES["en"])
    return template.format(city=city)


# ── Backward-compatible aliases ──────────────────────────────────────────────

def preference_prompt_hr() -> str:
    return get_preference_prompt("hr")


def preference_prompt_de() -> str:
    return get_preference_prompt("de")


def preference_prompt_en() -> str:
    return get_preference_prompt("en")


def preference_prompt_it() -> str:
    return get_preference_prompt("it")


def preference_prompt_hu() -> str:
    return get_preference_prompt("hu")


def preference_prompt_pl() -> str:
    return get_preference_prompt("pl")


# ── Preference parsing ───────────────────────────────────────────────────────


async def parse_preference_message(message: str) -> Optional[Dict[str, Any]]:
    """Parse a free-text or emoji-button preference message into structured guest_prefs."""
    if not message or not message.strip():
        return None

    text = message.lower().strip()
    tags: Set[str] = set()
    kids_ages: List[int] = []

    # Detect children ages (structural parsing, not intent keywords)
    age_matches = re.findall(r'(\d+)\s*(?:god|godina|yrs?|years?|jahre?|anni?)', text)
    for m in age_matches:
        try:
            age = int(m)
            if 0 <= age <= 17:
                kids_ages.append(age)
        except ValueError:
            pass

    list_match = re.search(
        r'(?:djecom|djeca|kids|children|kinder|bambini)\s+((?:\d+(?:\s*i\s*)?)+)\s*(?:god|godina|yrs?|years?|jahre?|anni?)',
        text,
    )
    if list_match:
        for n in re.findall(r'\d+', list_match.group(1)):
            try:
                age = int(n)
                if 0 <= age <= 17 and age not in kids_ages:
                    kids_ages.append(age)
            except ValueError:
                pass

    if kids_ages:
        tags.add("family")
        tags.add("children")

    ai_tags = await ai_classify_preference_tags(message)
    tags.update(ai_tags)

    # Emoji matching (explicit user selection)
    if "🍷" in message:
        tags.update(["wine", "food"])
    if "🏖️" in message or "🏝️" in message:
        tags.add("beach")
    if "🏛️" in message:
        tags.add("culture")
    if "🌿" in message or "🌲" in message:
        tags.add("nature")
    if "👨‍👩‍👧‍👦" in message:
        tags.update(["family", "children"])
    if "🎉" in message:
        tags.add("nightlife")

    if not tags:
        return None

    if "general" in tags and len(tags) > 1:
        tags.discard("general")

    return {
        "tags": sorted(tags),
        "kids_ages": kids_ages,
        "has_children": bool(kids_ages) or "children" in tags,
        "raw_text": message.strip(),
    }


def prefs_to_interests(guest_prefs: Optional[Dict[str, Any]]) -> List[str]:
    """Map session guest_prefs to guest_group interest tokens."""
    if not guest_prefs:
        return []
    return list(guest_prefs.get("tags") or [])


def prefs_to_api_categories(guest_prefs: Optional[Dict[str, Any]]) -> List[str]:
    """Map guest_prefs to RecommendationRequestAPI preferred_categories."""
    if not guest_prefs:
        return []
    out: Set[str] = set()
    _PREF_CATEGORIES_FROM_TAGS = {
        "wine": ["dining", "wine"],
        "food": ["dining"],
        "beach": ["beach", "relaxation"],
        "culture": ["cultural", "sightseeing"],
        "nature": ["nature", "activity"],
        "family": ["family", "activity"],
        "children": ["family"],
        "nightlife": ["activity"],
        "animals": ["activity"],
        "general": ["activity", "sightseeing", "cultural"],
    }
    for tag in guest_prefs.get("tags") or []:
        for cat in _PREF_CATEGORIES_FROM_TAGS.get(str(tag).lower(), [str(tag)]):
            out.add(cat)
    if guest_prefs.get("has_children"):
        out.update(["family", "activity"])
    return sorted(out)


def format_prefs_summary(guest_prefs: Dict[str, Any], language: str = "hr") -> str:
    """Human-readable summary of captured preferences in the given language."""
    tags = guest_prefs.get("tags") or []
    labels = PREFERENCE_LABELS.get(language, PREFERENCE_LABELS["en"])
    parts = [labels.get(t, t) for t in tags if t != "general"]
    ages = guest_prefs.get("kids_ages") or []
    if ages:
        age_str = ", ".join(str(a) for a in ages)
        kids_word = {
            "hr": "djeca", "de": "Kinder", "en": "kids", "it": "bambini",
            "hu": "gyerekek", "pl": "dzieci",
        }.get(language, "kids")
        age_suffix = {"hu": "év", "pl": "lat"}.get(language, "god.")
        parts.append(f"{kids_word} ({age_str} {age_suffix})")
    raw = (guest_prefs.get("raw_text") or "").strip()
    if parts:
        return ", ".join(dict.fromkeys(parts))
    fallback = {
        "hr": "opće interese", "de": "allgemeine Interessen", "en": "general interests",
        "it": "interessi generali", "hu": "általános érdeklődés", "pl": "ogólne zainteresowania",
    }.get(language, "general interests")
    return raw[:120] if raw else fallback
