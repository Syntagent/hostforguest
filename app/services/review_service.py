"""
Review and feedback service for guest reviews.

Provides review management including:
- Automated review requests
- Sentiment analysis
- Review response templates
- Review-based recommendations
- Public review display
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.models.attraction import Attraction, AttractionReview, ReviewStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.communication_service import CommunicationService
from app.services.content_generation_service import ContentGenerationService
from app.services.host_offerings_for_guest import scrub_contact_from_text
from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SentimentAnalysisResult(BaseModel):
    """Structured AI output for guest review sentiment."""

    sentiment: str = Field(description="positive, negative, or neutral")
    score: float = Field(ge=0.0, le=1.0, description="Sentiment score from 0 to 1")
    positive_keywords: int = Field(ge=0, description="Count of positive aspects or keywords")
    negative_keywords: int = Field(ge=0, description="Count of negative aspects or keywords")


class PublicReviewCardResponse(BaseModel):
    """Unauthenticated public review card — no guest or host PII."""

    id: str
    attraction_name: Optional[str] = None
    rating: int
    review_text: Optional[str] = None


class PublicReviewsListResponse(BaseModel):
    reviews: List[PublicReviewCardResponse]
    count: int


class ReviewService:
    """
    Service for managing guest reviews and feedback.
    
    Handles review requests, sentiment analysis, response generation,
    and review-based recommendation improvements.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the review service.
        
        Args:
            db: Database session
        """
        self.db = db
        settings_service = SettingsService(db)
        self._ai = AIServiceWithFallback(settings_service)
        self.content_service = ContentGenerationService(self._ai, settings_service)
        self.communication_service = CommunicationService(db)
    
    async def request_review(
        self,
        host: Host,
        guest_group: GuestGroup,
        attraction: Optional[Attraction] = None
    ) -> bool:
        """
        Send automated review request to guests.
        
        Args:
            host: Host instance
            guest_group: Guest group instance
            attraction: Optional specific attraction to review
            
        Returns:
            True if request sent successfully, False otherwise
        """
        try:
            # Generate review request email
            email_content = await self.content_service.generate_email_template(
                template_type="follow_up",
                host=host,
                guest_group={"group": guest_group},
                language=guest_group.preferred_language or "en"
            )
            
            # Add review-specific content
            review_prompt = f"""
            Please share your experience! Your feedback helps us improve recommendations
            for future guests. {f"We'd especially love to hear about {attraction.name}!" if attraction else ""}
            
            Review Link: [Review Link Here]
            """
            
            if email_content:
                email_content += "\n\n" + review_prompt
            
            # In production, would send via email service
            logger.info(f"Would send review request to {guest_group.lead_guest_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error requesting review: {e}")
            return False
    
    def _keyword_sentiment_analysis(self, review_text: str) -> Dict[str, Any]:
        """Deterministic keyword-based sentiment when AI is unavailable."""
        review_lower = review_text.lower()

        positive_keywords = [
            "excellent", "amazing", "wonderful", "great", "fantastic",
            "beautiful", "perfect", "loved", "enjoyed", "recommend",
        ]
        negative_keywords = [
            "disappointing", "poor", "bad", "terrible", "awful",
            "worst", "hated", "waste", "avoid",
        ]

        positive_count = sum(1 for word in positive_keywords if word in review_lower)
        negative_count = sum(1 for word in negative_keywords if word in review_lower)

        if positive_count > negative_count:
            sentiment = "positive"
            score = min(1.0, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            sentiment = "negative"
            score = max(0.0, 0.5 - (negative_count * 0.1))
        else:
            sentiment = "neutral"
            score = 0.5

        return {
            "sentiment": sentiment,
            "score": score,
            "positive_keywords": positive_count,
            "negative_keywords": negative_count,
        }

    async def _analyze_sentiment_with_ai(
        self,
        review_text: str,
        host_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """Use structured AI output for sentiment; returns None when AI fails."""
        try:
            res = await self._ai.generate_structured_response(
                str(host_id),
                [
                    {
                        "role": "user",
                        "content": (
                            "Analyze the sentiment of this guest review. "
                            "Return positive, negative, or neutral sentiment, a score from 0 to 1, "
                            "and counts of positive and negative keywords or themes.\n\n"
                            f"Review:\n{review_text}"
                        ),
                    }
                ],
                context={"task": "review_sentiment_analysis"},
                response_schema=SentimentAnalysisResult,
            )
            if res.get("success") and res.get("structured_data"):
                data = SentimentAnalysisResult.model_validate(res["structured_data"])
                sentiment = data.sentiment.lower().strip()
                if sentiment not in ("positive", "negative", "neutral"):
                    sentiment = "neutral"
                return {
                    "sentiment": sentiment,
                    "score": max(0.0, min(1.0, data.score)),
                    "positive_keywords": data.positive_keywords,
                    "negative_keywords": data.negative_keywords,
                }
        except Exception as e:
            logger.warning("AI sentiment analysis failed, using keyword fallback: %s", e)
        return None

    async def analyze_review_sentiment(
        self,
        review_text: str,
        host_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of a review.

        Uses structured AI output when host_id is provided; falls back to
        keyword counting when AI is unavailable or host_id is omitted.

        Args:
            review_text: Review text to analyze
            host_id: Optional host UUID for AI configuration

        Returns:
            Sentiment analysis results
        """
        try:
            if host_id:
                ai_result = await self._analyze_sentiment_with_ai(review_text, host_id)
                if ai_result:
                    return ai_result
            return self._keyword_sentiment_analysis(review_text)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return self._keyword_sentiment_analysis(review_text)
    
    async def generate_review_response(
        self,
        host: Host,
        review: AttractionReview,
        language: str = "en"
    ) -> Optional[str]:
        """
        Generate professional review response template.
        
        Args:
            host: Host instance
            review: Review to respond to
            language: Response language
            
        Returns:
            Generated response text or None
        """
        try:
            sentiment = await self.analyze_review_sentiment(review.review_text, host.id)
            
            if sentiment["sentiment"] == "positive":
                response_template = f"""
                Thank you so much for your wonderful review! We're delighted that you enjoyed
                {review.attraction.name if review.attraction else 'your experience'}. 
                Your feedback means a lot to us and helps us continue providing great experiences
                for our guests.
                
                We hope to welcome you back to {host.city} soon!
                
                Best regards,
                {host.name or 'Your Host'}
                """
            elif sentiment["sentiment"] == "negative":
                response_template = f"""
                Thank you for taking the time to share your feedback. We're sorry to hear that
                your experience wasn't what you expected. Your comments are valuable to us and
                help us improve.
                
                We'd love to discuss this further and make things right. Please feel free to
                contact us directly.
                
                Best regards,
                {host.name or 'Your Host'}
                """
            else:
                response_template = f"""
                Thank you for your feedback! We appreciate you taking the time to share your
                experience. Your comments help us improve our recommendations and services.
                
                Best regards,
                {host.name or 'Your Host'}
                """
            
            return response_template
            
        except Exception as e:
            logger.error(f"Error generating review response: {e}")
            return None
    
    async def get_public_reviews(
        self,
        attraction_id: Optional[uuid.UUID] = None,
        host_id: Optional[uuid.UUID] = None,
        limit: int = 20
    ) -> List[PublicReviewCardResponse]:
        """
        Get public reviews for display.
        
        Args:
            attraction_id: Optional attraction ID to filter by
            host_id: Optional host ID to filter by
            limit: Maximum number of reviews
            
        Returns:
            List of public review data
        """
        try:
            stmt = (
                select(AttractionReview, Attraction)
                .join(Attraction, AttractionReview.attraction_id == Attraction.id)
                .where(AttractionReview.status == ReviewStatus.APPROVED)
            )

            if attraction_id:
                stmt = stmt.where(AttractionReview.attraction_id == attraction_id)

            if host_id:
                stmt = stmt.where(Attraction.created_by_host_id == host_id)

            stmt = stmt.order_by(desc(AttractionReview.created_at))
            stmt = stmt.limit(limit)

            result = await self.db.execute(stmt)
            rows = result.all()

            public_reviews = []
            for review, attraction in rows:
                public_reviews.append(
                    PublicReviewCardResponse(
                        id=str(review.id),
                        attraction_name=scrub_contact_from_text(attraction.name),
                        rating=review.rating,
                        review_text=scrub_contact_from_text(review.review_text),
                    )
                )
            
            return public_reviews
            
        except Exception as e:
            logger.error(f"Error getting public reviews: {e}")
            return []
    
    async def update_recommendations_from_reviews(
        self,
        attraction_id: uuid.UUID
    ) -> bool:
        """
        Update recommendations based on review feedback.
        
        Args:
            attraction_id: Attraction ID
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get all reviews for attraction
            stmt = select(AttractionReview).where(
                and_(
                    AttractionReview.attraction_id == attraction_id,
                    AttractionReview.status == ReviewStatus.APPROVED
                )
            )
            
            result = await self.db.execute(stmt)
            reviews = result.scalars().all()
            
            if not reviews:
                return False

            attraction_stmt = select(Attraction).where(Attraction.id == attraction_id)
            attraction_result = await self.db.execute(attraction_stmt)
            attraction = attraction_result.scalar_one_or_none()
            host_id_for_ai = (
                attraction.created_by_host_id if attraction else None
            )

            # Analyze review patterns
            total_rating = sum(r.rating for r in reviews)
            avg_rating = total_rating / len(reviews)

            # Extract common themes from reviews
            common_themes = []
            for review in reviews:
                sentiment = await self.analyze_review_sentiment(
                    review.review_text, host_id_for_ai
                )
                if sentiment["sentiment"] == "positive":
                    # Extract positive aspects
                    common_themes.append("positive_feedback")
            
            # In production, would update attraction metadata or recommendation weights
            logger.info(f"Updated recommendations for attraction {attraction_id} based on {len(reviews)} reviews")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating recommendations from reviews: {e}")
            return False

