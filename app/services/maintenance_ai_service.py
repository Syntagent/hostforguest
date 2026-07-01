"""
AI-assisted partner ranking and message drafting for maintenance issues.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.partner import Partner
from app.models.maintenance import MaintenanceIssue
from app.services.maintenance_service import MaintenanceService
from app.services.settings_service import SettingsService
from app.services.ai_service_fallback import AIServiceWithFallback

logger = logging.getLogger(__name__)


class PartnerRankLine(BaseModel):
    partner_id: str = Field(description="UUID of partner")
    rank: int = Field(ge=1)
    reason: str = Field(max_length=500)


class PartnerRankResult(BaseModel):
    ranked: List[PartnerRankLine] = Field(default_factory=list)


class MaintenanceDraftResult(BaseModel):
    message_hr: str = Field(description="Full message in Croatian for the tradesperson")


class ReplySuggestionsResult(BaseModel):
    suggestions: List[str] = Field(default_factory=list)


class MaintenanceAIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._settings = SettingsService(db)
        self._ai = AIServiceWithFallback(self._settings)
        self._maint = MaintenanceService(db)

    async def suggest_partners_ranked(
        self,
        host: Host,
        issue: MaintenanceIssue,
    ) -> Dict[str, Any]:
        candidates = await self._maint.fetch_partner_candidates(
            host, issue.category, limit=20, linked_only=True
        )
        if not candidates:
            return {
                "ranked": [],
                "ai_used": False,
                "disclaimer": (
                    "No linked partners match this category. "
                    "Link maintenance partners to your account first."
                ),
            }

        payload = []
        for p, dist in candidates:
            tc = p.trade_categories or []
            payload.append(
                {
                    "partner_id": str(p.id),
                    "name": p.name,
                    "city": p.city,
                    "phone": p.phone,
                    "partner_type": p.partner_type,
                    "trade_categories": tc,
                    "distance_km": round(dist, 2) if dist is not None else None,
                }
            )

        user_msg = (
            "Rank these partners for the maintenance issue (best first). "
            "Only use partner_id values from the list. One line reason each.\n\n"
            f"Issue category: {issue.category}\nTitle: {issue.title}\nDescription: {issue.description or ''}\n\n"
            f"Candidates JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        res = await self._ai.generate_structured_response(
            str(host.id),
            [{"role": "user", "content": user_msg}],
            context={
                "task": "maintenance_partner_rank",
                "location": host.city or "Croatia",
            },
            response_schema=PartnerRankResult,
        )

        if res.get("success") and res.get("structured_data"):
            data = PartnerRankResult.model_validate(res["structured_data"])
            by_id = {str(p.id): (p, dist) for p, dist in candidates}
            ordered = []
            seen = set()
            for line in sorted(data.ranked, key=lambda x: x.rank):
                pid = line.partner_id
                if pid in by_id and pid not in seen:
                    seen.add(pid)
                    p, dist = by_id[pid]
                    ordered.append(
                        {
                            "partner_id": pid,
                            "name": p.name,
                            "phone": p.phone,
                            "city": p.city,
                            "distance_km": dist,
                            "reason": line.reason,
                        }
                    )
            for p, dist in candidates:
                sid = str(p.id)
                if sid not in seen:
                    ordered.append(
                        {
                            "partner_id": sid,
                            "name": p.name,
                            "phone": p.phone,
                            "city": p.city,
                            "distance_km": dist,
                            "reason": "Listed by proximity / category match",
                        }
                    )
            return {
                "ranked": ordered,
                "ai_used": True,
                "disclaimer": "Assistive ranking only — verify licenses and references before hiring.",
            }

        ordered = [
            {
                "partner_id": str(p.id),
                "name": p.name,
                "phone": p.phone,
                "city": p.city,
                "distance_km": dist,
                "reason": "Order by saved match and distance (AI unavailable)",
            }
            for p, dist in candidates
        ]
        return {
            "ranked": ordered,
            "ai_used": False,
            "disclaimer": "AI unavailable; showing deterministic order.",
        }

    async def draft_message(
        self,
        host: Host,
        issue: MaintenanceIssue,
        partner: Partner,
        tone: str = "formal",
        channel: str = "whatsapp",
        include_guest_contact: bool = False,
    ) -> Dict[str, Any]:
        guest_note = ""
        if include_guest_contact and issue.guest_group_id:
            guest_note = "Možete uključiti da je prijava od gosta (bez imena ako nije potrebno)."
        else:
            guest_note = "Ne uključuj identitet gosta; samo opis problema."

        user_msg = (
            f"Napiši kratku poruku na hrvatskom za majstora/partnera.\n"
            f"Ton: {tone}. Kanal: {channel}.\n"
            f"{guest_note}\n"
            f"Lokacija smještaja (samo grad/kraj): {host.city or 'Hrvatska'}\n"
            f"Kategorija: {issue.category}\nNaslov: {issue.title}\nOpis: {issue.description or ''}\n"
            f"Kontakt partnera (za pozdrav): {partner.name}\n"
        )
        res = await self._ai.generate_structured_response(
            str(host.id),
            [{"role": "user", "content": user_msg}],
            context={"task": "maintenance_draft_hr", "language": "hr"},
            response_schema=MaintenanceDraftResult,
        )
        text = ""
        if res.get("success") and res.get("structured_data"):
            text = MaintenanceDraftResult.model_validate(res["structured_data"]).message_hr
        elif res.get("success") and res.get("response"):
            text = str(res["response"])
        if not text.strip():
            text = (
                f"Poštovani,\n\nMolim ponudu/rad za: {issue.title}.\n"
                f"Opis: {issue.description or issue.category}\nLokacija: {host.city or 'Hrvatska'}.\n\nLijep pozdrav"
            )
        return {"message_hr": text.strip(), "ai_used": bool(res.get("structured_data"))}

    async def reply_suggestions(
        self,
        host: Host,
        inbound_text: str,
    ) -> Dict[str, Any]:
        user_msg = (
            "The host received this message from a tradesperson (Croatian or mixed). "
            "Suggest up to 3 short reply options in Croatian.\n\n"
            f"Message:\n{inbound_text}"
        )
        res = await self._ai.generate_structured_response(
            str(host.id),
            [{"role": "user", "content": user_msg}],
            context={"task": "maintenance_reply_suggestions", "language": "hr"},
            response_schema=ReplySuggestionsResult,
        )
        sugs: List[str] = []
        if res.get("success") and res.get("structured_data"):
            sugs = ReplySuggestionsResult.model_validate(res["structured_data"]).suggestions
        return {"suggestions": sugs[:5]}
