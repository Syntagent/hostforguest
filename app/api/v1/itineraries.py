"""
Itinerary planning API endpoints for guest trip management.

Provides comprehensive itinerary creation, day planning, activity management,
and Google Maps integration for Croatian tourism experiences.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
import logging
from datetime import datetime

from app.core.database import get_db
from app.models import (
    Host,
    ItineraryCreate,
    ItineraryUpdate,
    ItineraryResponse,
    ItineraryWithDetails,
    ItineraryAssignFromTemplate,
    DayPlanCreate,
    DayPlanResponse,
    DayPlanWithActivities,
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityVoteCreate,
    ActivityVoteResponse,
    RoutePointCreate,
    RoutePointReorder,
    RoutePointResponse,
    GoogleMapsDirectionsRequest,
    GoogleMapsDirectionsResponse,
    ItinerarySuggestionRequest,
    ItinerarySuggestionResponse,
)
from app.services.itinerary_service import ItineraryService
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.host_service import HostService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_host(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Host:
    """Authenticate host via X-Session-Token (same as guest-groups and dashboard)."""
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


# Host-facing endpoints for creating itineraries


@router.get("/host/templates", response_model=List[ItineraryResponse])
async def list_route_templates(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """List reusable route templates for the authenticated host."""
    svc = ItineraryService(db)
    return await svc.list_host_templates(current_host.id)


@router.get("/host/itineraries", response_model=List[ItineraryResponse])
async def list_host_guest_itineraries(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """List guest itineraries (non-templates) for the authenticated host."""
    svc = ItineraryService(db)
    return await svc.list_host_itineraries(current_host.id)


@router.post(
    "/templates/{template_id}/assign",
    response_model=ItineraryWithDetails,
    status_code=status.HTTP_201_CREATED,
)
async def assign_template_to_guest_group(
    template_id: uuid.UUID,
    body: ItineraryAssignFromTemplate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Copy a route template into a new itinerary for a guest group."""
    svc = ItineraryService(db)
    result = await svc.assign_template_to_group(current_host.id, template_id, body)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign template (invalid template, wrong host, group not found, or group already has an itinerary)",
        )
    return result


@router.get("/host/day-plans/{day_plan_id}/map-view")
async def get_host_day_plan_map_view(
    day_plan_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Map markers and route hints for a day plan (host auth, any itinerary owned by host)."""
    svc = ItineraryService(db)
    map_data = await svc.get_map_view_data_for_host(day_plan_id, current_host.id)
    if not map_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Day plan not found or no map data",
        )
    return map_data


@router.post("/", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    itinerary_data: ItineraryCreate,
    guest_group_id: Optional[uuid.UUID] = Query(
        None,
        description="Required when is_template is false",
    ),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a guest itinerary or a reusable route template (is_template=true, no guest_group_id).
    """
    try:
        if not itinerary_data.is_template:
            if guest_group_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="guest_group_id is required when is_template is false",
                )
            guest_svc = GuestGroupService(db)
            grp = await guest_svc.get_guest_group_by_id(guest_group_id)
            if not grp or not host_owns_guest_group(grp, current_host.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Guest group not found or not owned by this host",
                )

        itinerary_service = ItineraryService(db)

        itinerary = await itinerary_service.create_itinerary(
            host_id=current_host.id,
            guest_group_id=guest_group_id,
            itinerary_data=itinerary_data,
        )

        if not itinerary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create itinerary",
            )

        logger.info(
            "Created itinerary %s (template=%s, group=%s)",
            itinerary.id,
            itinerary_data.is_template,
            guest_group_id,
        )
        return itinerary

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        ) from ve
    except Exception as e:
        logger.error(f"Failed to create itinerary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create itinerary",
        ) from e


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
async def update_itinerary(
    itinerary_id: uuid.UUID,
    body: ItineraryUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Save route template / itinerary metadata (title, base location, etc.)."""
    svc = ItineraryService(db)
    updated = await svc.update_itinerary(itinerary_id, current_host.id, body)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found or access denied",
        )
    return updated


@router.get("/{itinerary_id}/route-points", response_model=List[RoutePointResponse])
async def list_route_points(
    itinerary_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """List TNT / route stops for an itinerary (all days)."""
    svc = ItineraryService(db)
    points = await svc.list_route_points(itinerary_id, current_host.id)
    if points is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return points


@router.post(
    "/{itinerary_id}/route-points",
    response_model=RoutePointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_route_point(
    itinerary_id: uuid.UUID,
    body: RoutePointCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Add a TNT point to a day on this route."""
    svc = ItineraryService(db)
    point = await svc.add_route_point(itinerary_id, current_host.id, body)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not add route point (invalid itinerary or day plan)",
        )
    return point


@router.put("/route-points/{point_id}", response_model=RoutePointResponse)
async def update_route_point(
    point_id: uuid.UUID,
    body: ActivityUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Update a TNT point."""
    svc = ItineraryService(db)
    point = await svc.update_route_point(point_id, current_host.id, body)
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route point not found")
    return point


@router.delete("/route-points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route_point(
    point_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Delete a TNT point."""
    svc = ItineraryService(db)
    ok = await svc.delete_route_point(point_id, current_host.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route point not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{itinerary_id}/route-points/reorder")
async def reorder_route_points(
    itinerary_id: uuid.UUID,
    body: RoutePointReorder,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Reorder TNT points within a day."""
    svc = ItineraryService(db)
    ok = await svc.reorder_route_points(itinerary_id, current_host.id, body)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not reorder route points",
        )
    return {"success": True}


@router.get("/{itinerary_id}", response_model=ItineraryWithDetails)
async def get_itinerary(
    itinerary_id: uuid.UUID,
    include_activities: bool = Query(True, description="Include activities in day plans"),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a complete itinerary with day plans and activities.
    
    Args:
        itinerary_id: Itinerary ID
        include_activities: Whether to include activities
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ItineraryWithDetails: Complete itinerary
    """
    try:
        itinerary_service = ItineraryService(db)
        
        itinerary = await itinerary_service.get_itinerary_with_details(
            itinerary_id=itinerary_id,
            include_activities=include_activities
        )
        
        if not itinerary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Itinerary not found"
            )
        
        # Verify host has access to this itinerary
        if itinerary.host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this itinerary"
            )
        
        return itinerary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get itinerary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve itinerary"
        )


@router.post("/{itinerary_id}/day-plans", response_model=DayPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_day_plan(
    itinerary_id: uuid.UUID,
    day_plan_data: DayPlanCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a day plan within an itinerary.
    
    Args:
        itinerary_id: Parent itinerary ID
        day_plan_data: Day plan creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        DayPlanResponse: Created day plan
    """
    try:
        itinerary_service = ItineraryService(db)
        
        # Verify host owns this itinerary
        itinerary = await itinerary_service.get_itinerary_with_details(itinerary_id, False)
        if not itinerary or itinerary.host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this itinerary"
            )
        
        day_plan = await itinerary_service.create_day_plan(
            itinerary_id=itinerary_id,
            day_plan_data=day_plan_data
        )
        
        if not day_plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create day plan"
            )
        
        logger.info(f"Created day plan {day_plan.id} for itinerary {itinerary_id}")
        return day_plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create day plan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create day plan"
        )


@router.post("/day-plans/{day_plan_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def add_activity_to_day(
    day_plan_id: uuid.UUID,
    activity_data: ActivityCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an activity to a day plan with Google Maps integration.
    
    Args:
        day_plan_id: Day plan ID
        activity_data: Activity creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ActivityResponse: Created activity with travel information
    """
    try:
        itinerary_service = ItineraryService(db)
        
        activity = await itinerary_service.add_activity_to_day(
            day_plan_id=day_plan_id,
            activity_data=activity_data
        )
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add activity to day plan"
            )
        
        logger.info(f"Added activity {activity.id} to day plan {day_plan_id}")
        return activity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add activity"
        )


@router.post("/day-plans/{day_plan_id}/optimize-route")
async def optimize_day_plan_route(
    day_plan_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Optimize the route for a day plan using Google Maps.
    
    Args:
        day_plan_id: Day plan to optimize
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict: Optimization result
    """
    try:
        itinerary_service = ItineraryService(db)
        
        success = await itinerary_service.optimize_day_plan_route(day_plan_id)
        
        if success:
            return {
                "success": True,
                "message": "Route optimized successfully",
                "day_plan_id": str(day_plan_id)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to optimize route - insufficient location data"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize route: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize route"
        )


# Google Maps integration endpoints

@router.post("/directions", response_model=GoogleMapsDirectionsResponse)
async def get_directions(
    directions_request: GoogleMapsDirectionsRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get directions between two locations using Google Maps.
    
    Args:
        directions_request: Direction request parameters
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        GoogleMapsDirectionsResponse: Directions with travel information
    """
    try:
        itinerary_service = ItineraryService(db)
        
        directions = await itinerary_service.get_directions(
            host_id=current_host.id,
            directions_request=directions_request
        )
        
        if not directions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to get directions - check locations and Google Maps API key"
            )
        
        return directions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get directions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get directions"
        )


# AI-powered itinerary generation

@router.post("/suggestions", response_model=ItinerarySuggestionResponse)
async def generate_itinerary_suggestions(
    suggestion_request: ItinerarySuggestionRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered itinerary suggestions for a guest group.
    
    Args:
        suggestion_request: Suggestion parameters
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ItinerarySuggestionResponse: Generated itinerary suggestions
    """
    try:
        itinerary_service = ItineraryService(db)
        
        suggestions = await itinerary_service.generate_itinerary_suggestions(
            host_id=current_host.id,
            suggestion_request=suggestion_request
        )
        
        if not suggestions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to generate suggestions - check guest group and parameters"
            )
        
        logger.info(f"Generated itinerary suggestions for guest group {suggestion_request.guest_group_id}")
        return suggestions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate itinerary suggestions"
        )


# Guest-facing endpoints (using access codes)

@router.get(
    "/guest/{access_code}/itinerary",
    response_model=Optional[ItineraryWithDetails],
)
async def get_guest_itinerary(
    access_code: str,
    db: AsyncSession = Depends(get_db)
) -> Optional[ItineraryWithDetails]:
    """
    Get itinerary for guests using access code.
    
    Args:
        access_code: Guest access code
        db: Database session
        
    Returns:
        ItineraryWithDetails: Guest's itinerary
    """
    try:
        guest_service = GuestGroupService(db)
        itinerary_service = ItineraryService(db)
        
        # Validate access code and get guest group
        guest_group = await guest_service.validate_access_code(access_code)
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )
        
        # Find itinerary for this guest group
        # This would need to be implemented in the itinerary service
        # For now, we'll return a placeholder response
        
        logger.info(f"Guest accessed itinerary with code {access_code}")
        
        # Get itinerary for this guest group
        itinerary_service = ItineraryService(db)
        itinerary = await itinerary_service.get_itinerary_by_guest_group(
            guest_group_id=guest_group.id,
            include_activities=True
        )
        
        if not itinerary:
            # 200 + JSON null — avoids client/proxy treating "no itinerary" as an error (404 noise in DevTools).
            return Response(content="null", media_type="application/json", status_code=200)

        return itinerary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get guest itinerary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve itinerary"
        )


# Collaborative planning endpoints

@router.post("/activities/{activity_id}/vote", response_model=ActivityVoteResponse)
async def vote_on_activity(
    activity_id: uuid.UUID,
    vote_data: ActivityVoteCreate,
    access_code: str = Query(..., description="Guest access code"),
    db: AsyncSession = Depends(get_db)
):
    """
    Allow guests to vote on activities using access code.
    
    Args:
        activity_id: Activity to vote on
        vote_data: Vote information
        access_code: Guest access code
        db: Database session
        
    Returns:
        ActivityVoteResponse: Created vote
    """
    try:
        guest_service = GuestGroupService(db)
        itinerary_service = ItineraryService(db)
        
        # Validate access code and get guest group
        guest_group = await guest_service.validate_access_code(access_code)
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )
        
        vote = await itinerary_service.vote_on_activity(
            guest_group_id=guest_group.id,
            activity_id=activity_id,
            vote_data=vote_data
        )
        
        if not vote:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record vote"
            )
        
        logger.info(f"Guest voted on activity {activity_id}: {vote_data.vote}")
        return vote
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to vote on activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record vote"
        )


@router.get("/activities/{activity_id}/votes", response_model=List[ActivityVoteResponse])
async def get_activity_votes(
    activity_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all votes for an activity (host only).
    
    Args:
        activity_id: Activity ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        List[ActivityVoteResponse]: List of votes
    """
    try:
        itinerary_service = ItineraryService(db)
        
        votes = await itinerary_service.get_activity_votes(activity_id)
        
        logger.info(f"Retrieved {len(votes)} votes for activity {activity_id}")
        return votes
        
    except Exception as e:
        logger.error(f"Failed to get activity votes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve votes"
        )


# Utility endpoints for guest experience

@router.get("/guest/{access_code}/day-plans/{day_plan_id}/map-view")
async def get_day_plan_map_view(
    access_code: str,
    day_plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get map view data for a day plan (guest-facing).
    
    Args:
        access_code: Guest access code
        day_plan_id: Day plan ID
        db: Database session
        
    Returns:
        Dict: Map view data with locations and routes
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Validate access code
        guest_group = await guest_service.validate_access_code(access_code)
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )
        
        # Get map view data from service
        itinerary_service = ItineraryService(db)
        map_data = await itinerary_service.get_map_view_data(day_plan_id)
        
        if not map_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Day plan not found or has no locations"
            )
        
        return map_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get map view: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate map view"
        )


@router.post("/activities/{activity_id}/check-in")
async def check_in_to_activity(
    activity_id: uuid.UUID,
    access_code: str = Query(..., description="Guest access code"),
    db: AsyncSession = Depends(get_db)
):
    """
    Allow guests to check in to an activity.
    
    Args:
        activity_id: Activity ID
        access_code: Guest access code
        db: Database session
        
    Returns:
        Dict: Check-in confirmation
    """
    try:
        guest_service = GuestGroupService(db)
        
        # Validate access code
        guest_group = await guest_service.validate_access_code(access_code)
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )
        
        # Check in to activity
        itinerary_service = ItineraryService(db)
        check_in_result = await itinerary_service.check_in_activity(
            activity_id=activity_id,
            guest_group_id=guest_group.id
        )
        
        return check_in_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check in to activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check in"
        ) 