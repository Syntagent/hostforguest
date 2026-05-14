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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.models.attraction import Attraction, AttractionReview, ReviewStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.communication_service import CommunicationService
from app.services.content_generation_service import ContentGenerationService
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


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
        ai_service = AIService(settings_service)
        self.content_service = ContentGenerationService(ai_service, settings_service)
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
    
    async def analyze_review_sentiment(
        self,
        review_text: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of a review.
        
        Args:
            review_text: Review text to analyze
            
        Returns:
            Sentiment analysis results
        """
        try:
            # In production, would use AI service for sentiment analysis
            # For now, basic keyword-based analysis
            
            review_lower = review_text.lower()
            
            positive_keywords = [
                "excellent", "amazing", "wonderful", "great", "fantastic",
                "beautiful", "perfect", "loved", "enjoyed", "recommend"
            ]
            negative_keywords = [
                "disappointing", "poor", "bad", "terrible", "awful",
                "worst", "hated", "waste", "avoid"
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
                "negative_keywords": negative_count
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "positive_keywords": 0,
                "negative_keywords": 0
            }
    
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
            sentiment = await self.analyze_review_sentiment(review.review_text)
            
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
    ) -> List[Dict[str, Any]]:
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
            stmt = select(AttractionReview).where(
                AttractionReview.status == ReviewStatus.APPROVED
            )
            
            if attraction_id:
                stmt = stmt.where(AttractionReview.attraction_id == attraction_id)
            
            if host_id:
                # Filter by host's attractions
                stmt = stmt.join(Attraction).where(
                    Attraction.created_by_host_id == host_id
                )
            
            stmt = stmt.order_by(desc(AttractionReview.created_at))
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            reviews = result.scalars().all()
            
            public_reviews = []
            for review in reviews:
                sentiment = await self.analyze_review_sentiment(review.review_text)
                
                public_reviews.append({
                    "id": str(review.id),
                    "attraction_name": review.attraction.name if review.attraction else None,
                    "rating": review.rating,
                    "review_text": review.review_text,
                    "guest_name": review.guest_name or "Anonymous",
                    "created_at": review.created_at.isoformat() if review.created_at else None,
                    "sentiment": sentiment["sentiment"],
                    "sentiment_score": sentiment["score"]
                })
            
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
            
            # Analyze review patterns
            total_rating = sum(r.rating for r in reviews)
            avg_rating = total_rating / len(reviews)
            
            # Extract common themes from reviews
            common_themes = []
            for review in reviews:
                sentiment = await self.analyze_review_sentiment(review.review_text)
                if sentiment["sentiment"] == "positive":
                    # Extract positive aspects
                    common_themes.append("positive_feedback")
            
            # In production, would update attraction metadata or recommendation weights
            logger.info(f"Updated recommendations for attraction {attraction_id} based on {len(reviews)} reviews")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating recommendations from reviews: {e}")
            return False

