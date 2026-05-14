"""
Partner API endpoints for business partner management.

Provides REST API endpoints for managing business partners,
host-partner relationships, and commission tracking.
"""

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.partner_service import PartnerService
from app.services.host_service import HostService
from app.models.partner import Partner, PartnerType, PartnerStatus
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_current_host(request: Request, db: AsyncSession = Depends(get_db)) -> Host:
    """Require X-Session-Token for host-scoped partner relationship routes."""
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required",
        )
    host_service = HostService(db)
    host = await host_service.get_current_host_from_session(session_token)
    if not host:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return host


def _require_self_host(host_id: str, current_host: Host) -> None:
    if str(current_host.id) != host_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access another host's partner links",
        )


def _partner_contact_payload(p: Partner) -> dict:
    """Full partner fields for authenticated host views (not used on public list/get)."""
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "partner_type": p.partner_type,
        "category": p.category,
        "city": p.city,
        "region": p.region,
        "email": p.email,
        "phone": p.phone,
        "website": p.website,
        "address": p.address,
        "price_range": p.price_range,
        "rate_card": p.rate_card or {},
        "price_notes": p.price_notes,
        "languages_spoken": p.languages_spoken or [],
    }


# Pydantic Models
class PartnerCreate(BaseModel):
    """Partner creation model."""
    name: str
    description: Optional[str] = None
    partner_type: str
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: str
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    business_hours: Optional[dict] = None
    price_range: Optional[str] = None
    commission_rate: float = 0.10


class PartnerResponse(BaseModel):
    """Partner response model."""
    id: str
    name: str
    description: Optional[str]
    partner_type: str
    category: Optional[str]
    city: str
    region: Optional[str]
    status: str
    commission_rate: float
    discount_code: Optional[str]
    total_bookings: int
    average_rating: Optional[float]
    
    class Config:
        from_attributes = True


class HostPartnerCreate(BaseModel):
    """Host-partner relationship creation model."""
    partner_id: str
    priority: int = 0
    commission_rate: Optional[float] = None
    custom_discount_code: Optional[str] = None
    custom_discount_percentage: Optional[float] = None
    partnership_notes: Optional[str] = None


@router.post("/", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    partner_data: PartnerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new business partner.
    
    Args:
        partner_data: Partner creation data
        db: Database session
        
    Returns:
        Created partner
    """
    try:
        service = PartnerService(db)
        partner = await service.create_partner(partner_data.model_dump(exclude_unset=True))
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create partner"
            )
        
        return PartnerResponse(
            id=str(partner.id),
            name=partner.name,
            description=partner.description,
            partner_type=partner.partner_type,
            category=partner.category,
            city=partner.city,
            region=partner.region,
            status=partner.status,
            commission_rate=partner.commission_rate,
            discount_code=partner.discount_code,
            total_bookings=partner.total_bookings,
            average_rating=partner.average_rating
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating partner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create partner: {str(e)}"
        )


@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a partner by ID (public). Response omits contact PII; use host-scoped cleaning
    or GET /partners/hosts/{your_host_id}/partners for actionable contact when linked.
    """
    try:
        service = PartnerService(db)
        partner = await service.get_partner(uuid.UUID(partner_id))
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        return PartnerResponse(
            id=str(partner.id),
            name=partner.name,
            description=partner.description,
            partner_type=partner.partner_type,
            category=partner.category,
            city=partner.city,
            region=partner.region,
            status=partner.status,
            commission_rate=partner.commission_rate,
            discount_code=partner.discount_code,
            total_bookings=partner.total_bookings,
            average_rating=partner.average_rating
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting partner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get partner: {str(e)}"
        )


@router.get("/", response_model=List[PartnerResponse])
async def list_partners(
    city: Optional[str] = Query(None),
    partner_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List partners with optional filters (public).

    Response omits contact PII (email, phone, website). Authenticated hosts should use
    GET /cleaning/providers or GET /partners/hosts/{own_host_id}/partners for full contact.
    """
    try:
        service = PartnerService(db)
        partners = await service.list_partners(
            city=city,
            partner_type=partner_type,
            status=status,
            limit=limit
        )
        
        return [
            PartnerResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                partner_type=p.partner_type,
                category=p.category,
                city=p.city,
                region=p.region,
                status=p.status,
                commission_rate=p.commission_rate,
                discount_code=p.discount_code,
                total_bookings=p.total_bookings,
                average_rating=p.average_rating
            )
            for p in partners
        ]
        
    except Exception as e:
        logger.error(f"Error listing partners: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list partners: {str(e)}"
        )


@router.post("/hosts/{host_id}/partners", status_code=status.HTTP_201_CREATED)
async def create_host_partner_relationship(
    host_id: str,
    relationship_data: HostPartnerCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a relationship between a host and partner.
    Requires session; host_id must match the authenticated host.
    """
    try:
        _require_self_host(host_id, current_host)
        service = PartnerService(db)
        relationship = await service.create_host_partner_relationship(
            host_id=uuid.UUID(host_id),
            partner_id=uuid.UUID(relationship_data.partner_id),
            relationship_data=relationship_data.model_dump(exclude={"partner_id"}, exclude_unset=True),
        )
        
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create host-partner relationship"
            )
        
        return {
            "success": True,
            "relationship_id": str(relationship.id),
            "host_id": host_id,
            "partner_id": relationship_data.partner_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating host-partner relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}"
        )


@router.get("/hosts/{host_id}/partners")
async def get_host_partners(
    host_id: str,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all partners for a host with contact fields (authenticated; host_id must be self).
    """
    try:
        _require_self_host(host_id, current_host)
        service = PartnerService(db)
        partners = await service.get_host_partners(uuid.UUID(host_id))
        out = []
        for p in partners:
            rel = p.get("relationship")
            out.append(
                {
                    "partner": _partner_contact_payload(p["partner"]),
                    "relationship": {
                        "priority": p["priority"],
                        "commission_rate": p["commission_rate"],
                        "status": p["status"],
                        "partnership_notes": rel.partnership_notes if rel else None,
                    },
                }
            )
        return out

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting host partners: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get host partners: {str(e)}"
        )


@router.put("/{partner_id}")
async def update_partner(
    partner_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a partner.
    
    Args:
        partner_id: Partner UUID
        update_data: Fields to update
        db: Database session
        
    Returns:
        Updated partner
    """
    try:
        service = PartnerService(db)
        partner = await service.update_partner(
            partner_id=uuid.UUID(partner_id),
            update_data=update_data
        )
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        return {"success": True, "partner_id": partner_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating partner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update partner: {str(e)}"
        )

