"""
Communication API endpoints for automated guest communications.

Provides REST API for sending pre-arrival emails, welcome kits,
SMS/WhatsApp messages, and post-stay follow-ups.
"""

import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import require_host_session
from app.services.communication_service import CommunicationService
from app.services.host_service import HostService
from app.services.guest_group_service import GuestGroupService
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


# Request Models
class SendPreArrivalEmailRequest(BaseModel):
    """Request for sending pre-arrival email."""
    guest_group_id: str


class GenerateWelcomeKitRequest(BaseModel):
    """Request for generating welcome kit."""
    guest_group_id: str


class SendWelcomeKitRequest(BaseModel):
    """Request for sending welcome kit."""
    guest_group_id: str
    delivery_method: str = "email"  # email, sms, whatsapp


class SendFollowUpRequest(BaseModel):
    """Request for sending post-stay follow-up."""
    guest_group_id: str


class SendSMSRequest(BaseModel):
    """Request for sending SMS."""
    phone_number: str
    message: str
    language: str = "en"


@router.post("/pre-arrival-email")
async def send_pre_arrival_email(
    request: SendPreArrivalEmailRequest,
    current_host: Host = Depends(require_host_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Send pre-arrival email to guests.
    
    Args:
        request: Pre-arrival email request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        communication_service = CommunicationService(db)
        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        
        # Get guest group
        guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(request.guest_group_id))
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Get host
        host = await host_service.get_host_by_id(guest_group.host_id)
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found"
            )
        
        # Send email
        success = await communication_service.send_pre_arrival_email(host, guest_group)
        
        if success:
            return {"success": True, "message": "Pre-arrival email sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send pre-arrival email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending pre-arrival email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.post("/welcome-kit/generate")
async def generate_welcome_kit(
    request: GenerateWelcomeKitRequest,
    current_host: Host = Depends(require_host_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate personalized welcome kit.
    
    Args:
        request: Welcome kit generation request
        db: Database session
        
    Returns:
        Welcome kit data
    """
    try:
        communication_service = CommunicationService(db)
        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        
        # Get guest group
        guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(request.guest_group_id))
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Get host
        host = await host_service.get_host_by_id(guest_group.host_id)
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found"
            )
        
        # Generate welcome kit
        welcome_kit = await communication_service.generate_welcome_kit(host, guest_group)
        
        if welcome_kit:
            return {"success": True, "welcome_kit": welcome_kit}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate welcome kit"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome kit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate welcome kit: {str(e)}"
        )


@router.post("/welcome-kit/send")
async def send_welcome_kit(
    request: SendWelcomeKitRequest,
    current_host: Host = Depends(require_host_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Send welcome kit to guests.
    
    Args:
        request: Welcome kit send request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        communication_service = CommunicationService(db)
        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        
        # Get guest group
        guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(request.guest_group_id))
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Get host
        host = await host_service.get_host_by_id(guest_group.host_id)
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found"
            )
        
        # Send welcome kit
        success = await communication_service.send_welcome_kit(
            host, guest_group, request.delivery_method
        )
        
        if success:
            return {
                "success": True,
                "message": f"Welcome kit sent via {request.delivery_method}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send welcome kit"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending welcome kit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send welcome kit: {str(e)}"
        )


@router.post("/follow-up")
async def send_follow_up(
    request: SendFollowUpRequest,
    current_host: Host = Depends(require_host_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Send post-stay follow-up email.
    
    Args:
        request: Follow-up request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        communication_service = CommunicationService(db)
        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        
        # Get guest group
        guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(request.guest_group_id))
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Get host
        host = await host_service.get_host_by_id(guest_group.host_id)
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found"
            )
        
        # Send follow-up
        success = await communication_service.send_post_stay_follow_up(host, guest_group)
        
        if success:
            return {"success": True, "message": "Follow-up email sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow-up email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending follow-up: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send follow-up: {str(e)}"
        )


@router.post("/sms")
async def send_sms(
    request: SendSMSRequest,
    current_host: Host = Depends(require_host_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Send SMS message.
    
    Args:
        request: SMS request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        communication_service = CommunicationService(db)
        
        success = await communication_service.send_sms(
            phone_number=request.phone_number,
            message=request.message,
            language=request.language
        )
        
        if success:
            return {"success": True, "message": "SMS sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send SMS"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SMS: {str(e)}"
        )

