"""
Host management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for host registration, authentication,
profile management, and CRUD operations.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.models.host import (
    HostCreate,
    HostUpdate,
    HostResponse,
    HostLogin,
    HostProfileCreate,
    HostProfileUpdate,
    HostProfileResponse,
    Host
)

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


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


@router.post("/login", response_model=Dict[str, Any])
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
        
        return {
            "success": True,
            "host": host_response,
            "session_token": auth_result["session_token"],
            "refresh_token": auth_result["refresh_token"],
            "expires_at": auth_result["expires_at"],
            "refresh_expires_at": auth_result["refresh_expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout")
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
        
        return {"success": True, "message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/refresh")
async def refresh_session(
    refresh_data: Dict[str, str],
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
        refresh_token = refresh_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        host_service = HostService(db)
        refresh_result = await host_service.refresh_host_session(refresh_token)
        
        if not refresh_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return {
            "success": True,
            "session_token": refresh_result["session_token"],
            "expires_at": refresh_result["expires_at"]
        }
        
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

@router.get("/sessions")
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
        List of session data
    """
    try:
        host_service = HostService(db)
        sessions = await host_service.get_host_sessions(current_host.id)
        
        return {
            "success": True,
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.post("/logout-all")
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
        
        return {
            "success": True,
            "message": "Logged out from all devices"
        }
        
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


@router.get("/analytics", response_model=Dict[str, Any])
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
        # Import services here to avoid circular imports
        from app.services.guest_group_service import GuestGroupService
        from app.services.attraction_service import AttractionService
        
        guest_group_service = GuestGroupService(db)
        attraction_service = AttractionService(db)
        
        # Get basic analytics data
        guest_groups = await guest_group_service.get_host_guest_groups(current_host.id)
        attractions = await attraction_service.get_host_attractions(current_host.id)
        
        # Calculate analytics
        active_groups = len([g for g in guest_groups if g.status == 'active'])
        total_attractions = len(attractions)
        
        # Get real recommendation counts
        from app.models.recommendation import Recommendation, RecommendationSet
        from app.models.attraction import AttractionReview
        from sqlalchemy import select, func, and_
        from datetime import datetime, timedelta
        
        # Count total recommendations given by this host
        total_recommendations_query = select(func.count(RecommendationSet.id)).where(
            RecommendationSet.host_id == current_host.id
        )
        total_recommendations_result = await db.execute(total_recommendations_query)
        total_recommendations = total_recommendations_result.scalar() or 0
        
        # Count recommendations given this month
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_recommendations_query = select(func.count(RecommendationSet.id)).where(
            and_(
                RecommendationSet.host_id == current_host.id,
                RecommendationSet.created_at >= current_month_start
            )
        )
        monthly_recommendations_result = await db.execute(monthly_recommendations_query)
        monthly_recommendations = monthly_recommendations_result.scalar() or 0
        
        # Get real review statistics
        review_stats = await attraction_service.get_host_review_stats(current_host.id)
        
        # Calculate real satisfaction metrics
        if review_stats and review_stats.total_reviews_received > 0:
            # Get average rating from actual reviews by joining with attractions
            avg_rating_query = select(func.avg(AttractionReview.rating)).select_from(
                AttractionReview.join(Attraction, AttractionReview.attraction_id == Attraction.id)
            ).where(
                and_(
                    Attraction.created_by_host_id == current_host.id,
                    AttractionReview.status == "APPROVED"
                )
            )
            avg_rating_result = await db.execute(avg_rating_query)
            average_rating = avg_rating_result.scalar() or 0.0
            total_reviews = review_stats.total_reviews_received
        else:
            # Fallback to host's stored average rating
            average_rating = current_host.average_rating or 0.0
            total_reviews = 0
        
        analytics = {
            "guest_groups": {
                "total": len(guest_groups),
                "active": active_groups,
                "inactive": len(guest_groups) - active_groups
            },
            "attractions": {
                "total": total_attractions,
                "categories": {}
            },
            "recommendations": {
                "total_given": total_recommendations,
                "this_month": monthly_recommendations
            },
            "satisfaction": {
                "average_rating": round(average_rating, 1),
                "total_reviews": total_reviews
            }
        }
        
        # Count attractions by category
        for attraction in attractions:
            category = attraction.attraction_type or "Uncategorized"
            analytics["attractions"]["categories"][category] = analytics["attractions"]["categories"].get(category, 0) + 1
        
        logger.info(f"Analytics retrieved successfully for: {current_host.email}")
        return analytics
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed for {current_host.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics data"
        )


@router.get("/{host_id}", response_model=HostResponse)
async def get_host_by_id(
    host_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get host information by ID (public endpoint).
    
    Args:
        host_id: Host UUID
        db: Database session
        
    Returns:
        HostResponse: Host information
        
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
    
    return HostResponse.model_validate(host)


@router.get("/", response_model=List[HostResponse])
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
        List[HostResponse]: List of hosts
    """
    host_service = HostService(db)
    
    if city:
        # Search by location
        hosts = await host_service.search_hosts_by_location(city, county)
    else:
        # List all hosts with pagination
        hosts = await host_service.list_hosts(skip, limit)
    
    return hosts


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host profile not found"
        )
    
    return HostProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=HostProfileResponse)
async def update_host_profile(
    profile_data: HostProfileUpdate,
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
    return HostProfileResponse.model_validate(profile) 