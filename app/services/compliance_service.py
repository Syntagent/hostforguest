"""
Compliance checklist service — Croatian host obligations catalog + per-host state.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import yaml
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_integration import ChannelAccount, ChannelType
from app.models.guest_group import GuestEVisitorData, GuestGroup
from app.models.host_compliance import (
    ComplianceCatalogResponse,
    ComplianceExplainAIResult,
    ComplianceExplainResponse,
    ComplianceHints,
    ComplianceMeResponse,
    ComplianceMergedCategory,
    ComplianceMergedItem,
    ComplianceProgress,
    CompliancePdvRule,
    HostComplianceItem,
    HostComplianceSettings,
)
from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "infra" / "compliance" / "obligations.hr.yaml"
)
_catalog_cache: Optional[ComplianceCatalogResponse] = None

DISCLAIMER_HR = (
    "Ovo je informativni pregled, ne porezno-pravni savjet. Za odluke se obratite ovlaštenom računovođi "
    "ili pravniku. Propisi se mijenjaju — provjerite službene izvore."
)


def _load_catalog_raw() -> Dict[str, Any]:
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_catalog() -> ComplianceCatalogResponse:
    global _catalog_cache
    if _catalog_cache is None:
        raw = _load_catalog_raw()
        _catalog_cache = ComplianceCatalogResponse.model_validate(raw)
    return _catalog_cache


def reload_catalog_for_tests() -> None:
    global _catalog_cache
    _catalog_cache = None


def matches_scenarios(applies_when: List[str], scenarios: Dict[str, bool]) -> bool:
    if not applies_when:
        return True
    if "always" in applies_when:
        return True
    for tag in applies_when:
        if tag == "evisitor_croatia":
            return True
        if scenarios.get(tag):
            return True
    return False


def item_relevance(
    applies_when: List[str], scenarios: Dict[str, bool]
) -> str:
    if not applies_when or "always" in applies_when:
        return "required"
    if matches_scenarios(applies_when, scenarios):
        return "required"
    active = [k for k, v in scenarios.items() if v]
    if not active:
        return "optional"
    return "not_applicable"


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_settings(self, host_id: UUID) -> HostComplianceSettings:
        q = select(HostComplianceSettings).where(HostComplianceSettings.host_id == host_id)
        row = (await self.db.execute(q)).scalar_one_or_none()
        if row:
            return row
        catalog = get_catalog()
        row = HostComplianceSettings(
            host_id=host_id,
            scenarios={},
            catalog_version=catalog.version,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def _get_item_map(self, host_id: UUID) -> Dict[str, HostComplianceItem]:
        q = select(HostComplianceItem).where(HostComplianceItem.host_id == host_id)
        rows = (await self.db.execute(q)).scalars().all()
        return {r.item_id: r for r in rows}

    async def get_hints(self, host_id: UUID) -> ComplianceHints:
        channel_q = select(ChannelAccount).where(
            ChannelAccount.host_id == host_id,
            ChannelAccount.channel == ChannelType.BOOKING_COM.value,
        )
        channel = (await self.db.execute(channel_q)).scalar_one_or_none()
        ev_q = (
            select(func.count(GuestEVisitorData.id))
            .select_from(GuestEVisitorData)
            .join(GuestGroup, GuestGroup.id == GuestEVisitorData.guest_group_id)
            .where(GuestGroup.host_id == host_id)
        )
        ev_count = (await self.db.execute(ev_q)).scalar() or 0

        return ComplianceHints(
            suggest_uses_ota=bool(channel),
            has_evisitor_records=ev_count > 0,
        )

    def _merge_catalog(
        self,
        scenarios: Dict[str, bool],
        item_map: Dict[str, HostComplianceItem],
    ) -> Tuple[
        List[ComplianceMergedCategory],
        ComplianceProgress,
        List[CompliancePdvRule],
        List[CompliancePdvRule],
    ]:
        catalog = get_catalog()
        categories_out: List[ComplianceMergedCategory] = []
        total_relevant = 0
        done = 0

        for cat in catalog.categories:
            merged_items: List[ComplianceMergedItem] = []
            for item in cat.items:
                rel = item_relevance(item.applies_when, scenarios)
                db_row = item_map.get(item.id)
                status = db_row.status if db_row else "missing"
                if rel == "not_applicable" and status == "missing":
                    status = "not_applicable"

                if rel in ("required", "optional"):
                    total_relevant += 1
                    if status == "done":
                        done += 1

                merged_items.append(
                    ComplianceMergedItem(
                        **item.model_dump(),
                        status=status,  # type: ignore[arg-type]
                        notes=db_row.notes if db_row else None,
                        completed_at=db_row.completed_at if db_row else None,
                        relevance=rel,  # type: ignore[arg-type]
                    )
                )
            categories_out.append(
                ComplianceMergedCategory(
                    id=cat.id,
                    label_hr=cat.label_hr,
                    items=merged_items,
                )
            )

        percent = int(round(100 * done / total_relevant)) if total_relevant else 0
        progress = ComplianceProgress(total_relevant=total_relevant, done=done, percent=percent)
        pdv_rules = catalog.pdv_regime_rules if scenarios.get("in_pdv") else []
        novasol_rules = catalog.novasol_regime_rules if scenarios.get("novasol") else []
        return categories_out, progress, pdv_rules, novasol_rules

    async def get_me(self, host_id: UUID) -> ComplianceMeResponse:
        settings = await self._get_settings(host_id)
        item_map = await self._get_item_map(host_id)
        scenarios = dict(settings.scenarios or {})
        categories, progress, pdv_rules, novasol_rules = self._merge_catalog(
            scenarios, item_map
        )
        hints = await self.get_hints(host_id)
        catalog = get_catalog()
        return ComplianceMeResponse(
            catalog_version=catalog.version,
            scenarios=scenarios,
            categories=categories,
            pdv_regime_rules=pdv_rules,
            novasol_regime_rules=novasol_rules,
            progress=progress,
            hints=hints,
        )

    async def update_scenarios(
        self, host_id: UUID, scenarios: Dict[str, bool]
    ) -> ComplianceMeResponse:
        settings = await self._get_settings(host_id)
        catalog = get_catalog()
        allowed = {s.id for s in catalog.scenarios}
        cleaned = {k: bool(v) for k, v in scenarios.items() if k in allowed}
        settings.scenarios = cleaned
        settings.catalog_version = catalog.version
        settings.updated_at = datetime.utcnow()
        await self.db.commit()
        return await self.get_me(host_id)

    async def patch_item(
        self,
        host_id: UUID,
        item_id: str,
        status: str,
        notes: Optional[str],
    ) -> ComplianceMeResponse:
        catalog = get_catalog()
        known_ids = {
            item.id
            for cat in catalog.categories
            for item in cat.items
        }
        if item_id not in known_ids:
            raise ValueError(f"Unknown compliance item: {item_id}")

        q = select(HostComplianceItem).where(
            HostComplianceItem.host_id == host_id,
            HostComplianceItem.item_id == item_id,
        )
        row = (await self.db.execute(q)).scalar_one_or_none()
        if not row:
            row = HostComplianceItem(host_id=host_id, item_id=item_id)
            self.db.add(row)

        row.status = status
        row.notes = notes
        row.completed_at = datetime.utcnow() if status == "done" else None
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        return await self.get_me(host_id)

    def _build_explain_context(
        self, me: ComplianceMeResponse, item_id: Optional[str]
    ) -> str:
        lines = [
            f"Katalog verzija: {me.catalog_version}",
            f"Aktivni scenariji: {json.dumps(me.scenarios, ensure_ascii=False)}",
            "",
            "Checklist (relevantne stavke):",
        ]
        for cat in me.categories:
            for item in cat.items:
                if item.relevance == "not_applicable":
                    continue
                lines.append(
                    f"- [{item.id}] {item.label_hr} | status={item.status} | {item.summary_hr}"
                )
                if item.detail_hr:
                    lines.append(f"  Detalj: {item.detail_hr[:500]}")

        if me.pdv_regime_rules:
            lines.append("")
            lines.append("PDV pravila iz kataloga:")
            for rule in me.pdv_regime_rules:
                lines.append(f"- {rule.title_hr}: {rule.body_hr}")

        if me.novasol_regime_rules:
            lines.append("")
            lines.append("Novasol pravila iz kataloga:")
            for rule in me.novasol_regime_rules:
                lines.append(f"- {rule.title_hr}: {rule.body_hr}")

        if item_id:
            for cat in me.categories:
                for item in cat.items:
                    if item.id == item_id and item.detail_hr:
                        lines.append("")
                        lines.append(f"Fokus stavka {item_id}: {item.detail_hr}")

        return "\n".join(lines)

    async def explain(
        self,
        host_id: UUID,
        message: str,
        item_id: Optional[str] = None,
    ) -> ComplianceExplainResponse:
        me = await self.get_me(host_id)
        context = self._build_explain_context(me, item_id)

        fallback_answer = None
        if item_id:
            for cat in me.categories:
                for item in cat.items:
                    if item.id == item_id:
                        fallback_answer = item.detail_hr or item.summary_hr
                        break

        ai = AIServiceWithFallback(SettingsService(self.db))
        user_prompt = f"""Kontekst checkliste i PDV pravila:
{context}

Pitanje hosta:
{message}"""

        try:
            host_id_str = str(host_id)
            res = await ai.generate_structured_response(
                host_id_str,
                [
                    {
                        "role": "system",
                        "content": (
                            "Ti si informativni asistent za hrvatske iznajmljivače smještaja (HostForGuest). "
                            "Odgovaraj na hrvatskom. NE daji pravni/porezni savjet — objasni obveze iz konteksta. "
                            + DISCLAIMER_HR
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                context={"task": "compliance_explain", "locale": "hr"},
                response_schema=ComplianceExplainAIResult,
            )
            if res.get("success") and res.get("structured_data"):
                parsed = ComplianceExplainAIResult.model_validate(res["structured_data"])
                return ComplianceExplainResponse(
                    answer_hr=parsed.answer_hr,
                    suggested_item_ids=parsed.suggested_item_ids,
                    disclaimer=DISCLAIMER_HR,
                    ai_used=True,
                )
            if res.get("success") and res.get("response"):
                try:
                    data = json.loads(res["response"])
                    parsed = ComplianceExplainAIResult.model_validate(data)
                    return ComplianceExplainResponse(
                        answer_hr=parsed.answer_hr,
                        suggested_item_ids=parsed.suggested_item_ids,
                        disclaimer=DISCLAIMER_HR,
                        ai_used=True,
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Compliance explain AI failed: %s", e)

        if fallback_answer:
            return ComplianceExplainResponse(
                answer_hr=fallback_answer,
                suggested_item_ids=[item_id] if item_id else [],
                disclaimer=DISCLAIMER_HR,
                ai_used=False,
            )

        return ComplianceExplainResponse(
            answer_hr=(
                "AI trenutno nije dostupan. Pregledajte checklistu i službene linkove uz svaku stavku, "
                "ili se obratite računovođi."
            ),
            suggested_item_ids=[],
            disclaimer=DISCLAIMER_HR,
            ai_used=False,
        )
