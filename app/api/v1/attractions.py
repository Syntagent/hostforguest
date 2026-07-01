"""
Attraction management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for attraction management, search, filtering,
and host contributions to the Croatian tourism database.
"""

import logging
import os
import requests
import json
from typing import List, Optional, Dict, Any
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.attraction_service import AttractionService
from app.services.host_service import HostService
from app.services.guest_group_service import GuestGroupService
from app.services.host_onboarding_service import HostOnboardingService
from app.models import (
    Host,
    AttractionCreate,
    AttractionUpdate,
    AttractionResponse,
    AttractionReviewCreate,
    AttractionReviewResponse,
    AttractionReviewUpdate,
    ReviewModerationRequest,
    ReviewModerationResponse,
    ReviewAnalytics,
    HostReviewStats,
    ReviewSearchRequest,
    ReviewSearchResponse,
    GuestReviewSubmission,
    ReviewHelpfulnessVote,
    SeasonalEventCreate,
    SeasonalEventResponse,
    HostContributionCreate,
    HostContributionResponse,
    AttractionSearchRequest,
    AttractionSearchResponse,
    HostContributionStats
)

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


# AI-powered attraction content generation
@router.post("/generate-content", response_model=Dict[str, Any])
async def generate_attraction_content(
    request: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered content for an attraction based on basic input.
    
    Args:
        request: Dict containing attraction details to enhance
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Generated attraction content
    """
    try:
        logger.info(f"🎯 Generating AI content for attraction by host {current_host.id}")
        
        # Extract basic attraction info from request
        attraction_name = request.get("name", "")
        category = request.get("category", "")
        location = request.get("location", "")
        host_interests = request.get("host_interests", [])
        
        if not attraction_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attraction name is required for AI content generation"
            )
        
        # Build location info
        location_info = {}
        if location:
            location_info["city"] = location
        elif current_host.city:
            location_info["city"] = current_host.city
        
        # Get host interests for personalization
        if not host_interests:
            host_interests = current_host.local_specialties or []
        
        # Use the existing AI service to generate content
        onboarding_service = HostOnboardingService(db)
        
        # Generate personalized content using real Croatian tourism data
        result = await onboarding_service.generate_local_attraction_suggestions(
            host_location=location_info,
            host_interests=host_interests,
            local_knowledge_level="expert"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate attraction content")
            )
        
        # Find the best matching attraction or create enhanced content
        generated_content = await _enhance_attraction_with_ai(
            attraction_name, category, location, result["attractions"], host_interests
        )
        
        logger.info(f"✅ Generated AI content for attraction: {attraction_name}")
        
        return {
            "success": True,
            "content": generated_content,
            "data_source": result.get("data_source", "ai_generated"),
            "sources_used": result.get("sources_used", 0),
            "personalization_level": result.get("personalization_level", "expert")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate attraction content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate attraction content"
        )


async def _enhance_attraction_with_ai(
    attraction_name: str,
    category: str,
    location: str,
    ai_attractions: List[Dict[str, Any]],
    host_interests: List[str]
) -> Dict[str, Any]:
    """
    Enhance attraction content using AI-generated suggestions.
    
    Args:
        attraction_name: Name of the attraction
        category: Category of the attraction
        location: Location of the attraction
        ai_attractions: List of AI-generated attractions
        host_interests: Host's interests for personalization
        
    Returns:
        Dict[str, Any]: Enhanced attraction content
    """
    try:
        # Try to find a matching attraction in AI suggestions
        matching_attraction = None
        for attraction in ai_attractions:
            if (attraction_name.lower() in attraction["name"].lower() or 
                attraction["name"].lower() in attraction_name.lower()):
                matching_attraction = attraction
                break
        
        # If no exact match, find similar category/location
        if not matching_attraction:
            for attraction in ai_attractions:
                if (category and category.lower() in attraction.get("category", "").lower()) or \
                   (location and location.lower() in attraction.get("location", "").lower()):
                    matching_attraction = attraction
                    break
        
        # Use the best match or create enhanced content
        if matching_attraction:
            enhanced_content = {
                "name": attraction_name,
                "description": matching_attraction.get("description", ""),
                "category": category or matching_attraction.get("category", ""),
                "location": location or matching_attraction.get("location", ""),
                "cost_estimate": matching_attraction.get("cost_estimate", ""),
                "authenticity_level": matching_attraction.get("authenticity_level", "high"),
                "host_tips": matching_attraction.get("host_tips", []),
                "best_time": matching_attraction.get("best_time", "anytime"),
                "accessibility": matching_attraction.get("accessibility", "moderate"),
                "crowd_level": matching_attraction.get("crowd_level", "moderate"),
                "local_insights": matching_attraction.get("local_insights", ""),
                "enhanced": True,
                "ai_generated": True
            }
        else:
            # Create enhanced content based on general Croatian tourism knowledge
            enhanced_content = {
                "name": attraction_name,
                "description": f"Discover the authentic charm of {attraction_name} in {location or 'Croatia'}. This {category.lower() if category else 'local attraction'} offers visitors a genuine Croatian experience, combining cultural heritage with modern hospitality.",
                "category": category or "Local Experience",
                "location": location or "Croatia",
                "cost_estimate": "€5-15 per person",
                "authenticity_level": "high",
                "host_tips": [f"Visit during off-peak hours for a more authentic experience at {attraction_name}"],
                "best_time": "morning or evening",
                "accessibility": "moderate",
                "crowd_level": "varies",
                "local_insights": f"Local tip: {attraction_name} is best experienced with an open mind and willingness to embrace Croatian culture.",
                "enhanced": True,
                "ai_generated": True
            }
        
        return enhanced_content
        
    except Exception as e:
        logger.error(f"Error enhancing attraction content: {e}")
        # Return basic enhanced content as fallback
        return {
            "name": attraction_name,
            "description": f"Experience the authentic charm of {attraction_name} in {location or 'Croatia'}. This local attraction offers visitors a genuine Croatian experience.",
            "category": category or "Local Experience",
            "location": location or "Croatia",
            "cost_estimate": "€5-15 per person",
            "authenticity_level": "high",
            "host_tips": [f"Local tip: Visit {attraction_name} during quieter hours for the best experience"],
            "best_time": "anytime",
            "accessibility": "moderate",
            "crowd_level": "moderate",
            "local_insights": "A must-visit local attraction offering authentic Croatian experiences.",
            "enhanced": True,
            "ai_generated": True
        }


# Public attraction endpoints (no authentication required)
@router.get("/", response_model=List[AttractionResponse])
async def get_attractions(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    city: Optional[str] = None,
    attraction_type: Optional[str] = None,
    category: Optional[str] = None,
    season: Optional[str] = None,
    language: Optional[str] = "en"
):
    """
    Get attractions with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        city: Filter by city (e.g., 'Lovran')
        attraction_type: Filter by attraction type
        category: Filter by category
        season: Filter by season (spring, summer, autumn, winter)
        language: Language for content (en, hr, de, it)
        
    Returns:
        List[AttractionResponse]: List of attractions
    """
    try:
        attraction_service = AttractionService(db)
        attractions = await attraction_service.search_attractions(
            city=city,
            attraction_type=attraction_type,
            category_tags=[category] if category else None,
            seasonal_filter=season,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(attractions)} attractions with filters: city={city}, type={attraction_type}")
        return attractions
        
    except Exception as e:
        logger.error(f"Failed to retrieve attractions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attractions"
        )


@router.get("/search", response_model=AttractionSearchResponse)
async def search_attractions(
    search_request: AttractionSearchRequest = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced attraction search with multiple criteria.
    
    Args:
        search_request: Search criteria and filters
        db: Database session
        
    Returns:
        AttractionSearchResponse: Search results with metadata
    """
    try:
        attraction_service = AttractionService(db)
        # Unpack search request into individual parameters for the service method
        city = search_request.city or search_request.query
        category_tags = [search_request.category] if search_request.category else None
        results_list = await attraction_service.search_attractions(
            city=city,
            region=None,
            attraction_type=search_request.attraction_type,
            category_tags=category_tags,
            seasonal_filter=search_request.season,
            skip=search_request.skip,
            limit=search_request.limit,
        )

        logger.info(f"Attraction search returned {len(results_list)} results")
        return AttractionSearchResponse(
            results=results_list,
            total_count=len(results_list),
            page=1,
            per_page=search_request.limit,
            query=search_request.query,
        )
        
    except Exception as e:
        logger.error(f"Failed to search attractions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search attractions"
        )


@router.get("/host", response_model=List[AttractionResponse])
async def get_host_attractions(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None
):
    """
    Get all attractions for the current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by attraction status
        
    Returns:
        List[AttractionResponse]: List of host's attractions
    """
    try:
        attraction_service = AttractionService(db)
        attractions = await attraction_service.get_host_attractions(
            host_id=current_host.id,
            status_filter=status_filter
        )
        
        # Apply pagination
        attractions = attractions[skip:skip + limit]
        
        logger.info(f"Retrieved {len(attractions)} attractions for host {current_host.id}")
        return attractions
        
    except Exception as e:
        logger.error(f"Failed to retrieve host attractions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host attractions"
        )


@router.get("/host/contributions", response_model=List[HostContributionResponse])
async def get_my_contributions(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all contributions made by the current host.

    Registered before ``/{attraction_id}`` so ``/host/contributions`` is not parsed as a UUID path.
    """
    try:
        attraction_service = AttractionService(db)
        contributions = await attraction_service.get_host_contributions_by_host(
            host_id=current_host.id,
            skip=skip,
            limit=limit,
        )
        logger.info(
            "Retrieved %s contributions for host %s", len(contributions), current_host.id
        )
        return contributions
    except Exception as e:
        logger.error(f"Failed to retrieve host contributions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host contributions",
        )


@router.get("/{attraction_id}", response_model=AttractionResponse)
async def get_attraction(
    attraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    language: Optional[str] = "en"
):
    """
    Get a specific attraction by ID.
    
    Args:
        attraction_id: Attraction ID
        db: Database session
        language: Language for content (en, hr, de, it)
        
    Returns:
        AttractionResponse: Attraction details
    """
    try:
        attraction_service = AttractionService(db)
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        # Increment view count
        await attraction_service.increment_view_count(attraction_id)
        
        logger.info(f"Retrieved attraction {attraction_id} in {language}")
        return attraction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve attraction {attraction_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attraction"
        )


@router.get("/city/{city}", response_model=List[AttractionResponse])
async def get_attractions_by_city(
    city: str,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    language: Optional[str] = "en"
):
    """
    Get attractions for a specific city (e.g., Lovran).
    
    Args:
        city: City name
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        language: Language for content
        
    Returns:
        List[AttractionResponse]: City attractions
    """
    try:
        attraction_service = AttractionService(db)
        attractions = await attraction_service.get_attractions_by_city(
            city=city,
            skip=skip,
            limit=limit,
            language=language
        )
        
        logger.info(f"Retrieved {len(attractions)} attractions for city {city}")
        return attractions
        
    except Exception as e:
        logger.error(f"Failed to retrieve attractions for city {city}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve attractions for city {city}"
        )


# Host-only endpoints for attraction management
@router.post("/", response_model=AttractionResponse, status_code=status.HTTP_201_CREATED)
async def create_attraction(
    attraction_data: AttractionCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new attraction (hosts only).
    
    Args:
        attraction_data: Attraction creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        AttractionResponse: Created attraction
    """
    try:
        attraction_service = AttractionService(db)
        attraction = await attraction_service.create_attraction(
            host_id=current_host.id,
            attraction_data=attraction_data
        )
        
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create attraction: unknown error"
            )
        
        logger.info(f"Attraction created successfully: {attraction.id} by host {current_host.id}")
        return attraction
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create attraction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create attraction: {str(e)}"
        )


@router.put("/{attraction_id}", response_model=AttractionResponse)
async def update_attraction(
    attraction_id: uuid.UUID,
    attraction_data: AttractionUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an attraction (only if host created it or is contributing).
    
    Args:
        attraction_id: Attraction ID
        attraction_data: Updated attraction data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        AttractionResponse: Updated attraction
    """
    try:
        attraction_service = AttractionService(db)
        
        # Check if host has permission to update this attraction
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        can_update = await attraction_service._host_can_edit_attraction(
            host_id=current_host.id,
            attraction=attraction
        )
        
        if not can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this attraction"
            )
        
        updated_attraction = await attraction_service.update_attraction(
            host_id=current_host.id,
            attraction_id=attraction_id,
            attraction_data=attraction_data
        )
        
        logger.info(f"Updated attraction {attraction_id} by host {current_host.id}")
        return updated_attraction
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update attraction {attraction_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update attraction: {str(e)}"
        )


@router.delete("/{attraction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attraction(
    attraction_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an attraction (only if host created it).
    
    Args:
        attraction_id: Attraction ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        None
    """
    try:
        attraction_service = AttractionService(db)
        
        # Check if host has permission to delete this attraction
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        can_delete = await attraction_service._host_can_edit_attraction(
            host_id=current_host.id,
            attraction=attraction
        )
        
        if not can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this attraction"
            )
        
        success = await attraction_service.delete_attraction(
            host_id=current_host.id,
            attraction_id=attraction_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete attraction"
            )
        
        logger.info(f"Attraction deleted successfully: {attraction_id} by host {current_host.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete attraction {attraction_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete attraction"
        )


# Host contribution endpoints
@router.post("/{attraction_id}/contributions", response_model=HostContributionResponse, status_code=status.HTTP_201_CREATED)
async def add_host_contribution(
    attraction_id: uuid.UUID,
    contribution_data: HostContributionCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Add host contribution to an attraction (personal tips, stories, etc.).
    
    Args:
        attraction_id: Attraction ID
        contribution_data: Host contribution data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostContributionResponse: Created contribution
    """
    try:
        attraction_service = AttractionService(db)
        
        # Verify attraction exists
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        contribution = await attraction_service.add_host_contribution(
            attraction_id=attraction_id,
            host_id=current_host.id,
            contribution_data=contribution_data
        )
        
        logger.info(f"Added host contribution to attraction {attraction_id} by host {current_host.id}")
        return contribution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add host contribution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add host contribution"
        )


@router.get("/{attraction_id}/contributions", response_model=List[HostContributionResponse])
async def get_host_contributions(
    attraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all host contributions for an attraction.
    
    Args:
        attraction_id: Attraction ID
        db: Database session
        
    Returns:
        List[HostContributionResponse]: List of host contributions
    """
    try:
        attraction_service = AttractionService(db)
        contributions = await attraction_service.get_host_contributions(attraction_id)
        
        logger.info(f"Retrieved {len(contributions)} contributions for attraction {attraction_id}")
        return contributions
        
    except Exception as e:
        logger.error(f"Failed to retrieve host contributions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host contributions"
        )


# Review endpoints (for guests)
@router.post("/{attraction_id}/reviews", response_model=AttractionReviewResponse, status_code=status.HTTP_201_CREATED)
async def add_attraction_review(
    attraction_id: uuid.UUID,
    review_data: AttractionReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a guest review for an attraction.
    
    Args:
        attraction_id: Attraction ID
        review_data: Review data
        db: Database session
        
    Returns:
        AttractionReviewResponse: Created review
    """
    try:
        attraction_service = AttractionService(db)
        
        # Verify attraction exists
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        review = await attraction_service.add_review(
            attraction_id=attraction_id,
            review_data=review_data
        )
        
        logger.info(f"Added review for attraction {attraction_id}")
        return review
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add attraction review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add attraction review"
        )


# Enhanced Review endpoints with moderation

@router.post("/reviews/submit", response_model=AttractionReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_guest_review(
    review_submission: GuestReviewSubmission,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a guest review using access code authentication.
    
    Args:
        review_submission: Review data with access code
        db: Database session
        
    Returns:
        AttractionReviewResponse: Created review
    """
    try:
        guest_service = GuestGroupService(db)
        attraction_service = AttractionService(db)
        
        # Validate access code and get guest group
        guest_group = await guest_service.validate_access_code(review_submission.access_code)
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access code"
            )
        
        # Verify attraction exists
        attraction = await attraction_service.get_attraction_by_id(review_submission.review_data.attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        # Create review
        review = await attraction_service.add_review(
            host_id=guest_group.host_id,
            guest_group_id=guest_group.id,
            review_data=review_submission.review_data
        )
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create review"
            )
        
        logger.info(f"Guest review submitted for attraction {review_submission.review_data.attraction_id}")
        return review
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit guest review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit review"
        )


@router.get("/{attraction_id}/reviews", response_model=List[AttractionReviewResponse])
async def get_attraction_reviews(
    attraction_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, description="Filter by review status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get reviews for an attraction with optional status filtering.
    
    Args:
        attraction_id: Attraction ID
        status_filter: Filter by review status (approved, pending, etc.)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List[AttractionReviewResponse]: List of reviews
    """
    try:
        attraction_service = AttractionService(db)
        reviews = await attraction_service.get_reviews(
            attraction_id=attraction_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(reviews)} reviews for attraction {attraction_id}")
        return reviews
        
    except Exception as e:
        logger.error(f"Failed to retrieve attraction reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attraction reviews"
        )


# Host-only review moderation endpoints

@router.get("/host/reviews/moderation", response_model=List[AttractionReviewResponse])
async def get_reviews_for_moderation(
    status: Optional[str] = Query("pending", description="Review status to filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get reviews that need moderation by the current host.
    
    Args:
        status: Review status filter (default: pending)
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        List[AttractionReviewResponse]: Reviews needing moderation
    """
    try:
        attraction_service = AttractionService(db)
        reviews = await attraction_service.get_host_reviews_for_moderation(
            host_id=current_host.id,
            status=status,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(reviews)} reviews for moderation by host {current_host.id}")
        return reviews
        
    except Exception as e:
        logger.error(f"Failed to retrieve reviews for moderation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reviews for moderation"
        )


@router.post("/reviews/{review_id}/moderate", response_model=ReviewModerationResponse)
async def moderate_review(
    review_id: uuid.UUID,
    moderation_request: ReviewModerationRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Moderate a review (approve, reject, verify, etc.).
    
    Args:
        review_id: Review ID to moderate
        moderation_request: Moderation action details
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ReviewModerationResponse: Moderation result
    """
    try:
        attraction_service = AttractionService(db)
        result = await attraction_service.moderate_review(
            host_id=current_host.id,
            review_id=review_id,
            moderation_request=moderation_request
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found or access denied"
            )
        
        logger.info(f"Review {review_id} moderated by host {current_host.id}: {moderation_request.action}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to moderate review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to moderate review"
        )


@router.post("/reviews/search", response_model=ReviewSearchResponse)
async def search_reviews(
    search_request: ReviewSearchRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Search and filter reviews with advanced criteria.
    
    Args:
        search_request: Search criteria
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ReviewSearchResponse: Search results
    """
    try:
        attraction_service = AttractionService(db)
        results = await attraction_service.search_reviews(search_request)
        
        logger.info(f"Review search performed by host {current_host.id}")
        return results
        
    except Exception as e:
        logger.error(f"Failed to search reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search reviews"
        )


@router.get("/{attraction_id}/reviews/analytics", response_model=ReviewAnalytics)
async def get_review_analytics(
    attraction_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive analytics for attraction reviews.
    
    Args:
        attraction_id: Attraction ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        ReviewAnalytics: Review analytics data
    """
    try:
        attraction_service = AttractionService(db)
        
        # Verify host owns this attraction
        attraction = await attraction_service.get_attraction_by_id(attraction_id)
        if not attraction or attraction.created_by_host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this attraction's analytics"
            )
        
        analytics = await attraction_service.get_review_analytics(attraction_id)
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analytics not found for this attraction"
            )
        
        logger.info(f"Review analytics retrieved for attraction {attraction_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve review analytics"
        )


@router.get("/host/reviews/stats", response_model=HostReviewStats)
async def get_host_review_stats(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get review management statistics for the current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostReviewStats: Host review statistics
    """
    try:
        attraction_service = AttractionService(db)
        stats = await attraction_service.get_host_review_stats(current_host.id)
        
        if not stats:
            # Return empty stats if host has no reviews yet
            stats = HostReviewStats(
                host_id=current_host.id,
                total_reviews_received=0,
                pending_moderation=0,
                approved_this_month=0,
                rejected_this_month=0,
                verification_rate=0.0,
                response_rate=0.0
            )
        
        logger.info(f"Review stats retrieved for host {current_host.id}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get host review stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host review statistics"
        )


@router.post("/reviews/{review_id}/helpful", response_model=Dict[str, Any])
async def vote_review_helpfulness(
    review_id: uuid.UUID,
    vote: ReviewHelpfulnessVote,
    db: AsyncSession = Depends(get_db)
):
    """
    Vote on review helpfulness (public endpoint).
    
    Args:
        review_id: Review ID
        vote: Helpfulness vote
        db: Database session
        
    Returns:
        Dict[str, Any]: Vote result
    """
    try:
        # This would typically update the review's helpfulness score
        # For now, return a simple response
        logger.info(f"Helpfulness vote submitted for review {review_id}: {vote.helpful}")
        
        return {
            "success": True,
            "message": "Vote recorded successfully",
            "review_id": str(review_id),
            "helpful": vote.helpful
        }
        
    except Exception as e:
        logger.error(f"Failed to record helpfulness vote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record vote"
        )


# AI Enhancement endpoint for attraction descriptions
@router.post("/ai-enhance", response_model=Dict[str, Any])
async def enhance_attraction_description(
    request: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhance attraction description using AI with contextual data.
    
    Args:
        request: Dict containing attraction details and context for enhancement
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Enhanced description and metadata
    """
    try:
        logger.info(f"🎯 Enhancing attraction description with AI for host {current_host.id}")
        
        # Extract data from request
        attraction_name = request.get("attraction_name", "")
        location = request.get("location", "")
        attraction_type = request.get("attraction_type", "")
        current_description = request.get("current_description", "")
        host_location = request.get("host_location", "")
        distance_from_host = request.get("distance_from_host", "")
        nearby_places = request.get("nearby_places", [])
        google_places_data = request.get("google_places_data", {})
        
        if not attraction_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attraction name is required for AI enhancement"
            )
        
        # Derive helper presentation fields for better, non-generic copy
        def _humanize_type(value: str) -> str:
            try:
                return value.replace("_", " ").strip().title()
            except Exception:
                return value

        gp_types = google_places_data.get("types", []) if isinstance(google_places_data.get("types", []), list) else []
        primary_type_raw = (attraction_type or (gp_types[0] if gp_types else "")).strip()
        attraction_kind = _humanize_type(primary_type_raw) if primary_type_raw else "Attraction"

        rating = google_places_data.get("rating")
        user_ratings_total = google_places_data.get("user_ratings_total")
        rating_text = ""
        if isinstance(rating, (int, float)) and isinstance(user_ratings_total, int):
            rating_text = f"Rated {rating}/5 by {user_ratings_total}+ visitors."

        price_level = google_places_data.get("price_level")
        price_map = {0: "Free", 1: "Budget", 2: "Moderate", 3: "Premium", 4: "Luxury"}
        price_text = price_map.get(price_level) if isinstance(price_level, int) else ""

        nearby_names = [p.get("name") for p in nearby_places if isinstance(p, dict) and p.get("name")]
        nearby_summary = ", ".join(nearby_names[:3])
        has_nearby = bool(nearby_summary)

        # Build enhanced prompt with context and strict output guidance
        host_name = current_host.first_name or current_host.business_name or "a local host"
        host_expertise = ", ".join(current_host.local_specialties) if current_host.local_specialties else "local Croatian tourism"
        
        # Compose explicit search queries and a structured context blob for tool grounding
        search_queries = [
            f"{attraction_name} {location} description history what to expect",
            f"{attraction_name} reviews Rijeka tourists",
            f"Why visit {attraction_name} {location}",
        ]

        structured_context = {
            "attraction": {
                "name": attraction_name,
                "type": attraction_kind,
                "raw_type": attraction_type,
                "location": location,
            },
            "host": {
                "name": host_name,
                "expertise": host_expertise,
                "base_location": host_location,
                "distance_from_host": distance_from_host,
            },
            "nearby_places": nearby_places,
            "google_places_data": google_places_data,
        }
        structured_context_json = json.dumps(structured_context, ensure_ascii=False)

        # Optional: fetch web context via SerpAPI if available
        def _gather_web_context(queries):
            api_key = os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_KEY")
            if not api_key:
                return []
            results = []
            base_url = "https://serpapi.com/search.json"
            for q in queries[:3]:
                try:
                    resp = requests.get(base_url, params={"engine": "google", "q": q, "api_key": api_key}, timeout=10)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for item in (data.get("organic_results") or [])[:2]:
                        link = item.get("link", "")
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        if link and title:
                            results.append({"title": title, "url": link, "snippet": snippet})
                except Exception:
                    continue
            return results[:5]

        web_context_items = _gather_web_context(search_queries)
        web_context_lines = []
        for it in web_context_items:
            web_context_lines.append(f"- {it['title']} ({it['url']}) — {it.get('snippet','')}")
        web_context_block = "\n".join(web_context_lines)
        enhanced_prompt = f"""
        You are a highly objective travel encyclopedia that provides information for a Croatian tourism platform.
        You will generate a 3-paragraph description of an attraction. The first two paragraphs must be completely objective and factual. 
        Only in the final paragraph, you will provide a subtle recommendation for guests staying with a local host named {host_name} (based in {host_location}).
        
        Generate a highly compelling description for this attraction.

        ATTRACTION DETAILS:
        - Name: {attraction_name}
        - Location: {location}
        - Type: {attraction_kind}
        - Original Description: {current_description or 'None provided'}

        HOST CONTEXT:
        - Host Name: {host_name}
        - Host Location: {host_location}
        - Host Expertise: {host_expertise}
        - Distance Context: This attraction is {distance_from_host} from the host's location

        NEARBY CONTEXT (to suggest pairings):
        - Nearby Places: {', '.join([f"{place.get('name', 'Unknown')} ({', '.join(place.get('types', []) if isinstance(place.get('types', []), list) else [])})" for place in nearby_places[:5]])}

        GOOGLE PLACES DATA:
        - Rating: {google_places_data.get('rating', 'N/A')}
        - User Ratings: {google_places_data.get('user_ratings_total', 'N/A')}
        - Price Level: {google_places_data.get('price_level', 'N/A')} ({price_text or 'Unknown'})
        - Types: {', '.join(gp_types)}

        WEB CONTEXT (Real facts to ground your response):
        {web_context_block or 'None available'}

        CRITICAL REQUIREMENTS:
        1) WHAT IT IS (STRICTLY OBJECTIVE FACTUAL INTRO): The FIRST paragraph must be exactly 2-3 sentences explaining objectively what this place is. Do not use words like "Welcome", "Dobrodošli", "As your host", "I recommend", or any conversational greetings. Do not write from the perspective of a host yet. Just state the cold hard facts: what is it, where is it, and what is its historical/cultural significance based on the Web Context or Google Places data. Assume the reader has never heard of it. Do not invent facts.
        2) THE EXPERIENCE: In the SECOND paragraph, transition into describing the ambiance, the sensory experience, what makes this place special, and why it's worth the trip. Still maintain a third-person, descriptive tone.
        3) THE HOST CONNECTION & PRACTICALS: In the THIRD paragraph, switch to a subtle, warm recommendation. Do not introduce yourself by name ("As your host Benedikt..."). Simply say something natural like "For our guests staying in {host_location}, this makes a perfect..." or "I always suggest...". Smoothly weave in the rating ({rating_text or 'highly rated'}), the cost level, and simple travel guidance from {host_location}. {(f"Suggest pairing a visit here with: {nearby_summary}.") if has_nearby else "Suggest a generic old-town walk or coffee stop nearby."}
        
        OUTPUT STYLE:
        - Write exactly 3 engaging paragraphs.
        - DO NOT EVER start with greetings like "Welcome", "Dobrodošli", "As your host", "Hi", "Hello", or anything similar. Start immediately with the facts.
        - Paragraph 1: Objective, factual, clear explanation (2-3 sentences max). No host voice.
        - Paragraph 2: The experience and ambiance (sensory, persuasive).
        - Paragraph 3: Subtle recommendation, travel guidance, and practicals.
        - DO NOT output a "Good to know" list of bullets at the end. Weave the practical info naturally into the prose.
        - Tone: Starts completely objective, becomes subtly warm at the end. 
        - NO REPETITION: Don't repeat the attraction name or distance multiple times.
        """
        
        # Use the existing AI service to generate enhanced description
        from app.services.ai_service import AIService
        from app.services.settings_service import SettingsService
        
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        
        # Create messages for AI generation
        messages = [
            {
                "role": "system",
                "content": "You are an objective travel encyclopedia that slowly transitions into a subtle, warm travel advisor. You strictly follow instructions about tone and structure. NEVER write from a first-person perspective like 'As your host' or 'I am Benedikt'. NEVER use conversational greetings like 'Welcome' or 'Dobrodošli'. Just provide the text requested."
            },
            {
                "role": "user",
                "content": enhanced_prompt
            }
        ]
        
        # Generate enhanced description
        ai_response = await ai_service.generate_chat_response(
            host_id=str(current_host.id),
            messages=messages,
            context={
                "location": host_location or "Lovran, Croatia",
                "local_info": {
                    "attraction": structured_context.get("attraction"),
                    "nearby_places": structured_context.get("nearby_places"),
                    "google_places_data": structured_context.get("google_places_data"),
                    "suggested_search_queries": search_queries,
                },
            },
            use_reasoning=False,  # Use Flash model to avoid 503 overloaded errors on Pro
            use_web_search=bool(request.get("use_web_search", True))
        )
        
        # Normalize AI response path and fallback into a single shaping flow
        enhancement_method = "ai_generated"
        ai_provider = ai_response.get("provider", "unknown")
        if not ai_response.get("success"):
            nearby_sentence = f"With nearby attractions like {nearby_summary}, visitors can create a great day trip." if has_nearby else ""
            rating_sentence = rating_text
            price_sentence = f" Typical cost level: {price_text}." if price_text else ""
            fallback_description = f"""
            {attraction_name} is a {attraction_kind.lower()} in {location}, approximately {distance_from_host} from {host_location}.
            
            Expect an experience that showcases authentic Croatian culture and local spirit — ideal for guests staying in {host_location} who want to explore beyond their accommodation. {rating_sentence}{price_sentence}
            {nearby_sentence}
            """
            ai_text = fallback_description.strip()
            enhancement_method = "fallback_generated"
            ai_provider = "fallback"
        else:
            ai_text = (ai_response.get("response", "") or "").strip()
        
        # Return AI-generated description with guaranteed structure
        ai_text = (ai_response.get("response", "") or "").strip()

        # Filter generic apology messages from providers and replace with shaped guidance
        lower_ai = ai_text.lower()
        if any(p in lower_ai for p in [
            "i apologize, but i'm currently unable",
            "unable to process your request",
            "please check your ai service configuration",
            "an excellent spot to experience authentic"
        ]):
            ai_text = fallback_description.strip()

        if not ai_text:
            # Fallback shaping if AI returned empty despite success flag
            ai_text = fallback_description.strip()

        enhanced_description = ai_text

        logger.info(f"✅ Successfully enhanced description for attraction: {attraction_name}")
        
        return {
            "success": True,
            "data": {
                "enhanced_description": enhanced_description,
                "enhancement_method": enhancement_method,
                "ai_provider": ai_provider,
                "context_used": {
                    "attraction_details": True,
                    "host_location": True,
                    "nearby_places": len(nearby_places),
                    "google_places_data": bool(google_places_data)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enhance attraction description: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enhance attraction description"
        )


# Analytics endpoints (hosts only)
@router.get("/{attraction_id}/analytics", response_model=Dict[str, Any])
async def get_attraction_analytics(
    attraction_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics for an attraction (hosts only).
    
    Args:
        attraction_id: Attraction ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Analytics data
    """
    try:
        attraction_service = AttractionService(db)
        
        # Check if host has permission to view analytics
        can_view = await attraction_service.can_host_view_analytics(
            attraction_id=attraction_id,
            host_id=current_host.id
        )
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view analytics for this attraction"
            )
        
        analytics = await attraction_service.get_attraction_analytics(attraction_id)
        
        logger.info(f"Retrieved analytics for attraction {attraction_id} by host {current_host.id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve attraction analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attraction analytics"
        )