"""
Maintenance issues and schedules for hosts.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.guest_group import GuestGroup
from app.models.partner import Partner, HostPartner, PartnerStatus
from app.models.maintenance import (
    MaintenanceIssue,
    MaintenanceSchedule,
    MaintenanceIssueEvent,
    MaintenanceOutreachDraft,
)

logger = logging.getLogger(__name__)

MAINTENANCE_CATEGORIES = [
    "hvac",
    "plumbing",
    "electrical",
    "appliances",
    "structure",
    "exterior",
    "safety",
    "cleaning",
    "connectivity",
    "other",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 2 * r * math.asin(math.sqrt(a))


class MaintenanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _partner_matches_category(self, partner: Partner, category: str) -> bool:
        cats = partner.trade_categories or []
        if not cats:
            fallback_types = ("trades", "service", "retail", "other")
            if category == "cleaning":
                return partner.partner_type in fallback_types + ("cleaning",)
            return partner.partner_type in fallback_types
        return category in cats or "other" in cats

    async def list_issues(self, host_id: uuid.UUID) -> List[MaintenanceIssue]:
        r = await self.db.execute(
            select(MaintenanceIssue)
            .where(MaintenanceIssue.host_id == host_id)
            .order_by(MaintenanceIssue.created_at.desc())
        )
        return list(r.scalars().all())

    async def get_issue(self, host_id: uuid.UUID, issue_id: uuid.UUID) -> Optional[MaintenanceIssue]:
        r = await self.db.execute(
            select(MaintenanceIssue).where(
                and_(MaintenanceIssue.id == issue_id, MaintenanceIssue.host_id == host_id)
            )
        )
        return r.scalar_one_or_none()

    async def create_issue(
        self,
        host_id: uuid.UUID,
        *,
        category: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "normal",
        status: str = "open",
        guest_group_id: Optional[uuid.UUID] = None,
        photo_urls: Optional[List[str]] = None,
        due_at: Optional[datetime] = None,
        source: str = "host",
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> MaintenanceIssue:
        issue = MaintenanceIssue(
            host_id=host_id,
            guest_group_id=guest_group_id,
            category=category,
            title=title,
            description=description,
            status=status,
            priority=priority,
            photo_urls=photo_urls or [],
            due_at=due_at,
            source=source,
            source_metadata=source_metadata or {},
        )
        self.db.add(issue)
        await self.db.flush()
        await self._add_event(issue.id, "created", {"source": source})
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def update_issue(
        self,
        host_id: uuid.UUID,
        issue_id: uuid.UUID,
        **fields: Any,
    ) -> Optional[MaintenanceIssue]:
        issue = await self.get_issue(host_id, issue_id)
        if not issue:
            return None
        allowed = {
            "title",
            "description",
            "category",
            "status",
            "priority",
            "photo_urls",
            "due_at",
            "resolved_at",
        }
        for k, v in fields.items():
            if k in allowed and v is not None:
                setattr(issue, k, v)
        if fields.get("status") == "resolved" and not issue.resolved_at:
            issue.resolved_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def _add_event(self, issue_id: uuid.UUID, event_type: str, payload: Dict[str, Any]) -> None:
        ev = MaintenanceIssueEvent(issue_id=issue_id, event_type=event_type, payload=payload)
        self.db.add(ev)

    async def list_issues_for_guest_group(self, guest_group_id: uuid.UUID) -> List[MaintenanceIssue]:
        r = await self.db.execute(
            select(MaintenanceIssue)
            .where(
                and_(
                    MaintenanceIssue.guest_group_id == guest_group_id,
                    MaintenanceIssue.source == "guest",
                )
            )
            .order_by(MaintenanceIssue.created_at.desc())
        )
        return list(r.scalars().all())

    async def create_guest_report_for_group(
        self,
        group: GuestGroup,
        *,
        category: str,
        title: str,
        description: Optional[str],
        photo_urls: Optional[List[str]],
    ) -> MaintenanceIssue:
        issue = MaintenanceIssue(
            host_id=group.host_id,
            guest_group_id=group.id,
            category=category,
            title=title,
            description=description,
            status="open",
            priority="normal",
            photo_urls=photo_urls or [],
            source="guest",
            source_metadata={"guest_group_id": str(group.id)},
        )
        self.db.add(issue)
        await self.db.flush()
        await self._add_event(issue.id, "created", {"source": "guest"})
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def get_host_for_webhook(self, host_id: uuid.UUID) -> Optional[Host]:
        r = await self.db.execute(select(Host).where(Host.id == host_id))
        return r.scalar_one_or_none()

    async def create_issue_from_webhook(
        self,
        host_id: uuid.UUID,
        category: str,
        title: str,
        description: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MaintenanceIssue:
        return await self.create_issue(
            host_id,
            category=category,
            title=title,
            description=description,
            source="webhook",
            source_metadata=metadata or {},
        )

    async def list_schedules(self, host_id: uuid.UUID) -> List[MaintenanceSchedule]:
        r = await self.db.execute(
            select(MaintenanceSchedule).where(MaintenanceSchedule.host_id == host_id)
        )
        return list(r.scalars().all())

    async def create_schedule(
        self,
        host_id: uuid.UUID,
        *,
        title: str,
        category: str,
        interval_days: int,
        next_due_at: Optional[datetime] = None,
    ) -> MaintenanceSchedule:
        due = next_due_at or (datetime.utcnow() + timedelta(days=interval_days))
        sch = MaintenanceSchedule(
            host_id=host_id,
            title=title,
            category=category,
            interval_days=interval_days,
            next_due_at=due,
            active=True,
        )
        self.db.add(sch)
        await self.db.commit()
        await self.db.refresh(sch)
        return sch

    async def run_due_schedules(self, host_id: uuid.UUID) -> List[MaintenanceIssue]:
        now = datetime.utcnow()
        r = await self.db.execute(
            select(MaintenanceSchedule).where(
                and_(
                    MaintenanceSchedule.host_id == host_id,
                    MaintenanceSchedule.active == True,  # noqa: E712
                    MaintenanceSchedule.next_due_at.is_not(None),
                    MaintenanceSchedule.next_due_at <= now,
                )
            )
        )
        schedules = list(r.scalars().all())
        created: List[MaintenanceIssue] = []
        for sch in schedules:
            issue = MaintenanceIssue(
                host_id=host_id,
                category=sch.category,
                title=f"[Preventive] {sch.title}",
                description="Opened automatically from maintenance schedule.",
                status="open",
                priority="low",
                source="preventive",
                source_metadata={"schedule_id": str(sch.id)},
            )
            self.db.add(issue)
            await self.db.flush()
            await self._add_event(issue.id, "created", {"schedule_id": str(sch.id)})
            sch.last_run_at = now
            sch.next_due_at = now + timedelta(days=sch.interval_days)
            created.append(issue)
        if created:
            await self.db.commit()
            for i in created:
                await self.db.refresh(i)
        return created

    async def run_all_due_schedules_for_all_hosts(self) -> List[MaintenanceIssue]:
        """
        Process every host that has at least one active maintenance schedule past due.

        Intended for cron / background workers; delegates to ``run_due_schedules`` per host
        so schedule bookkeeping stays identical to the host-triggered path.
        """
        now = datetime.utcnow()
        hr = await self.db.execute(
            select(MaintenanceSchedule.host_id)
            .where(
                and_(
                    MaintenanceSchedule.active == True,  # noqa: E712
                    MaintenanceSchedule.next_due_at.is_not(None),
                    MaintenanceSchedule.next_due_at <= now,
                )
            )
            .distinct()
        )
        host_ids = [row[0] for row in hr.all()]
        all_created: List[MaintenanceIssue] = []
        for hid in host_ids:
            chunk = await self.run_due_schedules(hid)
            all_created.extend(chunk)
        return all_created

    async def fetch_partner_candidates(
        self,
        host: Host,
        category: str,
        limit: int = 24,
        *,
        linked_only: bool = False,
    ) -> List[Tuple[Partner, Optional[float]]]:
        """Returns (partner, distance_km or None)."""
        linked_ids: List[uuid.UUID] = []
        lr = await self.db.execute(
            select(HostPartner.partner_id).where(
                and_(
                    HostPartner.host_id == host.id,
                    HostPartner.status == PartnerStatus.ACTIVE.value,
                )
            )
        )
        linked_ids = [row[0] for row in lr.all()]

        if linked_only and not linked_ids:
            return []

        stmt = select(Partner).where(Partner.status == PartnerStatus.ACTIVE.value)
        if linked_only:
            stmt = stmt.where(Partner.id.in_(linked_ids))
        pr = await self.db.execute(stmt)
        all_p = list(pr.scalars().all())

        host_lat = host.latitude
        host_lon = host.longitude

        scored: List[Tuple[Partner, Optional[float], int]] = []
        for p in all_p:
            if not self._partner_matches_category(p, category):
                continue
            dist: Optional[float] = None
            if (
                host_lat is not None
                and host_lon is not None
                and p.latitude is not None
                and p.longitude is not None
            ):
                dist = haversine_km(float(host_lat), float(host_lon), float(p.latitude), float(p.longitude))
            pri = 0 if p.id in linked_ids else 1
            city_match = 1 if (host.city and p.city and host.city.lower() == p.city.lower()) else 2
            scored.append((p, dist, pri * 10 + city_match))

        scored.sort(key=lambda x: (x[2], x[1] if x[1] is not None else 1e9))
        out: List[Tuple[Partner, Optional[float]]] = []
        for p, dist, _ in scored[:limit]:
            out.append((p, dist))
        return out

    async def save_outreach_draft(
        self,
        issue_id: uuid.UUID,
        partner_id: uuid.UUID,
        channel: str,
        draft_text: str,
        host_edited: bool,
    ) -> MaintenanceOutreachDraft:
        d = MaintenanceOutreachDraft(
            issue_id=issue_id,
            partner_id=partner_id,
            channel=channel,
            draft_text=draft_text,
            host_edited=host_edited,
        )
        self.db.add(d)
        await self.db.commit()
        await self.db.refresh(d)
        return d
