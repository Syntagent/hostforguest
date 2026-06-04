"""
Model-driven discovery of local event sources for a host property location.

Uses LLM with structured context — not keyword routing.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_source import ContentSource
from app.models.event_source_proposal import EventSourceProposal
from app.models.host import Host, HostProfile
from app.scraping.events.sources import load_national_event_sources
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

DISCOVERY_SYSTEM = """You are a tourism data researcher for Croatia.
Given a host property location, propose official event calendar sources (turistička zajednica,
city tourist boards, regional boards). Return ONLY valid JSON array, no markdown.
Each item: {"proposed_name": str, "proposed_url": str, "source_type": "local_office"|"tourism_board"|"event_calendar", "confidence": 0.0-1.0, "reasoning": str}
Prefer .hr domains and official tourism offices. Do not propose Facebook or login-walled sites."""


class EventSourceDiscoveryAgent:
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        self.db = db
        self.ai = ai_service or AIService()

    async def discover_for_host(
        self,
        host: Host,
        profile: Optional[HostProfile],
        *,
        max_proposals: int = 10,
    ) -> Dict[str, Any]:
        ctx = self._build_context(host, profile)
        proposals = await self._propose_sources(ctx, host.id, max_proposals=max_proposals)
        return {
            "success": True,
            "context": ctx,
            "proposals_created": len(proposals),
            "proposal_ids": [str(p.id) for p in proposals],
        }

    def _build_context(
        self, host: Host, profile: Optional[HostProfile]
    ) -> Dict[str, Any]:
        city = None
        region = None
        lat = None
        lng = None
        if profile:
            city = profile.city
            region = profile.county
            if profile.latitude is not None:
                lat = float(profile.latitude)
            if profile.longitude is not None:
                lng = float(profile.longitude)

        existing_urls = [d["url"] for d in load_national_event_sources()]
        return {
            "city": city or "Lovran",
            "region": region or "Kvarner",
            "lat": lat,
            "lng": lng,
            "country": "Croatia",
            "existing_registry_urls": existing_urls[:20],
        }

    async def _load_existing_urls(self) -> List[str]:
        result = await self.db.execute(select(ContentSource.url))
        return [str(u) for u in result.scalars().all() if u]

    async def _propose_sources(
        self,
        ctx: Dict[str, Any],
        host_id: uuid.UUID,
        *,
        max_proposals: int,
    ) -> List[EventSourceProposal]:
        existing_urls = set(await self._load_existing_urls())
        existing_urls.update(ctx.get("existing_registry_urls") or [])

        prompt = (
            f"Property city: {ctx.get('city')}\n"
            f"Region: {ctx.get('region')}\n"
            f"Coordinates: {ctx.get('lat')}, {ctx.get('lng')}\n"
            f"Already monitored URLs (do not duplicate): {list(existing_urls)[:15]}\n"
            f"Propose up to {max_proposals} new official event listing sources."
        )

        raw = await self._call_llm(prompt, str(host_id))
        items = self._parse_proposals_json(raw)
        created: List[EventSourceProposal] = []

        for item in items[:max_proposals]:
            url = str(item.get("proposed_url") or "").strip()
            if not url or url in existing_urls:
                continue
            if not url.startswith("http"):
                continue
            dup = await self.db.execute(
                select(EventSourceProposal).where(
                    and_(
                        EventSourceProposal.host_id == host_id,
                        EventSourceProposal.proposed_url == url,
                        EventSourceProposal.status == "pending",
                    )
                )
            )
            if dup.scalar_one_or_none():
                continue

            proposal = EventSourceProposal(
                host_id=host_id,
                city=ctx.get("city"),
                region=ctx.get("region"),
                lat=ctx.get("lat"),
                lng=ctx.get("lng"),
                proposed_name=str(item.get("proposed_name") or url)[:200],
                proposed_url=url[:500],
                source_type=str(item.get("source_type") or "local_office"),
                confidence=float(item.get("confidence") or 0.5),
                reasoning=str(item.get("reasoning") or "")[:2000],
                discovered_by="discovery_agent_v1",
                status="pending",
            )
            self.db.add(proposal)
            created.append(proposal)
            existing_urls.add(url)

        if created:
            await self.db.commit()
            for p in created:
                await self.db.refresh(p)
        return created

    async def _call_llm(self, prompt: str, host_id: str) -> str:
        try:
            result = await self.ai.generate_events_extraction(
                host_id=host_id,
                messages=[
                    {"role": "system", "content": DISCOVERY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            )
            if isinstance(result, dict):
                return str(result.get("response") or result.get("content") or "[]")
            return str(result or "[]")
        except Exception as exc:
            logger.warning("Discovery LLM unavailable, using fallback registry: %s", exc)
            return self._fallback_proposals_json()

    def _fallback_proposals_json(self) -> str:
        """Conservative fallback when AI is unavailable — not pretending to be intelligent discovery."""
        items = []
        for defn in load_national_event_sources()[:5]:
            items.append(
                {
                    "proposed_name": defn["name"],
                    "proposed_url": defn["listing_url"],
                    "source_type": "local_office",
                    "confidence": 0.4,
                    "reasoning": "National registry fallback (AI unavailable).",
                }
            )
        return json.dumps(items)

    def _parse_proposals_json(self, raw: str) -> List[Dict[str, Any]]:
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            arr = re.search(r"\[[\s\S]*\]", text)
            if not arr:
                return []
            try:
                data = json.loads(arr.group(0))
            except json.JSONDecodeError:
                return []
        if isinstance(data, dict) and "proposals" in data:
            data = data["proposals"]
        if not isinstance(data, list):
            return []
        return [x for x in data if isinstance(x, dict)]

    async def approve_proposal(
        self, proposal_id: uuid.UUID, host_id: uuid.UUID
    ) -> Optional[ContentSource]:
        from app.models.content_source import ContentSourceCreate, ContentType, SourceType
        from app.services.content_scraper_service import ContentScraperService

        row = await self.db.execute(
            select(EventSourceProposal).where(
                and_(
                    EventSourceProposal.id == proposal_id,
                    EventSourceProposal.host_id == host_id,
                )
            )
        )
        proposal = row.scalar_one_or_none()
        if not proposal or proposal.status != "pending":
            return None

        scraper = ContentScraperService(self.db)
        source = await scraper.create_content_source(
            ContentSourceCreate(
                name=proposal.proposed_name,
                url=proposal.proposed_url,
                source_type=SourceType.EVENT_CALENDAR,
                region=proposal.region,
                city=proposal.city,
                content_types=[ContentType.EVENTS],
                scraping_enabled=True,
                scraping_frequency="weekly",
            )
        )
        proposal.status = "approved"
        proposal.approved_source_id = source.id if source else None
        await self.db.commit()
        return source

    async def reject_proposal(self, proposal_id: uuid.UUID, host_id: uuid.UUID) -> bool:
        row = await self.db.execute(
            select(EventSourceProposal).where(
                and_(
                    EventSourceProposal.id == proposal_id,
                    EventSourceProposal.host_id == host_id,
                )
            )
        )
        proposal = row.scalar_one_or_none()
        if not proposal:
            return False
        proposal.status = "rejected"
        await self.db.commit()
        return True
