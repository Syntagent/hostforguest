"""
Maintenance issues, schedules, AI partner assist, guest reports, webhook.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.host import Host
from app.models.partner import Partner
from app.models.maintenance import MaintenanceIssue
from app.api.v1.hosts import get_current_host
from app.services.guest_group_service import GuestGroupService
from app.services.maintenance_service import MaintenanceService, MAINTENANCE_CATEGORIES
from app.services.maintenance_ai_service import MaintenanceAIService

logger = logging.getLogger(__name__)
router = APIRouter()


class MaintenanceIssueCreate(BaseModel):
    category: str = Field(..., max_length=80)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    priority: str = "normal"
    photo_urls: List[str] = Field(default_factory=list)
    due_at: Optional[datetime] = None


class MaintenanceIssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    due_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class GuestMaintenanceReportCreate(BaseModel):
    access_code: str = Field(..., min_length=6, max_length=20)
    category: str
    title: str
    description: Optional[str] = None
    photo_urls: List[str] = Field(default_factory=list)


class MaintenanceScheduleCreate(BaseModel):
    title: str
    category: str
    interval_days: int = Field(ge=1, le=3650)
    next_due_at: Optional[datetime] = None


class DraftMessageBody(BaseModel):
    partner_id: uuid.UUID
    tone: str = "formal"
    channel: str = "whatsapp"
    include_guest_contact: bool = False


class ReplySuggestionsBody(BaseModel):
    inbound_text: str = Field(..., min_length=1, max_length=8000)


class SaveDraftBody(BaseModel):
    partner_id: uuid.UUID
    channel: str = "whatsapp"
    draft_text: str
    host_edited: bool = True


def _issue_dict(i: MaintenanceIssue) -> Dict[str, Any]:
    return {
        "id": str(i.id),
        "host_id": str(i.host_id),
        "guest_group_id": str(i.guest_group_id) if i.guest_group_id else None,
        "category": i.category,
        "title": i.title,
        "description": i.description,
        "status": i.status,
        "priority": i.priority,
        "photo_urls": i.photo_urls or [],
        "due_at": i.due_at.isoformat() if i.due_at else None,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        "source": i.source,
        "source_metadata": i.source_metadata or {},
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


@router.get("/categories")
async def list_categories():
    return {"categories": MAINTENANCE_CATEGORIES}


@router.get("/issues")
async def list_issues(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issues = await svc.list_issues(current_host.id)
    return {"issues": [_issue_dict(i) for i in issues]}


@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    body: MaintenanceIssueCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    if body.category not in MAINTENANCE_CATEGORIES and body.category != "other":
        pass
    svc = MaintenanceService(db)
    issue = await svc.create_issue(
        current_host.id,
        category=body.category,
        title=body.title,
        description=body.description,
        priority=body.priority,
        photo_urls=body.photo_urls,
        due_at=body.due_at,
        source="host",
    )
    return _issue_dict(issue)


@router.get("/issues/{issue_id}")
async def get_issue(
    issue_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issue = await svc.get_issue(current_host.id, issue_id)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    return _issue_dict(issue)


@router.patch("/issues/{issue_id}")
async def patch_issue(
    issue_id: uuid.UUID,
    body: MaintenanceIssueUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    data = body.model_dump(exclude_unset=True)
    issue = await svc.update_issue(current_host.id, issue_id, **data)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    return _issue_dict(issue)


@router.post("/guest-reports", status_code=status.HTTP_201_CREATED)
async def guest_report(
    body: GuestMaintenanceReportCreate,
    db: AsyncSession = Depends(get_db),
):
    gsvc = GuestGroupService(db)
    group = await gsvc.validate_access_code(body.access_code)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired access code")
    svc = MaintenanceService(db)
    issue = await svc.create_guest_report_for_group(
        group,
        category=body.category,
        title=body.title,
        description=body.description,
        photo_urls=body.photo_urls,
    )
    return _issue_dict(issue)


@router.get("/schedules")
async def list_schedules(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    rows = await svc.list_schedules(current_host.id)
    return {
        "schedules": [
            {
                "id": str(s.id),
                "title": s.title,
                "category": s.category,
                "interval_days": s.interval_days,
                "active": s.active,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "next_due_at": s.next_due_at.isoformat() if s.next_due_at else None,
            }
            for s in rows
        ]
    }


@router.post("/schedules", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: MaintenanceScheduleCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    sch = await svc.create_schedule(
        current_host.id,
        title=body.title,
        category=body.category,
        interval_days=body.interval_days,
        next_due_at=body.next_due_at,
    )
    return {
        "id": str(sch.id),
        "title": sch.title,
        "category": sch.category,
        "interval_days": sch.interval_days,
        "next_due_at": sch.next_due_at.isoformat() if sch.next_due_at else None,
    }


@router.post("/run-preventive")
async def run_preventive(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    created = await svc.run_due_schedules(current_host.id)
    return {"created_count": len(created), "issues": [_issue_dict(i) for i in created]}


@router.post("/issues/{issue_id}/suggest-partners")
async def suggest_partners(
    issue_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issue = await svc.get_issue(current_host.id, issue_id)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    ai = MaintenanceAIService(db)
    return await ai.suggest_partners_ranked(current_host, issue)


@router.post("/issues/{issue_id}/draft-message")
async def draft_message(
    issue_id: uuid.UUID,
    body: DraftMessageBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issue = await svc.get_issue(current_host.id, issue_id)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    pr = await db.execute(select(Partner).where(Partner.id == body.partner_id))
    partner = pr.scalar_one_or_none()
    if not partner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner not found")
    ai = MaintenanceAIService(db)
    out = await ai.draft_message(
        current_host,
        issue,
        partner,
        tone=body.tone,
        channel=body.channel,
        include_guest_contact=body.include_guest_contact,
    )
    return out


@router.post("/issues/{issue_id}/save-draft")
async def save_draft(
    issue_id: uuid.UUID,
    body: SaveDraftBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issue = await svc.get_issue(current_host.id, issue_id)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    d = await svc.save_outreach_draft(
        issue_id,
        body.partner_id,
        body.channel,
        body.draft_text,
        body.host_edited,
    )
    return {"id": str(d.id), "created_at": d.created_at.isoformat() if d.created_at else None}


@router.post("/issues/{issue_id}/reply-suggestions")
async def reply_suggestions(
    issue_id: uuid.UUID,
    body: ReplySuggestionsBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = MaintenanceService(db)
    issue = await svc.get_issue(current_host.id, issue_id)
    if not issue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    ai = MaintenanceAIService(db)
    return await ai.reply_suggestions(current_host, body.inbound_text)


def _verify_maint_sig(body: bytes, signature_header: str, secret: str) -> bool:
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhook")
async def maintenance_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Maintenance-Signature") or ""
    secret = (settings.maintenance_webhook_secret or "").strip()
    if secret and not _verify_maint_sig(body, sig, secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
    try:
        data = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON")
    try:
        host_id = uuid.UUID(str(data.get("host_id")))
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "host_id required (UUID)")
    category = str(data.get("category") or "other")
    title = str(data.get("title") or "Webhook report")
    description = data.get("description")
    svc = MaintenanceService(db)
    host = await svc.get_host_for_webhook(host_id)
    if not host:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown host")
    issue = await svc.create_issue(
        host_id,
        category=category,
        title=title,
        description=description,
        source="webhook",
        source_metadata={"raw_keys": list(data.keys())},
    )
    return {"ok": True, "issue_id": str(issue.id)}
