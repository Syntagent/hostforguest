"""Host-authenticated cleaning partners, bookings, and AI-assisted discovery."""

from __future__ import annotations

import logging
import uuid
from datetime import date as date_type, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_host
from app.models.host import Host, HostProfile
from app.models.partner import Partner
from app.services.guest_group_service import GuestGroupService
from app.services.host_service import HostService
from app.services.partner_service import PartnerService
from app.services import cleaning_service as cleaning_ai

logger = logging.getLogger(__name__)
router = APIRouter()


def _partner_directory_card(p: Partner) -> Dict[str, Any]:
    """Public directory listing — no contact PII until host links the partner."""
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "partner_type": p.partner_type,
        "category": p.category,
        "city": p.city,
        "region": p.region,
        "price_range": p.price_range,
        "rate_card": p.rate_card or {},
        "price_notes": p.price_notes,
        "commission_rate": p.commission_rate,
        "average_rating": p.average_rating,
        "total_reviews": p.total_reviews,
        "languages_spoken": p.languages_spoken or [],
    }


def _partner_card(p: Partner) -> Dict[str, Any]:
    """Linked partner card — includes actionable contact fields."""
    return {
        **_partner_directory_card(p),
        "email": p.email,
        "phone": p.phone,
        "website": p.website,
        "address": p.address,
    }


class LinkCleanerBody(BaseModel):
    partner_id: uuid.UUID
    priority: int = 0
    partnership_notes: Optional[str] = None


class DiscoverBody(BaseModel):
    intent: str = "turnover"
    city: Optional[str] = None


class DraftMessageBody(BaseModel):
    partner_id: uuid.UUID
    intent: str = "turnover"
    service_date: Optional[str] = None
    guest_group_id: Optional[uuid.UUID] = None
    language: str = "hr"


class CreateCleaningBookingBody(BaseModel):
    partner_id: uuid.UUID
    service_date: Optional[datetime] = None
    guest_group_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    intent: str = "turnover"
    estimated_amount: float = 0.0
    currency: str = "EUR"


class BookingStatusBody(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|cancelled|completed)$")


class FeedbackBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class CleaningNextCheckoutHint(BaseModel):
    guest_group_id: str
    group_name: Optional[str] = None
    check_out_date: str


class CleaningMessageContextResponse(BaseModel):
    """GET /cleaning/message-context — property hints for draft templates."""

    property_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    next_checkout: Optional[CleaningNextCheckoutHint] = None


class CleaningUpcomingCheckoutItem(BaseModel):
    guest_group_id: str
    group_name: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: str
    group_size: int


class CleaningUpcomingCheckoutsResponse(BaseModel):
    checkouts: List[CleaningUpcomingCheckoutItem] = Field(default_factory=list)


class CleaningProviderDirectoryCard(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    partner_type: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    price_range: Optional[str] = None
    rate_card: Dict[str, Any] = Field(default_factory=dict)
    price_notes: Optional[str] = None
    commission_rate: Optional[float] = None
    average_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    languages_spoken: List[str] = Field(default_factory=list)


class CleaningProvidersResponse(BaseModel):
    disclaimer_indicative_fees: str
    providers: List[CleaningProviderDirectoryCard] = Field(default_factory=list)


class CleaningProviderLinkedCard(CleaningProviderDirectoryCard):
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None


class CleaningProviderRelationshipResponse(BaseModel):
    priority: Optional[int] = None
    status: Optional[str] = None
    commission_rate: Optional[float] = None
    partnership_notes: Optional[str] = None


class CleaningMyCleanerRow(BaseModel):
    partner: CleaningProviderLinkedCard
    relationship: CleaningProviderRelationshipResponse


class CleaningMyCleanersResponse(BaseModel):
    cleaners: List[CleaningMyCleanerRow] = Field(default_factory=list)


class CleaningLinkResponse(BaseModel):
    success: bool = True
    relationship_id: str


class CleaningSuccessResponse(BaseModel):
    success: bool = True


class CleaningDiscoverRankedItem(CleaningProviderDirectoryCard):
    ai_why: str = ""


class CleaningDiscoverResponse(BaseModel):
    disclaimer: Optional[str] = None
    ai_used: Optional[bool] = None
    fallback_reason: Optional[str] = None
    ranked: List[CleaningDiscoverRankedItem] = Field(default_factory=list)


class CleaningDraftMessageResponse(BaseModel):
    draft: str
    ai_used: bool = False
    fallback_reason: Optional[str] = None
    model: Optional[str] = None


class CleaningBookingResponse(BaseModel):
    id: str
    partner_id: Optional[str] = None
    guest_group_id: Optional[str] = None
    service_date: Optional[str] = None
    status: str
    notes: Optional[str] = None
    booking_amount: float
    currency: str
    booking_details: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class CleaningBookingListResponse(BaseModel):
    bookings: List[CleaningBookingResponse] = Field(default_factory=list)


class CleaningBookingCreateResponse(BaseModel):
    id: str
    status: str


class CleaningBookingStatusResponse(BaseModel):
    id: str
    status: str


class CleaningBookingFeedbackResponse(BaseModel):
    success: bool = True
    booking_id: str


@router.get("/message-context", response_model=CleaningMessageContextResponse)
async def message_context(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Property + next checkout hints for cleaning message templates (host session)."""
    stmt = select(HostProfile).where(HostProfile.host_id == current_host.id)
    result = await db.execute(stmt)
    prof = result.scalar_one_or_none()
    gsvc = GuestGroupService(db)
    groups = await gsvc.get_host_guest_groups(current_host.id, include_completed=True)
    now = datetime.utcnow()
    next_checkout: Optional[Dict[str, Any]] = None
    best_end: Optional[datetime] = None
    for g in groups:
        cod = getattr(g, "check_out_date", None)
        if cod is None:
            continue
        end = cod
        if isinstance(cod, date_type) and not isinstance(cod, datetime):
            end = datetime.combine(cod, datetime.min.time())
        if not isinstance(end, datetime):
            continue
        if end < now:
            continue
        if best_end is None or end < best_end:
            best_end = end
            next_checkout = {
                "guest_group_id": str(g.id),
                "group_name": g.group_name,
                "check_out_date": end.isoformat(),
            }
    return CleaningMessageContextResponse(
        property_name=prof.property_name if prof else None,
        address=(prof.address if prof else None) or current_host.address,
        city=(prof.city if prof else None) or current_host.city,
        county=current_host.county,
        next_checkout=(
            CleaningNextCheckoutHint(**next_checkout) if next_checkout else None
        ),
    )


@router.get("/providers", response_model=CleaningProvidersResponse)
async def list_cleaning_providers(
    city: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    loc_city = (city or current_host.city or "").strip() or None
    loc_region = (region or current_host.county or "").strip() or None
    partners = await svc.list_cleaning_partners(city=loc_city, region=loc_region, limit=80)
    return CleaningProvidersResponse(
        disclaimer_indicative_fees=(
            "Fees and rate_card are indicative only. Always confirm price and scope with the provider."
        ),
        providers=[CleaningProviderDirectoryCard(**_partner_directory_card(p)) for p in partners],
    )


@router.get("/my-cleaners", response_model=CleaningMyCleanersResponse)
async def my_cleaners(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    rows = await svc.get_host_partners(current_host.id)
    out: List[CleaningMyCleanerRow] = []
    for row in rows:
        p: Partner = row["partner"]
        if not svc._is_cleaning_partner_row(p):
            continue
        rel = row.get("relationship")
        out.append(
            CleaningMyCleanerRow(
                partner=CleaningProviderLinkedCard(**_partner_card(p)),
                relationship=CleaningProviderRelationshipResponse(
                    priority=row.get("priority"),
                    status=rel.status if rel else None,
                    commission_rate=row.get("commission_rate"),
                    partnership_notes=rel.partnership_notes if rel else None,
                ),
            )
        )
    return CleaningMyCleanersResponse(cleaners=out)


@router.post("/my-cleaners", status_code=status.HTTP_201_CREATED, response_model=CleaningLinkResponse)
async def link_my_cleaner(
    body: LinkCleanerBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    p = await svc.get_partner(body.partner_id)
    if not p or not svc._is_cleaning_partner_row(p):
        raise HTTPException(status_code=400, detail="Not a cleaning partner")
    rel = await svc.create_host_partner_relationship(
        current_host.id,
        body.partner_id,
        {
            "priority": body.priority,
            "partnership_notes": body.partnership_notes,
            "status": "active",
        },
    )
    if not rel:
        raise HTTPException(status_code=500, detail="Could not link cleaner")
    return CleaningLinkResponse(success=True, relationship_id=str(rel.id))


@router.delete("/my-cleaners/{partner_id}", response_model=CleaningSuccessResponse)
async def unlink_my_cleaner(
    partner_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    ok = await svc.remove_host_partner(current_host.id, partner_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not unlink")
    return CleaningSuccessResponse(success=True)


@router.get("/upcoming-checkouts", response_model=CleaningUpcomingCheckoutsResponse)
async def upcoming_checkouts(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    gsvc = GuestGroupService(db)
    groups = await gsvc.get_host_guest_groups(current_host.id, include_completed=True)
    now = datetime.utcnow()
    upcoming: List[Dict[str, Any]] = []
    for g in groups:
        cod = getattr(g, "check_out_date", None)
        if cod is None:
            continue
        end = cod
        if isinstance(cod, date_type) and not isinstance(cod, datetime):
            end = datetime.combine(cod, datetime.min.time())
        if not isinstance(end, datetime):
            continue
        if end >= now:
            cin = getattr(g, "check_in_date", None)
            cin_s = None
            if isinstance(cin, datetime):
                cin_s = cin.isoformat()
            elif hasattr(cin, "isoformat"):
                cin_s = cin.isoformat()
            upcoming.append(
                {
                    "guest_group_id": str(g.id),
                    "group_name": g.group_name,
                    "check_in_date": cin_s,
                    "check_out_date": end.isoformat(),
                    "group_size": g.group_size,
                }
            )
    upcoming.sort(key=lambda x: x["check_out_date"] or "")
    return CleaningUpcomingCheckoutsResponse(
        checkouts=[CleaningUpcomingCheckoutItem(**row) for row in upcoming[:24]]
    )


@router.post("/discover", response_model=CleaningDiscoverResponse)
async def discover_cleaners(
    body: DiscoverBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    city = (body.city or current_host.city or "").strip() or None
    candidates = await svc.list_cleaning_partners(city=city, region=None, limit=25)
    ranked_meta = await cleaning_ai.rank_cleaning_partners_with_ai(db, current_host, candidates, body.intent)
    by_id = {str(p.id): p for p in candidates}
    enriched: List[CleaningDiscoverRankedItem] = []
    for row in ranked_meta.get("ranked") or []:
        pid = row.get("partner_id")
        p = by_id.get(str(pid))
        if p:
            enriched.append(
                CleaningDiscoverRankedItem(
                    **_partner_directory_card(p),
                    ai_why=row.get("why", "") or "",
                )
            )
    return CleaningDiscoverResponse(
        disclaimer=ranked_meta.get("disclaimer"),
        ai_used=ranked_meta.get("ai_used"),
        fallback_reason=ranked_meta.get("fallback_reason"),
        ranked=enriched,
    )


@router.post("/draft-message", response_model=CleaningDraftMessageResponse)
async def draft_message(
    body: DraftMessageBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    if not await svc.host_has_partner_link(current_host.id, body.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    p = await svc.get_partner(body.partner_id)
    if not p or not svc._is_cleaning_partner_row(p):
        raise HTTPException(status_code=400, detail="Not a cleaning partner")
    hint = None
    if body.guest_group_id:
        gsvc = GuestGroupService(db)
        groups = await gsvc.get_host_guest_groups(current_host.id, include_completed=True)
        for g in groups:
            if str(g.id) == str(body.guest_group_id):
                hint = f"Checkout {g.check_out_date}, group {g.group_name or g.id}"
                break
    result = await cleaning_ai.draft_cleaning_message(
        db,
        current_host,
        p,
        body.intent,
        body.service_date,
        hint,
        body.language,
    )
    return CleaningDraftMessageResponse(**result)


@router.get("/bookings", response_model=CleaningBookingListResponse)
async def list_bookings(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    bookings = await svc.list_host_cleaning_bookings(current_host.id, limit=50)
    out: List[CleaningBookingResponse] = []
    for b in bookings:
        out.append(
            CleaningBookingResponse(
                id=str(b.id),
                partner_id=str(b.partner_id) if b.partner_id else None,
                guest_group_id=str(b.guest_group_id) if b.guest_group_id else None,
                service_date=b.service_date.isoformat() if b.service_date else None,
                status=b.status,
                notes=b.notes,
                booking_amount=b.booking_amount,
                currency=b.currency,
                booking_details=b.booking_details or {},
                created_at=b.created_at.isoformat() if b.created_at else None,
            )
        )
    return CleaningBookingListResponse(bookings=out)


@router.post("/bookings", status_code=status.HTTP_201_CREATED, response_model=CleaningBookingCreateResponse)
async def create_booking(
    body: CreateCleaningBookingBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    if not await svc.host_has_partner_link(current_host.id, body.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    if body.guest_group_id:
        gsvc = GuestGroupService(db)
        groups = await gsvc.get_host_guest_groups(current_host.id, include_completed=True)
        if not any(str(g.id) == str(body.guest_group_id) for g in groups):
            raise HTTPException(status_code=400, detail="guest_group_id not found for this host")
    b = await svc.create_cleaning_booking(
        current_host.id,
        body.partner_id,
        service_date=body.service_date,
        guest_group_id=body.guest_group_id,
        notes=body.notes,
        intent=body.intent,
        estimated_amount=body.estimated_amount,
        currency=body.currency,
    )
    if not b:
        raise HTTPException(status_code=400, detail="Could not create booking")
    return CleaningBookingCreateResponse(id=str(b.id), status=b.status)


@router.patch("/bookings/{booking_id}/status", response_model=CleaningBookingStatusResponse)
async def patch_booking_status(
    booking_id: uuid.UUID,
    body: BookingStatusBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    b = await svc.update_cleaning_booking_status(booking_id, current_host.id, body.status)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return CleaningBookingStatusResponse(id=str(b.id), status=b.status)


@router.post("/bookings/{booking_id}/feedback", response_model=CleaningBookingFeedbackResponse)
async def post_feedback(
    booking_id: uuid.UUID,
    body: FeedbackBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = PartnerService(db)
    b = await svc.submit_cleaning_booking_feedback(
        booking_id, current_host.id, body.rating, body.comment
    )
    if not b:
        raise HTTPException(status_code=400, detail="Feedback not allowed (must be completed booking, once only)")
    return CleaningBookingFeedbackResponse(success=True, booking_id=str(b.id))
