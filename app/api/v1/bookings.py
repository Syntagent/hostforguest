"""
Booking API endpoints for commission-based bookings.

Provides REST API for booking management, commission tracking,
and booking analytics with multi-currency support.
"""

import logging
from typing import List, Optional
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.booking_api import (
    BookingAnalyticsResponse,
    BookingMutationResponse,
    BookingResponse,
    BookingSummaryRow,
    HostBookingsListResponse,
    PartnerPayoutResponse,
)
from app.core.database import get_db
from app.api.v1.hosts import get_current_host
from app.models.host import Host
from app.services.booking_service import BookingService
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.partner_service import PartnerService
from app.models.partner import BookingStatus, PartnerBooking
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class CreateBookingRequest(BaseModel):
    """Request for creating a booking."""
    guest_group_id: str
    partner_id: str
    attraction_id: Optional[str] = None
    host_id: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str = "EUR"
    booking_reference: Optional[str] = None
    service_date: Optional[datetime] = None
    details: Optional[dict] = None
    notes: Optional[str] = None


@router.post("/", response_model=BookingResponse)
async def create_booking(
    request: CreateBookingRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new booking with automatic commission calculation.
    
    Args:
        request: Booking creation request
        db: Database session
        
    Returns:
        Created booking
    """
    try:
        guest_service = GuestGroupService(db)
        group = await guest_service.get_by_id(uuid.UUID(request.guest_group_id))
        if not group or not host_owns_guest_group(group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found",
            )
        if request.host_id and str(current_host.id) != request.host_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        partner_svc = PartnerService(db)
        if not await partner_svc.host_has_partner_link(
            current_host.id, uuid.UUID(request.partner_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found",
            )

        booking_service = BookingService(db)
        
        booking_data = {
            "host_id": current_host.id,
            "amount": request.amount,
            "currency": request.currency,
            "booking_reference": request.booking_reference,
            "service_date": request.service_date,
            "details": request.details or {},
            "notes": request.notes
        }
        
        booking = await booking_service.create_booking(
            guest_group_id=uuid.UUID(request.guest_group_id),
            partner_id=uuid.UUID(request.partner_id),
            attraction_id=uuid.UUID(request.attraction_id) if request.attraction_id else None,
            booking_data=booking_data
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking"
            )
        
        return BookingResponse(
            id=str(booking.id),
            guest_group_id=str(booking.guest_group_id),
            partner_id=str(booking.partner_id),
            booking_amount=booking.booking_amount,
            currency=booking.currency,
            commission_rate=booking.commission_rate,
            commission_amount=booking.commission_amount,
            status=booking.status,
            booking_date=booking.booking_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create booking: {str(e)}"
        )


async def _booking_for_host(
    db: AsyncSession, booking_id: str, current_host: Host
) -> PartnerBooking:
    stmt = select(PartnerBooking).where(PartnerBooking.id == uuid.UUID(booking_id))
    result = await db.execute(stmt)
    booking = result.scalar_one_or_none()
    if not booking or booking.host_id != current_host.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    return booking


@router.post("/{booking_id}/confirm", response_model=BookingMutationResponse)
async def confirm_booking(
    booking_id: str,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm a booking.
    
    Args:
        booking_id: Booking ID
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await _booking_for_host(db, booking_id, current_host)
        booking_service = BookingService(db)

        success = await booking_service.confirm_booking(uuid.UUID(booking_id))
        
        if success:
            return {"success": True, "message": "Booking confirmed"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to confirm booking"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm booking: {str(e)}"
        )


@router.post("/{booking_id}/cancel", response_model=BookingMutationResponse)
async def cancel_booking(
    booking_id: str,
    cancellation_reason: Optional[str] = None,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a booking.
    
    Args:
        booking_id: Booking ID
        cancellation_reason: Optional cancellation reason
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await _booking_for_host(db, booking_id, current_host)
        booking_service = BookingService(db)

        success = await booking_service.cancel_booking(
            uuid.UUID(booking_id),
            cancellation_reason
        )
        
        if success:
            return {"success": True, "message": "Booking cancelled"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel booking"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel booking: {str(e)}"
        )


@router.get("/host/{host_id}", response_model=HostBookingsListResponse)
async def get_host_bookings(
    host_id: str,
    booking_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all bookings for a host.
    
    Args:
        host_id: Host ID
        status: Optional status filter
        limit: Maximum number of bookings
        db: Database session
        
    Returns:
        List of bookings
    """
    try:
        if str(current_host.id) != host_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        booking_service = BookingService(db)

        booking_status_enum = BookingStatus(booking_status) if booking_status else None

        bookings = await booking_service.get_bookings_for_host(
            uuid.UUID(host_id),
            booking_status_enum,
            limit
        )
        
        rows = [
            BookingSummaryRow(
                id=str(b.id),
                guest_group_id=str(b.guest_group_id),
                partner_id=str(b.partner_id),
                booking_amount=b.booking_amount,
                currency=b.currency,
                commission_amount=b.commission_amount,
                status=b.status,
                booking_date=b.booking_date.isoformat() if b.booking_date else None,
            )
            for b in bookings
        ]
        return HostBookingsListResponse(bookings=rows, count=len(rows))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting host bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bookings: {str(e)}"
        )


@router.get("/partner/{partner_id}/payout", response_model=PartnerPayoutResponse)
async def get_partner_payout(
    partner_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate commission payout for a partner.
    
    Args:
        partner_id: Partner ID
        start_date: Optional start date filter
        end_date: Optional end date filter
        db: Database session
        
    Returns:
        Payout calculation
    """
    try:
        partner_uuid = uuid.UUID(partner_id)
        partner_svc = PartnerService(db)
        if not await partner_svc.host_has_partner_link(current_host.id, partner_uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found",
            )

        booking_service = BookingService(db)
        
        payout = await booking_service.calculate_commission_payout(
            partner_uuid,
            start_date,
            end_date,
            host_id=current_host.id,
        )
        
        return PartnerPayoutResponse.model_validate(payout)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating payout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate payout: {str(e)}"
        )


@router.get("/analytics", response_model=BookingAnalyticsResponse)
async def get_booking_analytics(
    host_id: Optional[str] = Query(None),
    partner_id: Optional[str] = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get booking analytics and metrics.
    
    Args:
        host_id: Optional host ID filter
        partner_id: Optional partner ID filter
        period_days: Number of days to analyze
        db: Database session
        
    Returns:
        Analytics data
    """
    try:
        if host_id and str(current_host.id) != host_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        booking_service = BookingService(db)
        
        analytics = await booking_service.get_booking_analytics(
            current_host.id,
            uuid.UUID(partner_id) if partner_id else None,
            period_days
        )
        
        return BookingAnalyticsResponse.model_validate(analytics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting booking analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

