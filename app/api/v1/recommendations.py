"""
Recommendation API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for AI-powered personalized recommendations
based on guest preferences, host insights, and Croatian tourism data.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_host
from app.services.recommendation_service import RecommendationService
from app.services.host_service import HostService
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group
from app.services.ai_service import AIService
from app.models.recommendation_api import (
    RecommendationAlgorithmTestResponse,
    RecommendationPerformanceMetricsResponse,
)
from app.models.recommendation import (
    RecommendationRequestAPI,
    RecommendationResponse,
    ExplorerRecommendationPublicResponse,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
    GuestRecommendationFeedbackResponse,
    RecommendationAnalytics,
    GuestGroupRecommendationAnalytics,
    WeatherContext,
    RecommendationBatch,
    GuestRecommendationBatch,
    GuestRecommendationItem,
)
from app.models.host import Host
from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)
router = APIRouter()


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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access code"
        )
    return guest_group


def _feedback_for_guest(
    feedback: RecommendationFeedbackResponse,
) -> GuestRecommendationFeedbackResponse:
    """Strip guest_group_id, lifecycle timestamps, and scrub contact patterns from feedback payloads."""
    from app.services.host_offerings_for_guest import scrub_contact_from_text, _scrub_safe_value

    data = feedback.model_dump(exclude={"guest_group_id", "created_at"})
    for key in ("feedback_text", "improvement_suggestions"):
        if data.get(key):
            data[key] = scrub_contact_from_text(data[key])
    if data.get("helpful_factors"):
        data["helpful_factors"] = _scrub_safe_value(data["helpful_factors"])
    return GuestRecommendationFeedbackResponse.model_validate(data)


# Guest endpoints (using access code)
@router.post("/guest/{access_code}", response_model=GuestRecommendationBatch)
async def get_guest_recommendations(
    access_code: str,
    request_data: RecommendationRequestAPI,
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized recommendations for a guest group.
    
    Args:
        access_code: Guest group access code
        request_data: Recommendation request parameters
        db: Database session
        
    Returns:
        RecommendationBatch: Personalized recommendations with explanations
    """
    try:
        # Validate access code and get guest group
        guest_group = await validate_access_code(access_code, db)
        guest_group_id = guest_group.id
        
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        batch = await recommendation_service.get_personalized_recommendations(
            guest_group_id=guest_group_id,
            request_data=request_data
        )
        enriched = await recommendation_service.enrich_batch_for_guest(
            batch, guest_group_id, viewer_host_id=guest_group.host_id
        )

        logger.info(
            "Generated %s recommendations for guest group %s",
            len(enriched.recommendations),
            guest_group_id,
        )
        return enriched
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to generate guest recommendations: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@router.post("/guest/{access_code}/feedback", response_model=GuestRecommendationFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_recommendation_feedback(
    access_code: str,
    feedback_data: RecommendationFeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback for a recommendation.
    
    Args:
        access_code: Guest group access code
        feedback_data: Recommendation feedback
        db: Database session
        
    Returns:
        RecommendationFeedbackResponse: Submitted feedback
    """
    try:
        # Validate access code and get guest group
        guest_group = await validate_access_code(access_code, db)
        
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        feedback = await recommendation_service.submit_feedback(
            guest_group_id=guest_group.id,
            feedback_data=feedback_data
        )
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found for this guest group",
            )

        logger.info(f"Feedback submitted for guest group {guest_group.id}")
        return _feedback_for_guest(feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit recommendation feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/guest/{access_code}/history", response_model=List[GuestRecommendationItem])
async def get_recommendation_history(
    access_code: str,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    Get recommendation history for a guest group.
    
    Args:
        access_code: Guest group access code
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[RecommendationResponse]: Recommendation history
    """
    try:
        # Validate access code and get guest group
        guest_group = await validate_access_code(access_code, db)
        
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        history = await recommendation_service.get_recommendation_history(
            guest_group_id=guest_group.id,
            skip=skip,
            limit=limit
        )
        enriched = await recommendation_service.enrich_list_for_guest(
            history, guest_group.id, viewer_host_id=guest_group.host_id
        )

        logger.info(f"Retrieved {len(enriched)} recommendations history for guest group {guest_group.id}")
        return enriched
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve recommendation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation history"
        )


# Host endpoints
@router.post("/host/generate", response_model=RecommendationBatch)
async def generate_host_recommendations(
    request_data: RecommendationRequestAPI,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate recommendations for host's guest groups (host preview).
    
    Args:
        request_data: Recommendation request parameters
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        RecommendationBatch: Generated recommendations
    """
    try:
        if not request_data.guest_group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="guest_group_id is required",
            )

        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)

        guest_service = GuestGroupService(db)
        guest_group = await guest_service.get_guest_group_by_id(request_data.guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group",
            )

        recommendations = await recommendation_service.get_personalized_recommendations(
            guest_group_id=request_data.guest_group_id,
            request_data=request_data
        )
        
        logger.info(f"Host {current_host.id} generated {len(recommendations.recommendations)} recommendations")
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate host recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@router.get("/host/analytics", response_model=RecommendationAnalytics)
async def get_host_recommendation_analytics(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get recommendation analytics for the host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        days: Number of days to analyze
        
    Returns:
        RecommendationAnalytics: Analytics data
    """
    try:
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        analytics = await recommendation_service.get_host_analytics(
            host_id=current_host.id,
            days=days
        )
        
        logger.info(f"Retrieved recommendation analytics for host {current_host.id}")
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to retrieve host recommendation analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation analytics"
        )


@router.get("/host/guest-groups/{guest_group_id}/analytics", response_model=GuestGroupRecommendationAnalytics)
async def get_guest_group_analytics(
    guest_group_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendation analytics for a specific guest group.
    
    Args:
        guest_group_id: Guest group ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Guest group analytics
    """
    try:
        # Verify guest group belongs to this host
        guest_service = GuestGroupService(db)
        guest_group = await guest_service.get_guest_group_by_id(guest_group_id)
        if not guest_group or not host_owns_guest_group(guest_group, current_host.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this guest group"
            )

        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        analytics = await recommendation_service.get_guest_group_analytics(guest_group_id)
        
        logger.info(f"Retrieved guest group analytics for {guest_group_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve guest group analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve guest group analytics"
        )


# Weather-based recommendations
@router.get("/weather/{city}", response_model=List[ExplorerRecommendationPublicResponse])
async def get_weather_based_recommendations(
    city: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, description="Number of recommendations")
):
    """
    Get weather-based recommendations for a city.
    
    Args:
        city: City name (e.g., 'Lovran')
        db: Database session
        limit: Number of recommendations to return
        
    Returns:
        List[RecommendationResponse]: Weather-appropriate recommendations
    """
    try:
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        recommendations = await recommendation_service.get_weather_based_recommendations(
            city=city,
            limit=limit
        )
        
        logger.info(f"Generated {len(recommendations)} weather-based recommendations for {city}")
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate weather-based recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate weather-based recommendations"
        )


# Seasonal recommendations
@router.get("/seasonal/{season}", response_model=List[ExplorerRecommendationPublicResponse])
async def get_seasonal_recommendations(
    season: str,
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = None,
    limit: int = Query(20, description="Number of recommendations")
):
    """
    Get seasonal recommendations.
    
    Args:
        season: Season (spring, summer, autumn, winter)
        db: Database session
        city: Optional city filter
        limit: Number of recommendations to return
        
    Returns:
        List[RecommendationResponse]: Seasonal recommendations
    """
    try:
        if season not in ["spring", "summer", "autumn", "winter"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid season. Must be one of: spring, summer, autumn, winter"
            )
        
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        recommendations = await recommendation_service.get_seasonal_recommendations(
            season=season,
            city=city,
            limit=limit
        )
        
        logger.info(f"Generated {len(recommendations)} seasonal recommendations for {season}")
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate seasonal recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate seasonal recommendations"
        )


# Algorithm testing endpoints (hosts only)
@router.post("/test/algorithm", response_model=RecommendationAlgorithmTestResponse)
async def test_recommendation_algorithm(
    test_data: RecommendationRequestAPI,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Test recommendation algorithm with different parameters (hosts only).
    
    Args:
        test_data: Test recommendation parameters
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Algorithm test results
    """
    try:
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        test_results = await recommendation_service.test_algorithm(
            test_data=test_data,
            host_id=current_host.id
        )
        
        logger.info(f"Algorithm test completed for host {current_host.id}")
        return test_results
        
    except Exception as e:
        logger.error(f"Failed to test recommendation algorithm: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test recommendation algorithm"
        )


@router.get("/performance/metrics", response_model=RecommendationPerformanceMetricsResponse)
async def get_performance_metrics(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendation system performance metrics (hosts only).
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Performance metrics
    """
    try:
        ai_service = AIService()
        recommendation_service = RecommendationService(db, ai_service)
        metrics = await recommendation_service.get_performance_metrics(
            host_id=current_host.id
        )
        
        logger.info(f"Retrieved performance metrics for host {current_host.id}")
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to retrieve performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        ) 