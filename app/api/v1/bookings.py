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

from app.core.database import get_db
from app.services.booking_service import BookingService
from app.models.partner import BookingStatus

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


class BookingResponse(BaseModel):
    """Booking response model."""
    id: str
    guest_group_id: str
    partner_id: str
    booking_amount: float
    currency: str
    commission_rate: float
    commission_amount: float
    status: str
    booking_date: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=BookingResponse)
async def create_booking(
    request: CreateBookingRequest,
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
        booking_service = BookingService(db)
        
        booking_data = {
            "host_id": uuid.UUID(request.host_id) if request.host_id else None,
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


@router.post("/{booking_id}/confirm")
async def confirm_booking(
    booking_id: str,
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


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    cancellation_reason: Optional[str] = None,
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


@router.get("/host/{host_id}")
async def get_host_bookings(
    host_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
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
        booking_service = BookingService(db)
        
        booking_status = BookingStatus(status) if status else None
        
        bookings = await booking_service.get_bookings_for_host(
            uuid.UUID(host_id),
            booking_status,
            limit
        )
        
        return {
            "bookings": [
                {
                    "id": str(b.id),
                    "guest_group_id": str(b.guest_group_id),
                    "partner_id": str(b.partner_id),
                    "booking_amount": b.booking_amount,
                    "currency": b.currency,
                    "commission_amount": b.commission_amount,
                    "status": b.status,
                    "booking_date": b.booking_date.isoformat() if b.booking_date else None
                }
                for b in bookings
            ],
            "count": len(bookings)
        }
        
    except Exception as e:
        logger.error(f"Error getting host bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bookings: {str(e)}"
        )


@router.get("/partner/{partner_id}/payout")
async def get_partner_payout(
    partner_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
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
        booking_service = BookingService(db)
        
        payout = await booking_service.calculate_commission_payout(
            uuid.UUID(partner_id),
            start_date,
            end_date
        )
        
        return payout
        
    except Exception as e:
        logger.error(f"Error calculating payout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate payout: {str(e)}"
        )


@router.get("/analytics")
async def get_booking_analytics(
    host_id: Optional[str] = Query(None),
    partner_id: Optional[str] = Query(None),
    period_days: int = Query(30, ge=1, le=365),
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
        booking_service = BookingService(db)
        
        analytics = await booking_service.get_booking_analytics(
            uuid.UUID(host_id) if host_id else None,
            uuid.UUID(partner_id) if partner_id else None,
            period_days
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting booking analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

