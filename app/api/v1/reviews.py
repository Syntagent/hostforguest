"""
Review API endpoints for guest reviews and feedback.

Provides REST API for review management including
sentiment analysis, response generation, and public review display.
"""

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.review_service import ReviewService
from app.services.host_service import HostService
from app.services.guest_group_service import GuestGroupService
from app.services.attraction_service import AttractionService

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class RequestReviewRequest(BaseModel):
    """Request for sending review request."""
    guest_group_id: str
    attraction_id: Optional[str] = None


class AnalyzeSentimentRequest(BaseModel):
    """Request for sentiment analysis."""
    review_text: str


class AnalyzeSentimentResponse(BaseModel):
    """Response with sentiment analysis."""
    sentiment: str
    score: float
    positive_keywords: int
    negative_keywords: int


class GenerateResponseRequest(BaseModel):
    """Request for generating review response."""
    review_id: str
    language: str = "en"


@router.post("/request")
async def request_review(
    request: RequestReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send automated review request to guests.
    
    Args:
        request: Review request data
        db: Database session
        
    Returns:
        Success status
    """
    try:
        review_service = ReviewService(db)
        host_service = HostService(db)
        guest_group_service = GuestGroupService(db)
        attraction_service = AttractionService(db)
        
        # Get guest group
        guest_group = await guest_group_service.get_guest_group_by_id(uuid.UUID(request.guest_group_id))
        if not guest_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )
        
        # Get host
        host = await host_service.get_by_id(guest_group.host_id)
        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found"
            )
        
        # Get attraction if provided
        attraction = None
        if request.attraction_id:
            attraction = await attraction_service.get_by_id(uuid.UUID(request.attraction_id))
        
        # Request review
        success = await review_service.request_review(host, guest_group, attraction)
        
        if success:
            return {"success": True, "message": "Review request sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send review request"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request review: {str(e)}"
        )


@router.post("/analyze-sentiment", response_model=AnalyzeSentimentResponse)
async def analyze_sentiment(
    request: AnalyzeSentimentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze sentiment of review text.
    
    Args:
        request: Sentiment analysis request
        db: Database session
        
    Returns:
        Sentiment analysis results
    """
    try:
        review_service = ReviewService(db)
        sentiment = await review_service.analyze_review_sentiment(request.review_text)
        
        return AnalyzeSentimentResponse(
            sentiment=sentiment["sentiment"],
            score=sentiment["score"],
            positive_keywords=sentiment["positive_keywords"],
            negative_keywords=sentiment["negative_keywords"]
        )
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze sentiment: {str(e)}"
        )


@router.post("/generate-response")
async def generate_review_response(
    request: GenerateResponseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate professional review response template.
    
    Args:
        request: Response generation request
        db: Database session
        
    Returns:
        Generated response text
    """
    try:
        from app.models.attraction import AttractionReview
        
        review_service = ReviewService(db)
        host_service = HostService(db)
        
        # Get review
        stmt = select(AttractionReview).where(AttractionReview.id == uuid.UUID(request.review_id))
        result = await db.execute(stmt)
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Get host (from attraction)
        if review.attraction:
            host = await host_service.get_by_id(review.attraction.created_by_host_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host not found for review"
            )
        
        # Generate response
        response = await review_service.generate_review_response(host, review, request.language)
        
        if response:
            return {"success": True, "response": response}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating review response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.get("/public")
async def get_public_reviews(
    attraction_id: Optional[str] = Query(None),
    host_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get public reviews for display.
    
    Args:
        attraction_id: Optional attraction ID to filter by
        host_id: Optional host ID to filter by
        limit: Maximum number of reviews
        db: Database session
        
    Returns:
        List of public reviews
    """
    try:
        review_service = ReviewService(db)
        
        reviews = await review_service.get_public_reviews(
            attraction_id=uuid.UUID(attraction_id) if attraction_id else None,
            host_id=uuid.UUID(host_id) if host_id else None,
            limit=limit
        )
        
        return {"reviews": reviews, "count": len(reviews)}
        
    except Exception as e:
        logger.error(f"Error getting public reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}"
        )


@router.post("/update-recommendations/{attraction_id}")
async def update_recommendations_from_reviews(
    attraction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Update recommendations based on review feedback.
    
    Args:
        attraction_id: Attraction ID
        db: Database session
        
    Returns:
        Success status
    """
    try:
        review_service = ReviewService(db)
        
        success = await review_service.update_recommendations_from_reviews(
            uuid.UUID(attraction_id)
        )
        
        if success:
            return {"success": True, "message": "Recommendations updated from reviews"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update recommendations"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update recommendations: {str(e)}"
        )

