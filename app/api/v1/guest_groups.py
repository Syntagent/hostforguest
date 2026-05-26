"""
Guest group management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for guest group creation, access code management,
preference collection, and CRUD operations.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.host_offerings_for_guest import build_host_offerings_payload
from app.services.host_service import HostService
from app.models.guest_group import (
    GuestGroupCreate,
    GuestGroupUpdate,
    GuestGroupResponse,
    HostGuestExperienceResponse,
    AccessCodeCreate,
    AccessCodeResponse,
    GuestPreferenceCreate,
    GuestPreferenceUpdate,
    GuestPreferenceResponse,
    GuestEVisitorDataCreate,
    GuestEVisitorDataUpdate,
    GuestEVisitorDataResponse,
    AccessCodeValidation,
    GuestGroup
)
from app.models.host import Host, HostProfile

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_current_host(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Host:
    """
    Get current authenticated host from session token.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Host: Current authenticated host
        
    Raises:
        HTTPException: If not authenticated
    """
    # Get session token from header
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )
    
    # Validate session and get host
    host_service = HostService(db)
    host = await host_service.get_current_host_from_session(session_token)
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return host


async def validate_access_code(
    access_code: str,
    db: AsyncSession = Depends(get_db)
) -> GuestGroup:
    """
    Validate guest group access code.
    
    Args:
        access_code: Guest group access code
        db: Database session
        
    Returns:
        GuestGroup: Validated guest group
        
    Raises:
        HTTPException: If access code is invalid or expired
    """
    guest_service = GuestGroupService(db)
    guest_group = await guest_service.validate_access_code(access_code)
    if not guest_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired access code"
        )
    return guest_group


# Host endpoints for managing guest groups
@router.post(
    "",
    response_model=GuestGroupResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post("/", response_model=GuestGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_group(
    guest_group_data: GuestGroupCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new guest group for the current host.
    
    Args:
        guest_group_data: Guest group creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GuestGroupResponse: Created guest group with access code
    """
    try:
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.create_guest_group(
            host_id=current_host.id,
            group_data=guest_group_data
        )

        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create guest group",
            )

        logger.info(f"Guest group created successfully: {guest_group.id} for host {current_host.id}")
        return guest_group

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create guest group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create guest group"
        )


@router.get("/", response_model=List[GuestGroupResponse])
@router.get("/host", response_model=List[GuestGroupResponse])
async def get_host_guest_groups(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None
):
    """
    Get all guest groups for the current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by guest group status
        
    Returns:
        List[GuestGroupResponse]: List of host's guest groups
    """
    try:
        guest_service = GuestGroupService(db)
        guest_groups = await guest_service.get_host_guest_groups(
            host_id=current_host.id,
            include_completed=True  # Include all groups for now
        )
        
        logger.info(f"Retrieved {len(guest_groups)} guest groups for host {current_host.id}")
        return guest_groups
        
    except Exception as e:
        logger.error(f"Failed to retrieve guest groups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve guest groups"
        )


@router.get("/{guest_group_id}", response_model=GuestGroupResponse)
async def get_guest_group(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific guest group by ID (host must own the group).
    
    Args:
        guest_group_id: Guest group ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GuestGroupResponse: Guest group details
    """
    try:
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Verify host owns this guest group
        if not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group"
            )

        logger.info(f"Retrieved guest group {guest_group_id} for host {current_host.id}")
        prof = await guest_service._profile_for_host_id(current_host.id)
        return await guest_service.guest_group_to_response(guest_group, profile=prof)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve guest group {guest_group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve guest group"
        )


@router.get("/{guest_group_id}/guest-experience", response_model=HostGuestExperienceResponse)
async def get_host_guest_experience(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    Return guest group details and the active access code so the host can open /guest/{code}.

    Does not consume access-code usage limits (read-only lookup).
    """
    try:
        guest_service = GuestGroupService(db)
        payload = await guest_service.get_host_guest_experience(
            host_id=current_host.id,
            guest_group_id=guest_group_id,
        )
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found",
            )
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed guest experience lookup for group {guest_group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load guest experience",
        )


@router.put("/{guest_group_id}", response_model=GuestGroupResponse)
async def update_guest_group(
    guest_group_id: uuid.UUID,
    guest_group_data: GuestGroupUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a guest group (host must own the group).
    
    Args:
        guest_group_id: Guest group ID
        guest_group_data: Updated guest group data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GuestGroupResponse: Updated guest group
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group exists and host owns it
        existing_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not existing_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        if not host_owns_guest_group(existing_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group"
            )
        
        updated_group = await guest_service.update_guest_group(
            group_id=guest_group_id,
            group_data=guest_group_data,
        )
        
        logger.info(f"Updated guest group {guest_group_id} for host {current_host.id}")
        return updated_group
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update guest group {guest_group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update guest group"
        )


@router.delete("/{guest_group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_group(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a guest group (host must own the group).
    
    Args:
        guest_group_id: Guest group ID
        current_host: Current authenticated host
        db: Database session
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group exists and host owns it
        existing_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not existing_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        if not host_owns_guest_group(existing_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group"
            )
        
        await guest_service.delete_guest_group(guest_group_id)
        
        logger.info(f"Deleted guest group {guest_group_id} for host {current_host.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete guest group {guest_group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete guest group"
        )


# Access code management endpoints
@router.post("/{guest_group_id}/regenerate-code", response_model=AccessCodeResponse)
async def regenerate_access_code(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate access code for a guest group.
    
    Args:
        guest_group_id: Guest group ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        AccessCodeResponse: New access code details
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group exists and host owns it
        existing_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not existing_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        if not host_owns_guest_group(existing_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group"
            )
        
        new_code = await guest_service.regenerate_access_code(guest_group_id)
        if not new_code:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate access code",
            )

        logger.info(f"Regenerated access code for guest group {guest_group_id}")
        return new_code

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to regenerate access code for guest group %s",
            guest_group_id,
        )
        detail = str(e) if settings.debug else "Failed to regenerate access code"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


# Guest endpoints (using access code authentication)
@router.post("/access/validate", response_model=GuestGroupResponse)
async def validate_guest_access(
    validation_data: AccessCodeValidation,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate guest access code and return guest group details.
    
    Args:
        validation_data: Access code validation data
        db: Database session
        
    Returns:
        GuestGroupResponse: Guest group details if valid
    """
    try:
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.validate_access_code(validation_data.access_code)

        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )

        logger.info(f"Access code validated for guest group {guest_group.id}")
        return await guest_service.guest_group_to_response(guest_group)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate access code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate access code"
        )


@router.get("/access/{access_code}", response_model=GuestGroupResponse)
async def get_guest_group_by_code(
    access_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get guest group details using access code.
    
    Args:
        access_code: Guest group access code
        db: Database session
        
    Returns:
        GuestGroupResponse: Guest group details
    """
    guest_group = await validate_access_code(access_code, db)
    guest_service = GuestGroupService(db)
    return await guest_service.guest_group_to_response(guest_group)


@router.get("/access/{access_code}/host-offerings")
async def get_host_offerings_by_guest_access_code(
    access_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Host profile and tips for guests using a **guest-group** access code.

    Resolves the host from the validated group (unlike /onboarding/guest-access which uses Host.guest_access_code).
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        host_result = await db.execute(select(Host).where(Host.id == guest_group.host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found for this guest group",
            )
        profile_result = await db.execute(select(HostProfile).where(HostProfile.host_id == host.id))
        profile = profile_result.scalar_one_or_none()
        host_offerings = build_host_offerings_payload(host, profile, access_code)
        return {
            "success": True,
            "host_offerings": host_offerings,
            "access_code": access_code,
            "valid_access": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load host offerings for guest access: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load host information",
        )


@router.post("/access/{access_code}/host-message", response_model=Dict[str, Any])
async def send_message_to_host_by_guest_access_code(
    access_code: str,
    message_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Guest message to host, authenticated by guest-group access code."""
    try:
        guest_group = await validate_access_code(access_code, db)
        host_result = await db.execute(select(Host).where(Host.id == guest_group.host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found",
            )

        message_text = message_data.get("message", "")
        message_type = message_data.get("type", "general")
        guest_name = message_data.get("guest_name", "Guest")

        if message_type == "question" or "recommend" in (message_text or "").lower():
            specialties = host.local_specialties or []
            top_specialties = ", ".join(specialties[:3]) if specialties else "local experiences"
            ai_response = (
                f"Hi {guest_name}! As {host.first_name or 'your host'}'s assistant, I'd be happy to help. "
                f"Based on your question about {host.city or 'the area'}, I recommend exploring our local specialties: "
                f"{top_specialties}. Would you like specific recommendations for activities, restaurants, or hidden gems?"
            )
            response: Dict[str, Any] = {
                "success": True,
                "response_type": "ai_assistant",
                "message": ai_response,
                "suggestions": [
                    "Tell me about local restaurants",
                    "What are the best beaches nearby?",
                    "Recommend activities for families",
                    "Show me hidden local gems",
                ],
                "can_contact_host": True,
                "response_time": "Immediate (AI) • Host usually responds within 2 hours",
            }
        else:
            response = {
                "success": True,
                "response_type": "queued_for_host",
                "message": (
                    f"Thanks {guest_name}! Your message has been sent to {host.first_name or 'your host'}. "
                    f"They typically respond within 2 hours. In the meantime, feel free to browse Discover and Plan."
                ),
                "estimated_response_time": "Within 2 hours",
                "ai_available": True,
            }

        logger.info("Guest message via group access %s: %s...", access_code, (message_text or "")[:50])
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Guest host-message error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        )


# Guest preference management
@router.post("/access/{access_code}/preferences", response_model=GuestPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def add_guest_preference(
    access_code: str,
    preference_data: GuestPreferenceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a guest preference to the group.
    
    Args:
        access_code: Guest group access code
        preference_data: Guest preference data
        db: Database session
        
    Returns:
        GuestPreferenceResponse: Created guest preference
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        preference = await guest_service.add_guest_preference(
            guest_group_id=guest_group.id,
            preference_data=preference_data
        )
        
        logger.info(f"Added guest preference for group {guest_group.id}")
        return preference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add guest preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add guest preference"
        )


@router.get("/access/{access_code}/preferences", response_model=List[GuestPreferenceResponse])
async def get_guest_preferences(
    access_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all guest preferences for the group.
    
    Args:
        access_code: Guest group access code
        db: Database session
        
    Returns:
        List[GuestPreferenceResponse]: List of guest preferences
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        preferences = await guest_service.get_guest_preferences(guest_group.id)
        
        logger.info(f"Retrieved {len(preferences)} preferences for group {guest_group.id}")
        return preferences
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve guest preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve guest preferences"
        )


@router.put("/access/{access_code}/preferences/{preference_id}", response_model=GuestPreferenceResponse)
async def update_guest_preference(
    access_code: str,
    preference_id: uuid.UUID,
    preference_data: GuestPreferenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a guest preference.
    
    Args:
        access_code: Guest group access code
        preference_id: Guest preference ID
        preference_data: Updated preference data
        db: Database session
        
    Returns:
        GuestPreferenceResponse: Updated guest preference
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        # Verify preference belongs to this guest group
        existing_preference = await guest_service.get_guest_preference_by_id(preference_id)
        if not existing_preference or existing_preference.guest_group_id != guest_group.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest preference not found"
            )
        
        updated_preference = await guest_service.update_guest_preference(
            preference_id=preference_id,
            preference_data=preference_data
        )
        
        logger.info(f"Updated guest preference {preference_id} for group {guest_group.id}")
        return updated_preference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update guest preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update guest preference"
        )


@router.delete("/access/{access_code}/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_preference(
    access_code: str,
    preference_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a guest preference.
    
    Args:
        access_code: Guest group access code
        preference_id: Guest preference ID
        db: Database session
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        # Verify preference belongs to this guest group
        existing_preference = await guest_service.get_guest_preference_by_id(preference_id)
        if not existing_preference or existing_preference.guest_group_id != guest_group.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest preference not found"
            )
        
        await guest_service.delete_guest_preference(preference_id)
        
        logger.info(f"Deleted guest preference {preference_id} for group {guest_group.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete guest preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete guest preference"
        )


# E-visitor Data Endpoints
@router.post("/{guest_group_id}/evisitor-data", response_model=GuestEVisitorDataResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_evisitor_data(
    guest_group_id: uuid.UUID,
    evisitor_data: GuestEVisitorDataCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create e-visitor data for a guest in a group.
    
    Args:
        guest_group_id: Guest group ID
        evisitor_data: E-visitor data creation model
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GuestEVisitorDataResponse: Created e-visitor data
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group belongs to current host
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        created_evisitor = await guest_service.create_guest_evisitor_data(
            guest_group_id=guest_group_id,
            evisitor_data=evisitor_data
        )
        
        if not created_evisitor:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create e-visitor data"
            )
        
        logger.info(f"E-visitor data created for guest group {guest_group_id}")
        return created_evisitor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create e-visitor data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create e-visitor data"
        )


@router.get("/{guest_group_id}/evisitor-data", response_model=List[GuestEVisitorDataResponse])
async def get_guest_evisitor_data(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all e-visitor data for a guest group.
    
    Args:
        guest_group_id: Guest group ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        List[GuestEVisitorDataResponse]: List of e-visitor data
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group belongs to current host
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        evisitor_data = await guest_service.get_guest_evisitor_data(guest_group_id)
        
        logger.info(f"Retrieved {len(evisitor_data)} e-visitor records for group {guest_group_id}")
        return evisitor_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve e-visitor data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve e-visitor data"
        )


@router.put("/{guest_group_id}/evisitor-data/{evisitor_id}", response_model=GuestEVisitorDataResponse)
async def update_guest_evisitor_data(
    guest_group_id: uuid.UUID,
    evisitor_id: uuid.UUID,
    evisitor_data: GuestEVisitorDataUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update e-visitor data for a guest.
    
    Args:
        guest_group_id: Guest group ID
        evisitor_id: E-visitor data ID
        evisitor_data: Updated e-visitor data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GuestEVisitorDataResponse: Updated e-visitor data
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group belongs to current host
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        updated_evisitor = await guest_service.update_guest_evisitor_data(
            evisitor_id=evisitor_id,
            update_data=evisitor_data
        )
        
        if not updated_evisitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="E-visitor data not found"
            )
        
        logger.info(f"E-visitor data {evisitor_id} updated for group {guest_group_id}")
        return updated_evisitor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update e-visitor data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update e-visitor data"
        )


@router.post("/{guest_group_id}/evisitor-data/{evisitor_id}/register", status_code=status.HTTP_200_OK)
async def mark_evisitor_registered(
    guest_group_id: uuid.UUID,
    evisitor_id: uuid.UUID,
    confirmation_number: str,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark e-visitor data as registered with Croatian authorities.
    
    Args:
        guest_group_id: Guest group ID
        evisitor_id: E-visitor data ID
        confirmation_number: E-visitor confirmation number
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        dict: Success message
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group belongs to current host
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        success = await guest_service.mark_evisitor_registered(
            evisitor_id=evisitor_id,
            confirmation_number=confirmation_number
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark e-visitor as registered"
            )
        
        logger.info(f"E-visitor data {evisitor_id} marked as registered for group {guest_group_id}")
        return {"message": "E-visitor data marked as registered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark e-visitor as registered: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark e-visitor as registered"
        )


@router.delete("/{guest_group_id}/evisitor-data/{evisitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_evisitor_data(
    guest_group_id: uuid.UUID,
    evisitor_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete e-visitor data for a guest.
    
    Args:
        guest_group_id: Guest group ID
        evisitor_id: E-visitor data ID
        current_host: Current authenticated host
        db: Database session
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Verify guest group belongs to current host
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        success = await guest_service.delete_guest_evisitor_data(evisitor_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="E-visitor data not found"
            )
        
        logger.info(f"E-visitor data {evisitor_id} deleted for group {guest_group_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete e-visitor data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete e-visitor data"
        ) 