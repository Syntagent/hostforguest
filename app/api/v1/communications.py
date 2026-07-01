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

from app.models.communications_api import (
    CommunicationSuccessResponse,
    WelcomeKitGenerateResponse,
)
from app.core.database import get_db
from app.core.auth import require_host_session
from app.services.communication_service import CommunicationService
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.models.host import Host
from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)
router = APIRouter()


async def _require_owned_guest_group(
    guest_group_service: GuestGroupService,
    guest_group_id: str,
    current_host: Host,
) -> GuestGroup:
    """Return guest group only when it belongs to the authenticated host."""
    guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(guest_group_id))
    if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest group not found",
        )
    return guest_group


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
    """Request for sending SMS to a guest group's lead phone."""
    guest_group_id: str
    message: str
    language: str = "en"


@router.post("/pre-arrival-email", response_model=CommunicationSuccessResponse)
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
        guest_group_service = GuestGroupService(db)
        guest_group = await _require_owned_guest_group(
            guest_group_service, request.guest_group_id, current_host
        )
        success = await communication_service.send_pre_arrival_email(current_host, guest_group)
        
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


@router.post("/welcome-kit/generate", response_model=WelcomeKitGenerateResponse)
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
        guest_group_service = GuestGroupService(db)
        guest_group = await _require_owned_guest_group(
            guest_group_service, request.guest_group_id, current_host
        )
        welcome_kit = await communication_service.generate_welcome_kit(current_host, guest_group)
        
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


@router.post("/welcome-kit/send", response_model=CommunicationSuccessResponse)
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
        guest_group_service = GuestGroupService(db)
        guest_group = await _require_owned_guest_group(
            guest_group_service, request.guest_group_id, current_host
        )
        success = await communication_service.send_welcome_kit(
            current_host, guest_group, request.delivery_method
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


@router.post("/follow-up", response_model=CommunicationSuccessResponse)
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
        guest_group_service = GuestGroupService(db)
        guest_group = await _require_owned_guest_group(
            guest_group_service, request.guest_group_id, current_host
        )
        success = await communication_service.send_post_stay_follow_up(current_host, guest_group)
        
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


@router.post("/sms", response_model=CommunicationSuccessResponse)
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
        guest_group_service = GuestGroupService(db)
        guest_group = await _require_owned_guest_group(
            guest_group_service, request.guest_group_id, current_host
        )
        if not guest_group.lead_guest_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest group has no lead guest phone number",
            )

        success = await communication_service.send_sms(
            phone_number=guest_group.lead_guest_phone,
            message=request.message,
            language=request.language,
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

