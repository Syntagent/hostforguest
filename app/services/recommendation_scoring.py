"""
Scoring logic for recommendation engine.

Contains all scoring calculation methods for ranking attractions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup
from app.models.recommendation import (
    RecommendationRequest,
    RECOMMENDATION_WEIGHTS,
    CROATIAN_SEASONAL_FACTORS,
    WeatherContext
)

logger = logging.getLogger(__name__)


class RecommendationScoring:
    """
    Scoring calculations for recommendations.
    
    Provides methods to calculate various scores for ranking attractions.
    """
    
    @staticmethod
    def calculate_preference_score(
        attraction: Attraction,
        guest_group: Dict[str, Any],
        request: RecommendationRequest
    ) -> float:
        """Calculate how well attraction matches guest preferences."""
        score = 0.0
        
        group = guest_group['group']
        
        # Match interests
        if group.interests:
            for interest in group.interests:
                if interest.lower() in [tag.lower() for tag in attraction.category_tags]:
                    score += 0.2
        
        # Match age groups
        if group.age_groups and attraction.age_suitability:
            common_ages = set(group.age_groups) & set(attraction.age_suitability)
            if common_ages:
                score += 0.3
        
        # Match travel style
        if group.travel_style == "active" and "adventure" in attraction.category_tags:
            score += 0.2
        elif group.travel_style == "relaxed" and "relaxation" in attraction.category_tags:
            score += 0.2
        
        # Match group dynamics
        if group.group_dynamics == "family" and "family_friendly" in attraction.category_tags:
            score += 0.2
        elif group.group_dynamics == "romantic" and "romantic" in attraction.category_tags:
            score += 0.2
        
        # Check request-specific preferences
        if request.preferred_categories:
            for category in request.preferred_categories:
                if category.lower() in [tag.lower() for tag in attraction.category_tags]:
                    score += 0.1
        
        # Penalize excluded categories
        if request.excluded_categories:
            for category in request.excluded_categories:
                if category.lower() in [tag.lower() for tag in attraction.category_tags]:
                    score -= 0.3
        
        return min(1.0, max(0.0, score))
    
    @staticmethod
    def calculate_host_insight_score(attraction: Attraction, host) -> float:
        """Calculate score based on host's knowledge and insights."""
        score = 0.0
        
        if attraction.created_by_host_id == host.id:
            score += 0.8
        
        if attraction.host_personal_tip:
            score += 0.3
        if attraction.host_insider_info:
            score += 0.3
        if attraction.host_story:
            score += 0.2
        
        if host.city and attraction.city and host.city.lower() == attraction.city.lower():
            score += 0.4
        
        return min(1.0, score)
    
    @staticmethod
    def calculate_popularity_score(attraction: Attraction) -> float:
        """Calculate score based on attraction popularity."""
        rec_score = min(1.0, attraction.recommendation_count / 100.0)
        
        rating_score = 0.0
        if attraction.guest_rating and attraction.total_ratings > 0:
            rating_score = (attraction.guest_rating - 1.0) / 4.0
        
        return (rec_score * 0.6) + (rating_score * 0.4)
    
    @staticmethod
    def calculate_seasonal_score(attraction: Attraction, request: RecommendationRequest) -> float:
        """Calculate seasonal appropriateness score."""
        if not request.season:
            return 0.5
        
        seasonal_factors = CROATIAN_SEASONAL_FACTORS.get(request.season, {})
        current_month = datetime.now().month
        
        score = 0.0
        
        if attraction.seasonal_availability == "year_round":
            score += 0.5
        elif attraction.best_months and current_month in attraction.best_months:
            score += 0.8
        
        tags = attraction.category_tags or []
        highlights = seasonal_factors.get('highlights', [])
        for highlight in highlights:
            if highlight in tags:
                score += 0.2
        
        avoid = seasonal_factors.get('avoid', [])
        for avoid_item in avoid:
            if avoid_item in tags:
                score -= 0.3
        
        if request.weather_context:
            if request.weather_context == WeatherContext.RAINY:
                if "indoor" in tags:
                    score += 0.3
                elif "outdoor" in tags:
                    score -= 0.2
            elif request.weather_context == WeatherContext.SUNNY:
                if "outdoor" in tags:
                    score += 0.3
        
        return min(1.0, max(0.0, score))
    
    @staticmethod
    def calculate_location_score(
        attraction: Attraction,
        request: RecommendationRequest,
        host
    ) -> float:
        """Calculate location convenience score."""
        score = 0.5
        
        host_area = getattr(host, "county", None) or getattr(host, "region", None)
        if host.city and attraction.city:
            if host.city.lower() == attraction.city.lower():
                score = 1.0
            elif attraction.region and host_area and host_area == attraction.region:
                score = 0.7
        
        return min(1.0, max(0.0, score))
    
    @staticmethod
    def calculate_vector_similarity_score(
        attraction: Attraction,
        guest_group: Optional[GuestGroup]
    ) -> float:
        """Calculate similarity score based on vector embeddings."""
        try:
            if not guest_group or not hasattr(guest_group, 'preference_embedding'):
                return 0.5
            
            if not hasattr(attraction, 'embedding') or not attraction.embedding:
                return 0.5
            
            import json
            guest_embedding = json.loads(guest_group.preference_embedding) if isinstance(guest_group.preference_embedding, str) else guest_group.preference_embedding
            attraction_embedding = json.loads(attraction.embedding) if isinstance(attraction.embedding, str) else attraction.embedding
            
            if not guest_embedding or not attraction_embedding:
                return 0.5
            
            similarity = RecommendationScoring.cosine_similarity(guest_embedding, attraction_embedding)
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Error calculating vector similarity: {e}")
            return 0.5
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            dot_product = np.dot(vec1_array, vec2_array)
            magnitude1 = np.linalg.norm(vec1_array)
            magnitude2 = np.linalg.norm(vec2_array)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return (similarity + 1) / 2  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.5
    
    @staticmethod
    def calculate_total_score(
        preference_score: float,
        host_insight_score: float,
        popularity_score: float,
        seasonal_score: float,
        location_score: float,
        vector_score: float
    ) -> float:
        """Calculate weighted total score."""
        return (
            preference_score * RECOMMENDATION_WEIGHTS.get("guest_preferences", 0.25) +
            host_insight_score * RECOMMENDATION_WEIGHTS.get("host_insights", 0.20) +
            popularity_score * RECOMMENDATION_WEIGHTS.get("popularity", 0.15) +
            seasonal_score * RECOMMENDATION_WEIGHTS.get("seasonal_relevance", 0.15) +
            location_score * RECOMMENDATION_WEIGHTS.get("location_proximity", 0.10) +
            vector_score * RECOMMENDATION_WEIGHTS.get("vector_similarity", 0.15)
        )

