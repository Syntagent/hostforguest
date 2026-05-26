"""Host cleaning: AI-assisted ranking and message drafts (DB candidates only)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.partner import Partner
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_AI_HITS: Dict[str, List[float]] = defaultdict(list)
_MAX_AI_PER_HOUR = 40


def _rate_limit_ai(host_id: uuid.UUID) -> bool:
    now = datetime.utcnow().timestamp()
    key = str(host_id)
    bucket = _AI_HITS[key]
    cutoff = now - 3600
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _MAX_AI_PER_HOUR:
        return False
    bucket.append(now)
    return True


def partner_to_candidate_dict(p: Partner) -> Dict[str, Any]:
    return {
        "partner_id": str(p.id),
        "name": p.name,
        "city": p.city,
        "region": p.region or "",
        "price_range": p.price_range or "",
        "rate_card": p.rate_card or {},
        "description": (p.description or "")[:400],
    }


def _fallback_rank(
    host: Host, candidates: List[Partner], intent: str
) -> List[Dict[str, Any]]:
    host_city = (host.city or "").strip().lower()
    ranked: List[Dict[str, Any]] = []
    for p in candidates:
        city = (p.city or "").strip().lower()
        why = "Registered cleaning partner"
        score = 0
        if host_city and city and host_city in city or city in host_city:
            score += 2
            why = f"Serves {p.city or 'your area'}"
        if intent == "deep_clean" and p.description and "deep" in p.description.lower():
            score += 1
            why = "Mentions deep cleaning"
        ranked.append(
            {
                "partner_id": str(p.id),
                "why": why,
                "_score": score,
            }
        )
    ranked.sort(key=lambda x: x.get("_score", 0), reverse=True)
    for row in ranked:
        row.pop("_score", None)
    return ranked


async def rank_cleaning_partners_with_ai(
    db: AsyncSession,
    host: Host,
    candidates: List[Partner],
    intent: str,
) -> Dict[str, Any]:
    """Rank cleaning partners; uses AI when configured, else deterministic fallback."""
    disclaimer = (
        "Rankings are indicative. Confirm availability, pricing, and insurance directly with the provider."
    )
    if not candidates:
        return {
            "ranked": [],
            "ai_used": False,
            "disclaimer": disclaimer,
            "fallback_reason": "no_partners",
        }

    if not _rate_limit_ai(host.id):
        return {
            "ranked": _fallback_rank(host, candidates, intent),
            "ai_used": False,
            "disclaimer": disclaimer,
            "fallback_reason": "rate_limit",
        }

    settings_svc = SettingsService(db)
    ai = AIService(settings_svc)
    payload = {
        "host_city": host.city,
        "intent": intent,
        "candidates": [partner_to_candidate_dict(p) for p in candidates[:15]],
    }
    prompt = (
        "Rank these cleaning partners for a Croatian vacation rental host. "
        "Return JSON only: {\"ranked\":[{\"partner_id\":\"uuid\",\"why\":\"short reason\"},...]} "
        f"Intent: {intent}. Data: {json.dumps(payload, ensure_ascii=False)}"
    )
    try:
        resp = await ai.generate_chat_response(
            str(host.id),
            [{"role": "user", "content": prompt}],
        )
        text = (resp or {}).get("content") or (resp or {}).get("response")
        if resp and resp.get("success") and text:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                parsed = json.loads(m.group())
                ranked = parsed.get("ranked")
                if isinstance(ranked, list) and ranked:
                    valid_ids = {str(p.id) for p in candidates}
                    cleaned = [
                        r
                        for r in ranked
                        if str(r.get("partner_id")) in valid_ids
                    ]
                    if cleaned:
                        return {
                            "ranked": cleaned,
                            "ai_used": True,
                            "disclaimer": disclaimer,
                            "fallback_reason": None,
                        }
    except Exception as exc:
        logger.warning("cleaning AI rank failed: %s", exc)

    return {
        "ranked": _fallback_rank(host, candidates, intent),
        "ai_used": False,
        "disclaimer": disclaimer,
        "fallback_reason": "ai_unavailable",
    }


async def draft_cleaning_message(
    db: AsyncSession,
    host: Host,
    partner: Partner,
    intent: str,
    service_date: Optional[str],
    context_hint: Optional[str],
    language: str = "hr",
) -> Dict[str, Any]:
    """Draft a message to a cleaning partner (AI optional)."""
    prop = host.business_name or "our property"
    city = host.city or "Lovran"
    date_line = f"Datum: {service_date}\n" if service_date else ""
    hint = f"{context_hint}\n" if context_hint else ""
    if language == "hr":
        template = (
            f"Pozdrav,\n\n"
            f"tražim uslugu čišćenja ({'generalno' if intent == 'turnover' else 'dubinsko'}) "
            f"za smještaj {prop} u {city}.\n"
            f"{date_line}{hint}"
            f"Molim potvrdu cijene, termina i što je uključeno (posteljina, sredstva).\n\n"
            f"Hvala,\n{host.first_name or 'Domaćin'}"
        )
    else:
        template = (
            f"Hello,\n\n"
            f"I need a {'turnover' if intent == 'turnover' else 'deep'} clean "
            f"for {prop} in {city}.\n"
            f"{date_line}{hint}"
            f"Please confirm price, time window, and what is included.\n\n"
            f"Thank you,\n{host.first_name or 'Host'}"
        )

    if _rate_limit_ai(host.id):
        settings_svc = SettingsService(db)
        ai = AIService(settings_svc)
        prompt = (
            f"Write a short professional message in {language} from a host to cleaner "
            f"'{partner.name}'. Intent: {intent}. Property: {prop}, {city}. "
            f"Date: {service_date or 'flexible'}. Context: {context_hint or 'none'}. "
            "Plain text only, under 120 words."
        )
        try:
            resp = await ai.generate_chat_response(
                str(host.id),
                [{"role": "user", "content": prompt}],
            )
            text = (resp or {}).get("content") or (resp or {}).get("response")
            if resp and resp.get("success") and text and len(str(text).strip()) > 40:
                return {"draft": str(text).strip(), "ai_used": True}
        except Exception as exc:
            logger.warning("cleaning AI draft failed: %s", exc)

    return {"draft": template, "ai_used": False}


