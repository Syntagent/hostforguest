"""
Adaptation / redesign projects (indicative planning).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.adaptation import AdaptationProject, AdaptationAsset, AdaptationProposal
from app.services.adaptation_roi import bom_totals, compute_adaptation_roi
from app.services.maintenance_service import MaintenanceService
from app.services.settings_service import SettingsService
from app.services.ai_service_fallback import AIServiceWithFallback

logger = logging.getLogger(__name__)


class AdaptationProjectService:
    """CRUD for adaptation projects and assets."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, host_id: uuid.UUID) -> List[AdaptationProject]:
        r = await self.db.execute(
            select(AdaptationProject)
            .where(AdaptationProject.host_id == host_id)
            .order_by(AdaptationProject.updated_at.desc())
        )
        return list(r.scalars().all())

    async def get_project(self, host_id: uuid.UUID, project_id: uuid.UUID) -> Optional[AdaptationProject]:
        r = await self.db.execute(
            select(AdaptationProject).where(
                and_(AdaptationProject.id == project_id, AdaptationProject.host_id == host_id)
            )
        )
        return r.scalar_one_or_none()

    async def create_project(
        self,
        host_id: uuid.UUID,
        *,
        title: str,
        brief: Optional[str] = None,
        style_tags: Optional[List[str]] = None,
        budget_band: Optional[str] = None,
    ) -> AdaptationProject:
        p = AdaptationProject(
            host_id=host_id,
            title=title,
            brief=brief,
            style_tags=style_tags or [],
            budget_band=budget_band,
            status="draft",
        )
        self.db.add(p)
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def update_project(
        self,
        host_id: uuid.UUID,
        project_id: uuid.UUID,
        **fields: Any,
    ) -> Optional[AdaptationProject]:
        p = await self.get_project(host_id, project_id)
        if not p:
            return None
        doc_notes = fields.pop("documentation_notes", None)
        for k in ("title", "brief", "style_tags", "budget_band", "status", "assumptions_json", "roi_inputs_json"):
            if k in fields and fields[k] is not None:
                setattr(p, k, fields[k])
        if doc_notes is not None:
            merged = dict(p.assumptions_json or {})
            merged["project_documentation"] = doc_notes
            p.assumptions_json = merged
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def add_asset(
        self,
        host_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        storage_url: str,
        kind: str = "before_photo",
        sort_order: int = 0,
    ) -> Optional[AdaptationAsset]:
        p = await self.get_project(host_id, project_id)
        if not p:
            return None
        a = AdaptationAsset(
            project_id=project_id,
            storage_url=storage_url,
            kind=kind,
            sort_order=sort_order,
        )
        self.db.add(a)
        await self.db.commit()
        await self.db.refresh(a)
        return a

    async def list_proposals(self, host_id: uuid.UUID, project_id: uuid.UUID) -> List[AdaptationProposal]:
        p = await self.get_project(host_id, project_id)
        if not p:
            return []
        r = await self.db.execute(
            select(AdaptationProposal)
            .where(AdaptationProposal.project_id == project_id)
            .order_by(AdaptationProposal.version.desc())
        )
        return list(r.scalars().all())

    async def patch_bom(
        self,
        host_id: uuid.UUID,
        project_id: uuid.UUID,
        lines: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        p = await self.get_project(host_id, project_id)
        if not p:
            return None
        tmin, tmax = bom_totals(lines)
        p.assumptions_json = {**(p.assumptions_json or {}), "bom_lines": lines}
        await self.db.commit()
        await self.db.refresh(p)
        return {
            "bom": {"lines": lines},
            "total_range_min": tmin,
            "total_range_max": tmax,
        }

    def compute_roi_for_project(
        self,
        project: AdaptationProject,
        investment_mid: Optional[float] = None,
    ) -> Dict[str, Any]:
        if investment_mid is None:
            lines = (project.assumptions_json or {}).get("bom_lines") or []
            tmin, tmax = bom_totals(lines)
            investment_mid = (tmin + tmax) / 2 if (tmin or tmax) else 0.0
        return compute_adaptation_roi(project.roi_inputs_json or {}, investment_mid)


class AdaptationBOMLineModel(BaseModel):
    section: str = ""
    description: str = ""
    qty_hint: str = ""
    unit: str = ""
    cost_min_eur: float = 0
    cost_mid_eur: float = 0
    cost_max_eur: float = 0
    supplier_category: str = "other"


class AdaptationAnalyzeResultModel(BaseModel):
    vision_summary: str = ""
    risks_and_checks: List[str] = Field(default_factory=list)
    mood_board_text: str = ""
    bom_lines: List[AdaptationBOMLineModel] = Field(default_factory=list)


_POOL_KEYWORDS = ("pool", "bazen", "basen", "infinity", "swimming")


def _project_text_blob(project: AdaptationProject) -> str:
    parts = [project.title or "", project.brief or "", " ".join(project.style_tags or [])]
    return " ".join(parts).lower()


def _looks_like_pool_project(project: AdaptationProject) -> bool:
    return any(k in _project_text_blob(project) for k in _POOL_KEYWORDS)


def _pool_finish_risks() -> List[str]:
    return [
        "Provjera hidroizolacije i uklapanja epoksidnog / poliesterskog sustava s dobavljačem (kompatibilnost s betonom).",
        "Elektrika: izjednačenje potencijala, zaštitni odvod (FID/RCD), zone 0–2 — samo licencirani elektroinstalater.",
        "Lokalna pravila: ograda, pokrivač, alarm — provjerite s općinom / kućnim redom.",
        "Tlak test cjevovoda prije zatvaranja i prije epoksidne završnice.",
    ]


def _offline_pool_shell_finish_bom() -> List[AdaptationBOMLineModel]:
    """Indicative BOM when AI is offline and project looks like a pool shell fit-out (e.g. 6×3 m, epoxy)."""
    return [
        AdaptationBOMLineModel(
            section="Hydraulics",
            description="Pumpa cirkulacije, filter (pjeskovni/kartušni), armature, povezivanje na skimmer / slivnike / prskalice ako nisu u ljusci",
            qty_hint="1",
            unit="set",
            cost_min_eur=2800,
            cost_mid_eur=7200,
            cost_max_eur=16000,
            supplier_category="plumbing",
        ),
        AdaptationBOMLineModel(
            section="Electrical",
            description="Napajanje strojarnice, osvjetljenje bazena, uzemljenje / izjednačenje potencijala (TN-C-S / odvod)",
            qty_hint="1",
            unit="set",
            cost_min_eur=900,
            cost_mid_eur=2800,
            cost_max_eur=5500,
            supplier_category="electrical",
        ),
        AdaptationBOMLineModel(
            section="Interior finish",
            description="Priprema betona, grunt, epoksidna ili poliesterska završnica u plavoj tonaciji (materijal + rad)",
            qty_hint="~18–40 m²",
            unit="shell",
            cost_min_eur=3500,
            cost_mid_eur=9000,
            cost_max_eur=22000,
            supplier_category="paint",
        ),
        AdaptationBOMLineModel(
            section="Edge / coping",
            description="Rubni kamen / PVC coping, odvod ruba, spoj s terasom",
            qty_hint="1",
            unit="obvod",
            cost_min_eur=1200,
            cost_mid_eur=4500,
            cost_max_eur=11000,
            supplier_category="tiles",
        ),
        AdaptationBOMLineModel(
            section="Heating (optional)",
            description="Toplotna pumpa za bazen ili solarni set (ako želite sezonu produžiti)",
            qty_hint="0–1",
            unit="set",
            cost_min_eur=0,
            cost_mid_eur=6500,
            cost_max_eur=18000,
            supplier_category="hvac",
        ),
        AdaptationBOMLineModel(
            section="Safety & commissioning",
            description="Pokrivač, kemija prvo punjenje, puštanje u pogon s serviserom",
            qty_hint="1",
            unit="lot",
            cost_min_eur=800,
            cost_mid_eur=2200,
            cost_max_eur=6000,
            supplier_category="other",
        ),
    ]


class AdaptationPhaseModel(BaseModel):
    """One ordered step on the renovation / adaptation path."""

    phase_name: str = ""
    description: str = ""
    order: int = 1
    duration_weeks_min: int = 0
    duration_weeks_max: int = 0
    key_tasks: List[str] = Field(default_factory=list)


class AdaptationAssistantResponseModel(BaseModel):
    """Coach output: path, costs, time, and how to communicate with trades."""

    reply: str = ""
    phases: List[AdaptationPhaseModel] = Field(default_factory=list)
    cost_orientation: str = ""
    timeline_overview: str = ""
    communication_tips: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)


class AdaptationAIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._settings = SettingsService(db)
        self._ai = AIServiceWithFallback(self._settings)
        self._maint = MaintenanceService(db)

    async def analyze_project(self, host: Host, project: AdaptationProject) -> Dict[str, Any]:
        r = await self.db.execute(
            select(AdaptationAsset)
            .where(AdaptationAsset.project_id == project.id)
            .order_by(AdaptationAsset.sort_order)
        )
        assets = list(r.scalars().all())
        urls = [a.storage_url for a in assets if a.kind == "before_photo"]

        brief = project.brief or ""
        styles = project.style_tags or []
        budget = project.budget_band or "mid"

        user_msg = (
            "You are assisting a Croatian short-term rental host with an indicative renovation scope. "
            "This is NOT structural engineering or legal advice. "
            f"Project title: {project.title}\n"
            f"Brief: {brief}\n"
            f"Style tags: {', '.join(styles)}\n"
            f"Budget band: {budget}\n"
            f"Number of before photos (URLs for context only, you may not see pixels): {len(urls)}\n"
            f"Photo URLs: {json.dumps(urls[:12])}\n"
            "Return structured BOM line items with indicative EUR ranges for Croatia (rough market bands). "
            "Include risks_and_checks reminding to verify permits and hire licensed trades where needed."
        )

        res = await self._ai.generate_structured_response(
            str(host.id),
            [{"role": "user", "content": user_msg}],
            context={"task": "adaptation_analyze", "location": host.city or "Croatia"},
            response_schema=AdaptationAnalyzeResultModel,
        )

        parsed: Optional[AdaptationAnalyzeResultModel] = None
        ai_structured_ok = bool(res.get("success") and res.get("structured_data"))
        if ai_structured_ok:
            try:
                parsed = AdaptationAnalyzeResultModel.model_validate(res["structured_data"])
            except Exception as e:
                logger.warning("adaptation analyze validate failed: %s", e)
                parsed = None
                ai_structured_ok = False

        bom_source = "ai"
        pool = _looks_like_pool_project(project)

        if parsed is None:
            if pool:
                parsed = AdaptationAnalyzeResultModel(
                    vision_summary=(
                        "Structured AI output was not available — check GOOGLE_AI_API_KEY / OPENAI_API_KEY in .env "
                        "or host AI settings, then run **Analyze** again. "
                        "Because this project looks like a **pool** (shell / bazen), we added an indicative "
                        "checklist below for finishing a concrete shell (hydraulics, power, epoxy-style interior, coping, commissioning). "
                        "Not a quote."
                    ),
                    risks_and_checks=_pool_finish_risks(),
                    mood_board_text=" ".join(styles) if styles else "Pool shell completion",
                    bom_lines=_offline_pool_shell_finish_bom(),
                )
                bom_source = "template_pool"
            else:
                parsed = AdaptationAnalyzeResultModel(
                    vision_summary=(
                        "Structured AI output was not available. Check API keys in .env, add more detail to the brief, "
                        "and run Analyze again. No automatic BOM was added for this project type."
                    ),
                    risks_and_checks=[
                        "Provjerite dozvole i statiku prije rušenja zidova.",
                        "Angažirajte licencirane struke za plin, struju i vodu.",
                    ],
                    mood_board_text=" ".join(styles) or "Moderan, ugodan prostor za goste.",
                    bom_lines=[],
                )
                bom_source = "none"
        elif not parsed.bom_lines and pool:
            merged_risks = list(dict.fromkeys((parsed.risks_and_checks or []) + _pool_finish_risks()))
            vs = (parsed.vision_summary or "").strip()
            if not vs or "unavailable" in vs.lower():
                new_vs = (
                    "The model returned no line items. For your **pool shell** project we filled in a **template BOM** "
                    "(indicative EUR bands for Croatia). Validate everything with installers — not a quote."
                )
            else:
                new_vs = (
                    vs + " We added template BOM lines typical for finishing a pool shell (indicative only)."
                ).strip()
            parsed = parsed.model_copy(
                update={
                    "bom_lines": _offline_pool_shell_finish_bom(),
                    "risks_and_checks": merged_risks,
                    "vision_summary": new_vs,
                }
            )
            bom_source = "template_pool"
        elif not parsed.bom_lines:
            bom_source = "empty_ai"

        bom_dicts = [b.model_dump() for b in parsed.bom_lines]
        tmin, tmax = bom_totals(bom_dicts)
        tmid = (tmin + tmax) / 2 if (tmin or tmax) else 0.0

        r2 = await self.db.execute(
            select(AdaptationProposal)
            .where(AdaptationProposal.project_id == project.id)
            .order_by(AdaptationProposal.version.desc())
            .limit(1)
        )
        last = r2.scalar_one_or_none()
        ver = (last.version + 1) if last else 1

        proposal = AdaptationProposal(
            project_id=project.id,
            version=ver,
            vision_analysis_json={
                "vision_summary": parsed.vision_summary,
                "risks_and_checks": parsed.risks_and_checks,
                "mood_board_text": parsed.mood_board_text,
            },
            bom_json={"lines": bom_dicts},
            concept_image_urls=[],
            total_range_min=tmin or None,
            total_range_max=tmax or None,
            model_ids={"provider": res.get("provider"), "model": res.get("model")},
        )
        self.db.add(proposal)
        project.assumptions_json = {
            **(project.assumptions_json or {}),
            "bom_lines": bom_dicts,
        }
        await self.db.commit()
        await self.db.refresh(proposal)
        await self.db.refresh(project)

        roi = compute_adaptation_roi(project.roi_inputs_json or {}, tmid)

        return {
            "proposal_id": str(proposal.id),
            "version": ver,
            "vision_analysis": proposal.vision_analysis_json,
            "bom": proposal.bom_json,
            "total_range_min": proposal.total_range_min,
            "total_range_max": proposal.total_range_max,
            "roi_preview": roi,
            "disclaimer": "Indicative only — not a quote, not legal or structural advice.",
            "ai_used": ai_structured_ok and bom_source == "ai",
            "bom_source": bom_source,
            "hints": [
                "ROI below uses your saved ADR/occupancy only after you click **ROI (sample inputs)** or patch inputs; "
                "first run may show zeros until those fields are set.",
                "For supplier search on pools try categories: **plumbing**, **electrical**, **hvac** — not only tiles.",
            ],
        }

    async def suggest_suppliers(
        self,
        host: Host,
        project: AdaptationProject,
        bom_category: str,
    ) -> Dict[str, Any]:
        """Map supplier_category from BOM to maintenance category heuristic."""
        cat_map = {
            "plumbing": "plumbing",
            "electrical": "electrical",
            "tiles": "structure",
            "flooring": "structure",
            "carpentry": "structure",
            "furniture": "other",
            "lighting": "electrical",
            "hvac": "hvac",
            "paint": "cleaning",
            "pool": "plumbing",
            "epoxy": "paint",
        }
        mc = cat_map.get(bom_category.lower(), "other")
        candidates = await self._maint.fetch_partner_candidates(host, mc, limit=15)
        ranked = [
            {
                "partner_id": str(p.id),
                "name": p.name,
                "phone": p.phone,
                "city": p.city,
                "distance_km": dist,
            }
            for p, dist in candidates
        ]
        host_has_coordinates = host.latitude is not None and host.longitude is not None
        any_distance_unknown = any(r["distance_km"] is None for r in ranked)
        return {
            "bom_category": bom_category,
            "maintenance_category": mc,
            "partners": ranked,
            "discovery": {
                "host_has_coordinates": host_has_coordinates,
                "any_distance_unknown": any_distance_unknown,
                "sort_explanation": (
                    "Partners come from your directory (active listings). Order: linked to you first, "
                    "then same city as your property, then by distance when both your address and the "
                    "partner listing have coordinates. A missing distance (km) means it could not be "
                    "computed—not “infinitely far.”"
                ),
            },
        }

    def _assistant_fallback(self, user_message: str) -> AdaptationAssistantResponseModel:
        return AdaptationAssistantResponseModel(
            reply=(
                "AI keys are not configured or the model did not return structured data. "
                "Use **Analyze (AI)** on your project to generate a BOM and indicative totals, "
                "then ask a specific question (e.g. “in what order should I schedule trades?”).\n\n"
                f"You asked: {user_message[:500]}"
            ),
            phases=[
                AdaptationPhaseModel(
                    phase_name="Scope & permits",
                    description="Freeze the brief, list must-haves vs nice-to-haves, confirm if permits or condo rules apply.",
                    order=1,
                    duration_weeks_min=1,
                    duration_weeks_max=4,
                    key_tasks=[
                        "Written scope + reference photos",
                        "Check local dozvole / building manager",
                        "Ballpark budget band (low / mid / high)",
                    ],
                ),
                AdaptationPhaseModel(
                    phase_name="Quotes & sequencing",
                    description="Line up licensed trades in a logical order (e.g. rough-in before finishes).",
                    order=2,
                    duration_weeks_min=2,
                    duration_weeks_max=6,
                    key_tasks=[
                        "2–3 written quotes per trade",
                        "Agree start dates and access windows",
                        "Deposit / milestone terms in writing",
                    ],
                ),
                AdaptationPhaseModel(
                    phase_name="Execution & snag",
                    description="Work through the plan, then walk through with a punch list before final payment.",
                    order=3,
                    duration_weeks_min=2,
                    duration_weeks_max=12,
                    key_tasks=["Weekly check-ins", "Photo progress log", "Final inspection with trades"],
                ),
            ],
            cost_orientation=(
                "Indicative only: tie numbers to your BOM line ranges (min/mid/max EUR) after running analysis; "
                "add 10–20% contingency for older coastal stock."
            ),
            timeline_overview=(
                "Small cosmetic refreshes often sit in the 2–6 week range once trades are booked; "
                "kitchens/baths or structural touchpoints can run many weeks—depends on permits and lead times."
            ),
            communication_tips=[
                "Send one written brief (scope, budget band, deadline, access rules) and reuse it for every quote.",
                "Ask each trade what they need finished before they start (e.g. electrician before plaster).",
                "Keep changes in email/WhatsApp so expectations stay traceable.",
            ],
            follow_up_questions=[
                "Which room is the bottleneck for guest revenue if it stays unfinished?",
                "Do you already have a BOM from Analyze, or should we build one first?",
            ],
        )

    async def assistant_turn(
        self,
        host: Host,
        project: AdaptationProject,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Conversational coach: project path, indicative costs/time, contractor communication.
        """
        history = history or []
        history = history[-12:]

        r2 = await self.db.execute(
            select(AdaptationProposal)
            .where(AdaptationProposal.project_id == project.id)
            .order_by(AdaptationProposal.version.desc())
            .limit(1)
        )
        prop = r2.scalar_one_or_none()
        bom_lines = (prop.bom_json or {}).get("lines") if prop and prop.bom_json else []
        if not bom_lines:
            bom_lines = (project.assumptions_json or {}).get("bom_lines") or []
        bom_json = json.dumps(bom_lines[:24], ensure_ascii=False)[:8000]

        vision_bits = {}
        if prop and prop.vision_analysis_json:
            vision_bits = prop.vision_analysis_json

        hist_txt = ""
        for h in history:
            role = (h.get("role") or "").strip()
            content = (h.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            hist_txt += f"{role.upper()}: {content[:2000]}\n"

        ctx_block = (
            f"Host city/region: {host.city or ''} {host.county or ''} {host.country or 'Croatia'}\n"
            f"Property type: {host.business_type or 'rental'}\n"
            f"PROJECT title: {project.title}\n"
            f"Brief: {project.brief or ''}\n"
            f"Style tags: {', '.join(project.style_tags or [])}\n"
            f"Budget band: {project.budget_band or 'unspecified'}\n"
            f"Vision / analysis snapshot: {json.dumps(vision_bits, ensure_ascii=False)[:4000]}\n"
            f"BOM lines (JSON, indicative): {bom_json}\n"
        )

        user_msg = (
            "You are the Adaptation Studio assistant for a Croatian short-term rental host.\n"
            "Help with: logical project path (phases), indicative cost orientation (EUR bands, not quotes), "
            "rough timelines in weeks, and clear communication with contractors.\n"
            "This is NOT legal, structural, or tax advice. Encourage licensed trades and permits where relevant.\n"
            "Answer in the user's language if they wrote in Croatian; otherwise English.\n\n"
            f"CONTEXT:\n{ctx_block}\n"
            f"PRIOR TURNS:\n{hist_txt or '(none)'}\n"
            f"USER MESSAGE:\n{user_message}\n"
        )

        res = await self._ai.generate_structured_response(
            str(host.id),
            [{"role": "user", "content": user_msg}],
            context={"task": "adaptation_assistant", "location": host.city or "Croatia"},
            response_schema=AdaptationAssistantResponseModel,
        )

        parsed: Optional[AdaptationAssistantResponseModel] = None
        ai_substantive = False
        if res.get("success") and res.get("structured_data"):
            try:
                parsed = AdaptationAssistantResponseModel.model_validate(res["structured_data"])
                ai_substantive = True
            except Exception as e:
                logger.warning("adaptation assistant validate failed: %s", e)

        if parsed is None:
            parsed = self._assistant_fallback(user_message)
            ai_substantive = False
        else:
            prose = (res.get("response") or "").strip()
            if not (parsed.reply or "").strip() and prose:
                parsed = parsed.model_copy(update={"reply": prose[:12000]})
                ai_substantive = True
            if not (parsed.reply or "").strip():
                parsed = self._assistant_fallback(user_message)
                ai_substantive = False

        out = parsed.model_dump()
        out["disclaimer"] = (
            "Indicative planning only — not a quote, not legal or structural engineering advice."
        )
        out["ai_used"] = ai_substantive
        return out
