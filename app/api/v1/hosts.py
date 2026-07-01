"""
Host management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for host registration, authentication,
profile management, and CRUD operations.
"""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import get_current_host
from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.services.host_offerings_for_guest import guest_safe_host_public
from app.models.guest_group import GuestGroupResponse
from app.models.attraction import AttractionResponse
from app.models.host import (
    HostCreate,
    HostUpdate,
    HostResponse,
    HostPublicResponse,
    HostLogin,
    HostPasswordChange,
    HostProfileCreate,
    HostProfileUpdate,
    HostProfileResponse,
    Host,
    TelegramPairingResponse,
    HostAnalytics,
    HostAnalyticsGuestGroups,
    HostAnalyticsAttractions,
    HostAnalyticsRecommendations,
    HostAnalyticsSatisfaction,
    HostDashboardStatsResponse,
    DashboardRealtimeSnippet,
    HostSessionItem,
    HostSessionsResponse,
    HostAuthSuccessResponse,
    HostSessionRefreshResponse,
    HostLoginResponse,
    HostGeocodeResponse,
    HostTelegramUnlinkResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# In-process dashboard bundle cache: host_id -> (monotonic_ts, payload)
_dashboard_stats_cache: Dict[str, Tuple[float, HostDashboardStatsResponse]] = {}
_DASHBOARD_STATS_TTL_SEC = 60


async def _build_host_analytics(current_host: Host, db: AsyncSession) -> HostAnalytics:
    """Shared analytics payload for /analytics and /dashboard/stats."""
    from app.services.guest_group_service import GuestGroupService
    from app.services.attraction_service import AttractionService
    from app.models.recommendation import RecommendationSet
    from app.models.attraction import Attraction, AttractionReview
    from sqlalchemy import select, func, and_

    guest_group_service = GuestGroupService(db)
    attraction_service = AttractionService(db)

    from app.models.guest_group import GuestGroupStatus
    from app.services.guest_group_stay import is_in_stay

    guest_groups = await guest_group_service.get_host_guest_groups(current_host.id)
    attractions = await attraction_service.get_host_attractions(current_host.id)

    # "Active" on the dashboard = in stay today (calendar dates), not DB activation status.
    in_stay_groups = len([g for g in guest_groups if is_in_stay(g)])
    activated_groups = len(
        [g for g in guest_groups if g.status == GuestGroupStatus.ACTIVE.value]
    )

    total_recommendations_query = select(func.count(RecommendationSet.id)).where(
        RecommendationSet.host_id == current_host.id
    )
    total_recommendations_result = await db.execute(total_recommendations_query)
    total_recommendations = total_recommendations_result.scalar() or 0

    current_month_start = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    monthly_recommendations_query = select(func.count(RecommendationSet.id)).where(
        and_(
            RecommendationSet.host_id == current_host.id,
            RecommendationSet.created_at >= current_month_start,
        )
    )
    monthly_recommendations_result = await db.execute(monthly_recommendations_query)
    monthly_recommendations = monthly_recommendations_result.scalar() or 0

    review_stats = await attraction_service.get_host_review_stats(current_host.id)

    if review_stats and review_stats.total_reviews_received > 0:
        avg_rating_query = (
            select(func.avg(AttractionReview.rating))
            .select_from(
                AttractionReview.join(
                    Attraction, AttractionReview.attraction_id == Attraction.id
                )
            )
            .where(
                and_(
                    Attraction.created_by_host_id == current_host.id,
                    AttractionReview.status == "APPROVED",
                )
            )
        )
        avg_rating_result = await db.execute(avg_rating_query)
        average_rating = avg_rating_result.scalar() or 0.0
        total_reviews = review_stats.total_reviews_received
    else:
        average_rating = current_host.average_rating or 0.0
        total_reviews = 0

    analytics = HostAnalytics(
        guest_groups=HostAnalyticsGuestGroups(
            total=len(guest_groups),
            active=in_stay_groups,
            in_stay=in_stay_groups,
            activated=activated_groups,
            inactive=len(guest_groups) - in_stay_groups,
        ),
        attractions=HostAnalyticsAttractions(total=len(attractions), categories={}),
        recommendations=HostAnalyticsRecommendations(
            total_given=total_recommendations,
            this_month=monthly_recommendations,
        ),
        satisfaction=HostAnalyticsSatisfaction(
            average_rating=round(average_rating, 1),
            total_reviews=total_reviews,
        ),
    )
    for attraction in attractions:
        category = attraction.attraction_type or "Uncategorized"
        analytics.attractions.categories[category] = (
            analytics.attractions.categories.get(category, 0) + 1
        )
    return analytics


@router.post("/register", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
async def register_host(
    host_data: HostCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new host account.
    
    Creates a new host account with authentication credentials
    and basic profile information.
    
    Args:
        host_data: Host registration data
        db: Database session
        
    Returns:
        HostResponse: Created host information
        
    Raises:
        HTTPException: If email already exists or registration fails
    """
    logger.info(f"Host registration attempt for email: {host_data.email}")
    
    host_service = HostService(db)
    
    # Check if email already exists
    existing_host = await host_service.get_host_by_email(host_data.email)
    if existing_host:
        logger.warning(f"Registration failed: Email already exists {host_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new host
    new_host = await host_service.create_host(host_data)
    if not new_host:
        logger.error(f"Host registration failed for email: {host_data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host registration failed"
        )
    
    logger.info(f"Host registered successfully: {host_data.email}")
    return new_host


@router.post("/login", response_model=HostLoginResponse)
async def login_host(
    login_data: HostLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login host and create session.
    
    Args:
        login_data: Login credentials
        request: FastAPI request object
        db: Database session
        
    Returns:
        Dict with host data and session tokens
    """
    try:
        host_service = HostService(db)
        
        # Get client info
        user_agent = request.headers.get("User-Agent")
        ip_address = request.client.host if request.client else None
        
        # Authenticate and create session
        auth_result = await host_service.authenticate_host(
            email=login_data.email,
            password=login_data.password,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Convert host to response model
        host_response = HostResponse.model_validate(auth_result["host"])
        
        return HostLoginResponse(
            success=True,
            host=host_response,
            session_token=auth_result["session_token"],
            refresh_token=auth_result["refresh_token"],
            expires_at=auth_result["expires_at"],
            refresh_expires_at=auth_result["refresh_expires_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout", response_model=HostAuthSuccessResponse)
async def logout_host(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout host by invalidating session.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Success message
    """
    try:
        session_token = request.headers.get("X-Session-Token")
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session token required"
            )
        
        host_service = HostService(db)
        success = await host_service.logout_host(session_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session token"
            )
        
        return HostAuthSuccessResponse(success=True, message="Logged out successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/refresh", response_model=HostSessionRefreshResponse)
async def refresh_session(
    request: Request,
    refresh_data: Optional[Dict[str, str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh session using refresh token.
    
    Args:
        refresh_data: Dict with refresh_token
        db: Database session
        
    Returns:
        Dict with new session data
    """
    try:
        refresh_data = refresh_data or {}
        refresh_token = refresh_data.get("refresh_token")
        if not refresh_token:
            session_token = request.headers.get("X-Session-Token")
            if session_token:
                from app.services.session_service import SessionService
                session_svc = SessionService(db)
                existing = await session_svc.validate_session(session_token)
                if existing and existing.refresh_token:
                    refresh_token = existing.refresh_token
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required (body or valid X-Session-Token)"
            )
        
        host_service = HostService(db)
        refresh_result = await host_service.refresh_host_session(refresh_token)
        
        if not refresh_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return HostSessionRefreshResponse(
            success=True,
            session_token=refresh_result["session_token"],
            expires_at=refresh_result["expires_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session refresh failed"
        )

@router.get("/me", response_model=HostResponse)
async def get_current_host_info(
    current_host: Host = Depends(get_current_host)
):
    """
    Get current host information.
    
    Args:
        current_host: Current authenticated host
        
    Returns:
        HostResponse: Current host data
    """
    return HostResponse.model_validate(current_host)

@router.get("/sessions", response_model=HostSessionsResponse)
async def get_host_sessions(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active sessions for current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostSessionsResponse: Active session rows for the account UI
    """
    try:
        host_service = HostService(db)
        sessions = await host_service.get_host_sessions(current_host.id)
        return HostSessionsResponse(
            success=True,
            sessions=[HostSessionItem.model_validate(row) for row in sessions],
        )
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.post("/logout-all", response_model=HostAuthSuccessResponse)
async def logout_all_devices(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from all devices.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Success message
    """
    try:
        host_service = HostService(db)
        success = await host_service.logout_all_devices(current_host.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout from all devices"
            )
        
        return HostAuthSuccessResponse(
            success=True,
            message="Logged out from all devices",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout all devices error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.put("/me", response_model=HostResponse)
async def update_current_host(
    host_update: HostUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current host's profile information.
    
    Args:
        host_update: Updated host data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostResponse: Updated host information
        
    Raises:
        HTTPException: If update fails
    """
    logger.info(f"Host profile update for: {current_host.email}")
    
    host_service = HostService(db)
    updated_host = await host_service.update_host(current_host.id, host_update)
    
    if not updated_host:
        logger.error(f"Host profile update failed for: {current_host.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host profile update failed"
        )
    
    logger.info(f"Host profile updated successfully: {current_host.email}")
    return updated_host


@router.post("/me/change-password", response_model=HostAuthSuccessResponse)
async def change_host_password(
    body: HostPasswordChange,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the authenticated host."""
    host_service = HostService(db)
    ok = await host_service.change_password(
        current_host.id,
        body.current_password,
        body.new_password,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return HostAuthSuccessResponse(success=True, message="Password updated")


@router.get("/me/telegram-code", response_model=TelegramPairingResponse)
async def get_telegram_pairing_code(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Generate or return the host's active Telegram pairing code (10 min TTL)."""
    from app.services.telegram_pairing_service import TelegramPairingService

    svc = TelegramPairingService(db)
    payload = await svc.get_or_create_pairing_code(current_host.id)
    return TelegramPairingResponse.model_validate(payload)


@router.delete("/me/telegram-link", response_model=HostTelegramUnlinkResponse)
async def unlink_telegram_account(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Telegram from the authenticated host account."""
    from app.services.telegram_pairing_service import TelegramPairingService

    svc = TelegramPairingService(db)
    ok = await svc.unlink_telegram(current_host.id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink Telegram",
        )
    return HostTelegramUnlinkResponse(
        success=True,
        message="Telegram veza prekinuta",
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_host(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) current host account.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Raises:
        HTTPException: If deletion fails
    """
    logger.info(f"Host account deletion for: {current_host.email}")
    
    host_service = HostService(db)
    success = await host_service.delete_host(current_host.id)
    
    if not success:
        logger.error(f"Host account deletion failed for: {current_host.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host account deletion failed"
        )
    
    logger.info(f"Host account deleted successfully: {current_host.email}")


@router.get("/analytics", response_model=HostAnalytics)
async def get_host_analytics(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics data for the current host's dashboard.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Analytics data including guest groups, attractions, etc.
        
    Raises:
        HTTPException: If analytics retrieval fails
    """
    logger.info(f"Host analytics request for: {current_host.email}")
    
    try:
        analytics = await _build_host_analytics(current_host, db)
        logger.info(f"Analytics retrieved successfully for: {current_host.email}")
        return analytics
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed for {current_host.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics data"
        )


@router.get("/dashboard/stats", response_model=HostDashboardStatsResponse)
async def get_dashboard_stats(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
    refresh: bool = Query(False, description="Bypass 60s in-process cache"),
):
    """
    Single-call dashboard bundle (analytics, groups, attractions, profile, realtime).

    Cached in-process for 60 seconds per host unless refresh=true.
    """
    cache_key = str(current_host.id)
    now = time.monotonic()
    if not refresh:
        cached = _dashboard_stats_cache.get(cache_key)
        if cached and (now - cached[0]) < _DASHBOARD_STATS_TTL_SEC:
            return cached[1]

    try:
        from app.services.guest_group_service import GuestGroupService
        from app.services.attraction_service import AttractionService

        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        attraction_service = AttractionService(db)

        analytics = await _build_host_analytics(current_host, db)
        profile = await host_service.get_host_profile(current_host.id)
        guest_groups = await guest_group_service.get_host_guest_groups(current_host.id)
        attractions = await attraction_service.get_host_attractions(current_host.id)

        realtime_updates: List[DashboardRealtimeSnippet] = []
        try:
            from app.services.events_feed_service import EventsFeedService

            city = current_host.city or (profile.city if profile else None) or "Lovran"
            updates = await EventsFeedService(db).get_updates(city=city, limit=5)
            realtime_updates = [
                DashboardRealtimeSnippet(
                    id=str(u.get("id", "")),
                    title=u.get("title", ""),
                    content=(u.get("content") or u.get("description") or "")[:500],
                    description=(u.get("description") or u.get("content") or "")[:300],
                    created_at=u.get("created_at"),
                    start_at=u.get("start_at"),
                    end_at=u.get("end_at"),
                    source=u.get("source_name") or u.get("source"),
                )
                for u in updates
            ]
        except Exception as rt_err:
            logger.warning("Dashboard realtime snippet skipped: %s", rt_err)

        payload = HostDashboardStatsResponse(
            analytics=analytics,
            profile=HostProfileResponse.model_validate(profile) if profile else None,
            guest_groups=[
                GuestGroupResponse.model_validate(g) for g in guest_groups
            ],
            attractions=[
                AttractionResponse.model_validate(a) for a in attractions
            ],
            realtime_updates=realtime_updates,
            cached_at=datetime.now(timezone.utc).isoformat(),
        )
        _dashboard_stats_cache[cache_key] = (now, payload)
        return payload
    except Exception as e:
        logger.error("Dashboard stats failed for %s: %s", current_host.email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard stats",
        ) from e


@router.get("/{host_id}", response_model=HostPublicResponse)
async def get_host_by_id(
    host_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get host public profile by ID (no email, phone, or street address).
    
    Args:
        host_id: Host UUID
        db: Database session
        
    Returns:
        HostPublicResponse: Public host profile
        
    Raises:
        HTTPException: If host not found
    """
    host_service = HostService(db)
    host = await host_service.get_host_by_id(host_id)
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    
    return guest_safe_host_public(host)


@router.get("/", response_model=List[HostPublicResponse])
async def list_hosts(
    skip: int = 0,
    limit: int = 100,
    city: Optional[str] = None,
    county: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List hosts with optional filtering and pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        city: Optional city filter
        county: Optional county filter
        db: Database session
        
    Returns:
        List[HostPublicResponse]: List of hosts (PII omitted)
    """
    host_service = HostService(db)
    
    if city:
        # Search by location
        hosts = await host_service.search_hosts_by_location(city, county)
    else:
        # List all hosts with pagination
        hosts = await host_service.list_hosts(skip, limit)
    
    return [guest_safe_host_public(h) for h in hosts]


# Host Profile Endpoints
@router.post("/me/profile", response_model=HostProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_host_profile(
    profile_data: HostProfileCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create extended profile for current host.
    
    Args:
        profile_data: Profile creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostProfileResponse: Created profile information
        
    Raises:
        HTTPException: If profile creation fails
    """
    logger.info(f"Host profile creation for: {current_host.email}")
    
    host_service = HostService(db)
    profile = await host_service.create_host_profile(current_host.id, profile_data)
    
    if not profile:
        logger.error(f"Host profile creation failed for: {current_host.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host profile creation failed - profile may already exist"
        )
    
    logger.info(f"Host profile created successfully for: {current_host.email}")
    return profile


@router.get("/me/profile", response_model=HostProfileResponse)
async def get_current_host_extended_profile(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current host's extended profile.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostProfileResponse: Extended profile information
        
    Raises:
        HTTPException: If profile not found
    """
    host_service = HostService(db)
    profile = await host_service.get_host_profile(current_host.id)
    
    if not profile:
        # Return empty profile instead of 404 so frontend can show create form
        now = datetime.now(timezone.utc)
        return HostProfileResponse(
            id=uuid.uuid4(),
            host_id=current_host.id,
            created_at=now,
            updated_at=now,
        )
    
    return HostProfileResponse.model_validate(profile)


@router.get("/me/geocode", response_model=HostGeocodeResponse)
async def geocode_accommodation_address(
    address: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
    current_host: Host = Depends(get_current_host),
):
    """
    Resolve GPS coordinates from accommodation address fields.

    Used by the Accommodation tab to auto-fill latitude/longitude while typing.
    """
    from app.services.geocoding_service import GeocodingService

    _ = current_host  # auth gate only
    result = GeocodingService.geocode(address=address, city=city, county=county)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not locate this address. Add city and county, then try again.",
        )
    return HostGeocodeResponse(
        latitude=result.latitude,
        longitude=result.longitude,
        matched_query=result.matched_query,
        precision=result.precision,
    )


@router.put("/me/profile", response_model=HostProfileResponse)
async def update_host_profile(
    profile_data: HostProfileUpdate,
    background_tasks: BackgroundTasks,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current host's extended profile.
    
    Args:
        profile_data: Profile update data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostProfileResponse: Updated profile information
        
    Raises:
        HTTPException: If profile update fails
    """
    logger.info(f"Host profile update for: {current_host.email}")
    
    host_service = HostService(db)
    profile = await host_service.update_host_profile(current_host.id, profile_data)
    
    if not profile:
        logger.error(f"Host profile update failed for: {current_host.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host profile update failed"
        )
    
    logger.info(f"Host profile updated successfully for: {current_host.email}")

    if profile_data.city or profile_data.latitude or profile_data.longitude:
        async def _discover_event_sources() -> None:
            from app.core.database import get_async_session
            from app.services.event_source_discovery_agent import EventSourceDiscoveryAgent
            from app.services.rls_service import RLSService

            host_id = current_host.id
            async for session in get_async_session():
                await RLSService(session).set_host_context(host_id)
                agent = EventSourceDiscoveryAgent(session)
                prof = await HostService(session).get_host_profile(host_id)
                await agent.discover_for_host(current_host, prof)
                break

        background_tasks.add_task(_discover_event_sources)

    return HostProfileResponse.model_validate(profile) 