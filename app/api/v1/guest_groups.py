"""
Guest group management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for guest group creation, access code management,
preference collection, and CRUD operations.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import get_current_host
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.host_offerings_for_guest import (
    attach_host_broadcast_messages,
    build_host_offerings_payload,
    scrub_contact_from_text,
)
from app.services.host_service import HostService
from app.services.event_recommendation_service import (
    EventRecommendationService,
    sanitize_event_recommendations_for_guest,
)
from app.services.guest_saved_events_service import GuestSavedEventsService
from app.models.guest_group import (
    GuestGroupCreate,
    GuestGroupUpdate,
    GuestGroupResponse,
    GuestGroupGuestResponse,
    HostGuestExperienceResponse,
    AccessCodeCreate,
    AccessCodeResponse,
    GuestPreferenceCreate,
    GuestPreferenceUpdate,
    GuestPreferenceResponse,
    GuestPreferenceGuestResponse,
    GuestEVisitorDataCreate,
    GuestEVisitorDataUpdate,
    GuestEVisitorDataResponse,
    EVisitorRegisterRequest,
    AccessCodeValidation,
    GuestGroup,
    HostGroupBroadcastRecord,
    HostGroupBroadcastDelivery,
    HostGroupBroadcastResponse,
    HostSavedEventRecord,
    HostSavedEventsResponse,
    HostSavedEventItineraryActivityResponse,
    GuestSavedEventRecord,
    GuestSavedEventsResponse,
    GuestHostOfferingsApiResponse,
    GuestEventRecommendationsResponse,
    GuestConciergeMessageResponse,
)
from app.models.host import Host, HostProfile

logger = logging.getLogger(__name__)
router = APIRouter()


def _preference_for_guest(preference: GuestPreferenceResponse) -> GuestPreferenceGuestResponse:
    """Strip guest_group_id and scrub contact patterns from preference payloads."""
    from app.services.host_offerings_for_guest import scrub_contact_from_text, _scrub_safe_value

    data = preference.model_dump(exclude={"guest_group_id", "created_at", "updated_at"})
    for key in ("guest_name", "age_category", "mobility_notes"):
        if data.get(key):
            data[key] = scrub_contact_from_text(data[key])
    if data.get("language_preference"):
        original = str(data["language_preference"])
        scrubbed = scrub_contact_from_text(original)
        if (
            scrubbed != original
            and scrubbed
            and "[contact removed]" in scrubbed
        ) or len(scrubbed) > 10:
            data["language_preference"] = "en"
        else:
            data["language_preference"] = scrubbed
    for key in ("personal_interests", "dietary_needs", "cultural_interests", "food_interests"):
        if data.get(key):
            data[key] = _scrub_safe_value(data[key])
    return GuestPreferenceGuestResponse.model_validate(data)


class GuestAssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    guest_name: Optional[str] = None


class HostGroupBroadcastRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


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
@router.post("/access/validate", response_model=GuestGroupGuestResponse)
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
        GuestGroupGuestResponse: Guest group details if valid
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
        return await guest_service.guest_group_to_guest_response(guest_group)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate access code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate access code"
        )


@router.get("/access/{access_code}", response_model=GuestGroupGuestResponse)
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
        GuestGroupGuestResponse: Guest group details
    """
    guest_group = await validate_access_code(access_code, db)
    guest_service = GuestGroupService(db)
    return await guest_service.guest_group_to_guest_response(guest_group)


@router.get(
    "/access/{access_code}/host-offerings",
    response_model=GuestHostOfferingsApiResponse,
)
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
        prefs = guest_group.seasonal_preferences if isinstance(guest_group.seasonal_preferences, dict) else {}
        attach_host_broadcast_messages(host_offerings, prefs)
        return GuestHostOfferingsApiResponse(
            success=True,
            host_offerings=host_offerings,
            access_code=access_code,
            valid_access=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load host offerings for guest access: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load host information",
        )


@router.get(
    "/access/{access_code}/event-recommendations",
    response_model=GuestEventRecommendationsResponse,
)
async def get_guest_event_recommendations(
    access_code: str,
    limit: int = Query(15, ge=1, le=30),
    refresh: bool = Query(False, description="Bypass in-process recommendation cache"),
    db: AsyncSession = Depends(get_db),
):
    """Personalized local events for the guest stay window."""
    try:
        guest_group = await validate_access_code(access_code, db)
        host_result = await db.execute(select(Host).where(Host.id == guest_group.host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")
        profile_result = await db.execute(select(HostProfile).where(HostProfile.host_id == host.id))
        profile = profile_result.scalar_one_or_none()
        guest_service = GuestGroupService(db)
        preferences = await guest_service.get_guest_preferences(guest_group.id)
        svc = EventRecommendationService(db)
        payload = await svc.get_recommendations_for_access_code(
            guest_group, host, profile, preferences, limit=limit, refresh=refresh
        )
        return GuestEventRecommendationsResponse.model_validate(
            sanitize_event_recommendations_for_guest(payload)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("event-recommendations failed for %s: %s", access_code, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load event recommendations",
        )


def _guest_saved_events_response(data: Dict[str, Any]) -> GuestSavedEventsResponse:
    return GuestSavedEventsResponse(
        success=True,
        saved_event_ids=data["saved_event_ids"],
        saved_events=[
            GuestSavedEventRecord.model_validate(row) for row in data["saved_events"]
        ],
    )


@router.get(
    "/access/{access_code}/saved-events",
    response_model=GuestSavedEventsResponse,
)
async def get_guest_saved_events(
    access_code: str,
    db: AsyncSession = Depends(get_db),
):
    """List events the guest saved to their plan."""
    guest_group = await validate_access_code(access_code, db)
    svc = GuestSavedEventsService(db)
    return _guest_saved_events_response(await svc.list_for_group(guest_group.id))


@router.post(
    "/access/{access_code}/saved-events",
    response_model=GuestSavedEventsResponse,
)
async def save_guest_event(
    access_code: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Save an event idea to the guest plan."""
    guest_group = await validate_access_code(access_code, db)
    svc = GuestSavedEventsService(db)
    try:
        data = await svc.upsert(guest_group.id, body)
        return _guest_saved_events_response(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/access/{access_code}/saved-events/{event_id}",
    response_model=GuestSavedEventsResponse,
)
async def patch_guest_saved_event(
    access_code: str,
    event_id: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    guest_group = await validate_access_code(access_code, db)
    svc = GuestSavedEventsService(db)
    try:
        data = await svc.patch(guest_group.id, event_id, body)
        return _guest_saved_events_response(data)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved event not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/access/{access_code}/saved-events/{event_id}",
    response_model=GuestSavedEventsResponse,
)
async def delete_guest_saved_event(
    access_code: str,
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    guest_group = await validate_access_code(access_code, db)
    svc = GuestSavedEventsService(db)
    data = await svc.remove(guest_group.id, event_id)
    return _guest_saved_events_response(data)


@router.put(
    "/{guest_group_id}/saved-events/{event_id}",
    response_model=HostSavedEventsResponse,
)
async def host_update_saved_event(
    guest_group_id: uuid.UUID,
    event_id: str,
    body: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Host updates guest-saved event status (planned, notes, etc.)."""
    guest_service = GuestGroupService(db)
    group = await guest_service.get_guest_group_by_id(guest_group_id)
    if not group or not host_owns_guest_group(group, current_host.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest group not found")
    svc = GuestSavedEventsService(db)
    try:
        patch = dict(body)
        patch["host_action_at"] = patch.get("host_action_at") or datetime.utcnow().isoformat()
        data = await svc.patch(guest_group_id, event_id, patch, for_host=True)
        return HostSavedEventsResponse(
            success=True,
            saved_event_ids=data["saved_event_ids"],
            saved_events=[
                HostSavedEventRecord.model_validate(row) for row in data["saved_events"]
            ],
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved event not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{guest_group_id}/saved-events/{event_id}/itinerary-activity",
    response_model=HostSavedEventItineraryActivityResponse,
)
async def host_convert_saved_event_to_activity(
    guest_group_id: uuid.UUID,
    event_id: str,
    body: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Convert a guest-saved event into a scheduled itinerary activity."""
    guest_service = GuestGroupService(db)
    group = await guest_service.get_guest_group_by_id(guest_group_id)
    if not group or not host_owns_guest_group(group, current_host.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest group not found")
    svc = GuestSavedEventsService(db)
    try:
        data = await svc.convert_to_itinerary_activity(
            guest_group_id, event_id, current_host.id, body
        )
        return HostSavedEventItineraryActivityResponse(
            success=True,
            saved_event_ids=data["saved_event_ids"],
            saved_events=[
                HostSavedEventRecord.model_validate(row) for row in data["saved_events"]
            ],
            activity=data["activity"],
            already_added=bool(data.get("already_added")),
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved event not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _message_asks_about_events(text: str) -> bool:
    t = (text or "").lower()
    return any(
        w in t
        for w in (
            "event",
            "festival",
            "concert",
            "dogad",
            "week",
            "weekend",
            "happening",
            "marunada",
            "črešn",
            "cresnj",
        )
    )


@router.post("/{guest_group_id}/message", response_model=HostGroupBroadcastResponse)
async def send_host_message_to_group(
    guest_group_id: uuid.UUID,
    body: HostGroupBroadcastRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Host broadcasts a message to guests in a group (in-app + optional SMS)."""
    try:
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found",
            )

        record = await guest_service.append_host_broadcast_message(
            group_id=guest_group_id,
            message=body.message.strip(),
            host_name=f"{current_host.first_name or ''} {current_host.last_name or ''}".strip()
            or "Your host",
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save message",
            )

        delivery = HostGroupBroadcastDelivery(in_app=True, sms=False)
        if guest_group.lead_guest_phone:
            from app.services.communication_service import CommunicationService

            comm = CommunicationService(db)
            delivery = HostGroupBroadcastDelivery(
                in_app=True,
                sms=await comm.send_sms(
                    phone_number=guest_group.lead_guest_phone,
                    message=body.message.strip(),
                    language=guest_group.preferred_language or "en",
                ),
            )

        logger.info(
            "Host %s broadcast to group %s: %s...",
            current_host.id,
            guest_group_id,
            body.message[:50],
        )
        return HostGroupBroadcastResponse(
            success=True,
            message="Message sent to the group.",
            delivery=delivery,
            broadcast=HostGroupBroadcastRecord.model_validate(record),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Host group broadcast error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message to group",
        )


@router.post("/access/{access_code}/host-message", response_model=GuestConciergeMessageResponse)
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
            from app.services.host_offerings_for_guest import _guest_safe_local_specialties

            def _specialty_labels(raw: list) -> list[str]:
                labels: list[str] = []
                for item in _guest_safe_local_specialties(raw or [])[:3]:
                    if isinstance(item, str):
                        labels.append(item)
                    elif isinstance(item, dict):
                        labels.append(
                            item.get("name")
                            or item.get("title")
                            or item.get("label")
                            or "Specialty"
                        )
                return labels

            top_specialties = ", ".join(_specialty_labels(host.local_specialties)) or "local experiences"
            ai_response = (
                f"Hi {guest_name}! As {host.first_name or 'your host'}'s assistant, I'd be happy to help. "
                f"Based on your question about {host.city or 'the area'}, I recommend exploring our local specialties: "
                f"{top_specialties}. Would you like specific recommendations for activities, restaurants, or hidden gems?"
            )
            response: Dict[str, Any] = {
                "success": True,
                "message": ai_response,
                "suggestions": [
                    "Tell me about local restaurants",
                    "What are the best beaches nearby?",
                    "Recommend activities for families",
                    "Show me hidden local gems",
                ],
                "can_contact_host": True,
            }
        else:
            response = {
                "success": True,
                "message": (
                    f"Thanks {guest_name}! Your message has been sent to {host.first_name or 'your host'}. "
                    f"They typically respond within 2 hours. In the meantime, feel free to browse Discover and Plan."
                ),
            }

        from app.services.host_offerings_for_guest import scrub_contact_from_text

        if response.get("message"):
            response["message"] = (
                scrub_contact_from_text(response["message"], scrub_urls=True)
                or response["message"]
            )

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


@router.post("/access/{access_code}/assistant", response_model=GuestConciergeMessageResponse)
async def guest_assistant_chat(
    access_code: str,
    body: GuestAssistantRequest,
    db: AsyncSession = Depends(get_db),
):
    """Guest AI assistant using host stay context and optional provider keys."""
    try:
        guest_group = await validate_access_code(access_code, db)
        host_result = await db.execute(select(Host).where(Host.id == guest_group.host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Host not found")

        profile_result = await db.execute(
            select(HostProfile).where(HostProfile.host_id == guest_group.host_id)
        )
        profile = profile_result.scalar_one_or_none()
        host_offerings = build_host_offerings_payload(host, profile, access_code)

        guest_service = GuestGroupService(db)
        prefs = await guest_service.get_guest_preferences(guest_group.id)
        pref_summary = None
        if prefs:
            p = prefs[0]
            pref_summary = {
                "age_category": getattr(p, "age_category", None),
                "personal_interests": getattr(p, "personal_interests", None) or [],
                "dietary_needs": getattr(p, "dietary_needs", None) or [],
                "cultural_interests": getattr(p, "cultural_interests", None) or [],
                "food_interests": getattr(p, "food_interests", None) or [],
                "mobility_notes": getattr(p, "mobility_notes", None),
                "language_preference": getattr(p, "language_preference", None),
            }
            if guest_group.budget_level:
                pref_summary["budget_level"] = guest_group.budget_level

        stay = host_offerings.get("stay_info") or {}
        context = {
            "role": "guest_stay_assistant",
            "property_name": stay.get("property_name"),
            "city": stay.get("city"),
            "amenities": stay.get("amenities") or [],
            "services_offered": stay.get("services_offered") or [],
            "property_rules": stay.get("property_rules") or {},
            "local_tips": (host_offerings.get("recommendations") or {}).get("local_tips") or [],
            "guest_preferences": pref_summary,
            "group_name": guest_group.group_name,
        }

        if _message_asks_about_events(body.message):
            rec_svc = EventRecommendationService(db)
            rec_payload = await rec_svc.get_recommendations_for_access_code(
                guest_group, host, profile, prefs, limit=5, refresh=False
            )
            rec_payload = sanitize_event_recommendations_for_guest(rec_payload)
            context["nearby_events"] = [
                {
                    "title": r.get("title"),
                    "start_date": r.get("start_date"),
                    "distance_km": r.get("distance_km"),
                    "plan_hint": r.get("plan_hint"),
                    "cities": r.get("cities") or [],
                }
                for r in (rec_payload.get("recommendations") or [])[:5]
            ]

        guest_name = body.guest_name or guest_group.group_name or "Guest"
        system_hint = (
            f"You are a helpful local guide assistant for guests staying at "
            f"{stay.get('property_name') or 'the property'} in {stay.get('city') or 'Croatia'}. "
            "Answer briefly and practically. Prefer host-provided facts. "
            "If nearby_events are listed in context, mention up to three with dates and distance. "
            "If unsure, suggest the guest message their host."
        )
        messages = [
            {"role": "user", "content": body.message.strip()},
        ]

        ai_response_text = None
        ai_provider = "fallback"
        try:
            from app.services.ai_service import AIService

            ai = AIService(db)
            ai_result = await ai.generate_chat_response(
                str(host.id),
                messages,
                context={**context, "system_hint": system_hint},
            )
            if ai_result.get("success") and ai_result.get("response"):
                ai_response_text = str(ai_result["response"]).strip()
                ai_provider = ai_result.get("provider") or "ai"
        except Exception as ai_err:
            logger.warning("Guest assistant AI unavailable: %s", ai_err)

        if not ai_response_text:
            city = stay.get("city") or host.city or "the area"
            nearby = context.get("nearby_events") or []
            if _message_asks_about_events(body.message):
                if nearby:
                    lines = []
                    for ev in nearby[:3]:
                        dist = ev.get("distance_km")
                        dist_part = f" (~{dist} km)" if dist is not None else ""
                        date_part = f" — {ev.get('start_date')}" if ev.get("start_date") else ""
                        lines.append(f"• {ev.get('title')}{dist_part}{date_part}")
                    ai_response_text = (
                        f"Hi {guest_name}! Events near {city}:\n"
                        + "\n".join(lines)
                        + "\nOpen the Events tab for full details and to save ideas to your plan."
                    )
                else:
                    ai_response_text = (
                        f"Hi {guest_name}! Open the Events tab in your guide for festivals and happenings "
                        f"near {city}. You can save ideas to Plan and ask your host to help with timing."
                    )
            else:
                tips = (host_offerings.get("recommendations") or {}).get("local_tips") or []
                tip_line = tips[0] if tips else "Explore Discover and Plan in your guide."
                ai_response_text = (
                    f"Hi {guest_name}! For {city}: {tip_line} "
                    "Your host can help with property-specific questions — tap Message host anytime."
                )

        ai_response_text = scrub_contact_from_text(ai_response_text, scrub_urls=True)

        suggestions = [
            "What's good to do today?",
            "What's on the events list this week?",
            "Where should we eat nearby?",
            "How do check-in and house rules work?",
        ]

        return {
            "success": True,
            "message": ai_response_text,
            "suggestions": suggestions,
            "can_contact_host": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Guest assistant error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process assistant request",
        )


# Guest preference management
@router.post("/access/{access_code}/preferences", response_model=GuestPreferenceGuestResponse, status_code=status.HTTP_201_CREATED)
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
        GuestPreferenceGuestResponse: Created guest preference
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        preference = await guest_service.add_guest_preference(
            guest_group_id=guest_group.id,
            preference_data=preference_data
        )
        
        logger.info(f"Added guest preference for group {guest_group.id}")
        return _preference_for_guest(preference)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add guest preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add guest preference"
        )


@router.get("/access/{access_code}/preferences", response_model=List[GuestPreferenceGuestResponse])
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
        List[GuestPreferenceGuestResponse]: List of guest preferences
    """
    try:
        guest_group = await validate_access_code(access_code, db)
        guest_service = GuestGroupService(db)
        
        preferences = await guest_service.get_guest_preferences(guest_group.id)
        
        logger.info(f"Retrieved {len(preferences)} preferences for group {guest_group.id}")
        return [_preference_for_guest(p) for p in preferences]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve guest preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve guest preferences"
        )


@router.put("/access/{access_code}/preferences/{preference_id}", response_model=GuestPreferenceGuestResponse)
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
        GuestPreferenceGuestResponse: Updated guest preference
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
        if not updated_preference:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update guest preference"
            )
        
        logger.info(f"Updated guest preference {preference_id} for group {guest_group.id}")
        return _preference_for_guest(updated_preference)
        
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
            guest_group_id=guest_group_id,
            evisitor_id=evisitor_id,
            update_data=evisitor_data,
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


@router.post(
    "/{guest_group_id}/evisitor-data/{evisitor_id}/register",
    response_model=GuestEVisitorDataResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_evisitor_registered(
    guest_group_id: uuid.UUID,
    evisitor_id: uuid.UUID,
    body: EVisitorRegisterRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark e-visitor data as registered with Croatian authorities.
    
    Args:
        guest_group_id: Guest group ID
        evisitor_id: E-visitor data ID
        body: Registration payload with confirmation number
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
        
        registered_evisitor = await guest_service.mark_evisitor_registered(
            guest_group_id=guest_group_id,
            evisitor_id=evisitor_id,
            confirmation_number=body.confirmation_number,
        )
        
        if not registered_evisitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="E-visitor data not found"
            )
        
        logger.info(f"E-visitor data {evisitor_id} marked as registered for group {guest_group_id}")
        return registered_evisitor
        
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
        
        success = await guest_service.delete_guest_evisitor_data(
            guest_group_id, evisitor_id
        )
        
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