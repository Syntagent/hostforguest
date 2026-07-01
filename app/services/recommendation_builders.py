"""
Recommendation set and individual recommendation builders.

Handles creation of recommendation sets and individual recommendations.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import (
    RecommendationRequest,
    Recommendation,
    RecommendationSet,
    RecommendationType,
    RecommendationPriority,
    RecommendationResponse,
    RecommendationSetResponse,
    RECOMMENDATION_WEIGHTS
)
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup
from app.models.host import Host

logger = logging.getLogger(__name__)


class RecommendationBuilders:
    """
    Builders for recommendation sets and individual recommendations.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize recommendation builders.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_recommendation_set(
        self,
        request: RecommendationRequest,
        scored_recommendations: List[Dict[str, Any]],
        start_time: datetime
    ) -> Optional[RecommendationSetResponse]:
        """Create the final recommendation set."""
        try:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            rec_set = RecommendationSet(
                request_id=request.id,
                guest_group_id=request.guest_group_id,
                host_id=request.host_id,
                title=self._generate_set_title(request, scored_recommendations),
                description=self._generate_set_description(request),
                total_recommendations=len(scored_recommendations),
                processing_time_ms=int(processing_time),
                personalization_factors=self._get_personalization_factors(request),
                host_contribution_weight=RECOMMENDATION_WEIGHTS["host_insights"]
            )
            
            self.db.add(rec_set)
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
            try:
                await self.db.refresh(rec_set)
            except Exception:
                pass  # RLS may block SELECT after flush
            
            # Create individual recommendations
            recommendations = []
            for rec_data in scored_recommendations:
                recommendation = await self.create_individual_recommendation(
                    request, rec_set, rec_data
                )
                if recommendation:
                    recommendations.append(recommendation)
            
            rec_set.delivered_at = datetime.utcnow()
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
            
            response = RecommendationSetResponse(
                id=rec_set.id,
                title=rec_set.title,
                description=rec_set.description,
                total_recommendations=rec_set.total_recommendations,
                algorithm_version=rec_set.algorithm_version,
                processing_time_ms=rec_set.processing_time_ms,
                personalization_factors=rec_set.personalization_factors,
                host_contribution_weight=rec_set.host_contribution_weight,
                recommendations=recommendations,
                created_at=rec_set.created_at
            )
            
            return response
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating recommendation set: {e}")
            return None
    
    async def create_individual_recommendation(
        self,
        request: RecommendationRequest,
        rec_set: RecommendationSet,
        rec_data: Dict[str, Any]
    ) -> Optional[RecommendationResponse]:
        """Create an individual recommendation."""
        try:
            attraction = rec_data['attraction']
            
            # Partner wrappers (SimpleNamespace) have different IDs - set attraction_id to None
            from app.models.attraction import Attraction as AttractionModel
            attraction_id = attraction.id if isinstance(attraction, AttractionModel) else None
            rec_type = RecommendationType.ATTRACTION if isinstance(attraction, AttractionModel) else RecommendationType.ATTRACTION
            
            recommendation = Recommendation(
                request_id=request.id,
                attraction_id=attraction_id,
                title=attraction.name,
                description=attraction.description,
                recommendation_type=RecommendationType.ATTRACTION,
                relevance_score=rec_data['total_score'],
                priority=rec_data['priority'],
                rank_order=rec_data['rank_order'],
                host_insight=rec_data.get('host_insight'),
                host_tip=rec_data.get('host_tip'),
                why_recommended=rec_data.get('why_recommended'),
                estimated_duration=attraction.host_recommended_duration,
                best_time_to_visit=attraction.host_favorite_time,
                estimated_cost=attraction.admission_fee,
                booking_required=False,
                distance_km=None,
                travel_time_minutes=None,
                weather_suitability=self._get_weather_suitability(attraction),
                season_suitability=(attraction.best_months or []) or [],
                group_suitability=(attraction.age_suitability or []) or []
            )
            
            self.db.add(recommendation)
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
            try:
                await self.db.refresh(recommendation)
            except Exception:
                pass  # RLS may block SELECT after flush
            
            return RecommendationResponse.model_validate(recommendation)
            
        except Exception as e:
            logger.error(f"Error creating individual recommendation: {e}")
            return None
    
    def _generate_set_title(
        self,
        request: RecommendationRequest,
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate title for recommendation set."""
        if request.request_type == RecommendationType.ATTRACTION:
            return f"Recommended Attractions in {request.current_location or 'Lovran'}"
        elif request.request_type == RecommendationType.ACTIVITY:
            return f"Activities for Your Visit"
        elif request.request_type == RecommendationType.EVENT:
            return f"Events and Festivals"
        else:
            return f"Personalized Recommendations"
    
    def _generate_set_description(self, request: RecommendationRequest) -> str:
        """Generate description for recommendation set."""
        return f"Curated recommendations based on your preferences and local host expertise."
    
    def _get_personalization_factors(self, request: RecommendationRequest) -> Dict[str, Any]:
        """Get factors used in personalization."""
        return {
            "request_type": request.request_type,
            "season": request.season,
            "weather_context": request.weather_context,
            "group_size": request.group_size,
            "duration_hours": request.duration_hours,
            "budget_range": request.budget_range,
            "preferred_categories": request.preferred_categories,
            "algorithm_weights": RECOMMENDATION_WEIGHTS
        }
    
    def _get_weather_suitability(self, attraction: Attraction) -> List[str]:
        """Determine weather suitability for attraction."""
        from app.models.recommendation import WeatherContext
        
        suitability = []
        
        if "outdoor" in (attraction.category_tags or []):
            suitability.extend([WeatherContext.SUNNY, WeatherContext.CLOUDY])
        if "indoor" in (attraction.category_tags or []):
            suitability.extend([WeatherContext.RAINY, WeatherContext.COLD])
        if "beach" in (attraction.category_tags or []):
            suitability.extend([WeatherContext.SUNNY, WeatherContext.HOT])
        
        return suitability

