"""
Recommendation service for the Croatian tourist host platform.

Integrates host knowledge, guest preferences, attraction data, and
automated content updates to provide personalized recommendations.
"""

import logging
import math
from datetime import datetime, date
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.exc import IntegrityError

from app.models.recommendation import (
    RecommendationRequest,
    Recommendation,
    RecommendationSet,
    RecommendationType,
    RecommendationPriority,
    WeatherContext,
    RecommendationRequestCreate,
    RecommendationRequestAPI,
    RecommendationResponse,
    RecommendationSetResponse,
    RecommendationFeedback,
    RecommendationSetFeedback,
    RecommendationBatch,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
    RecommendationAnalytics,
    RECOMMENDATION_WEIGHTS,
    PREFERENCE_CATEGORIES,
    CROATIAN_SEASONAL_FACTORS,
)
from app.models.attraction import Attraction, AttractionStatus, SeasonalEvent
from app.models.guest_group import GuestGroup, GuestPreference
from app.models.host import Host
from app.models.content_source import ContentUpdate
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.services.graph_service import GraphService
from app.services.recommendation_scoring import RecommendationScoring
from app.services.recommendation_candidates import RecommendationCandidates
from app.services.recommendation_builders import RecommendationBuilders

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for generating intelligent recommendations.
    
    Combines host knowledge, guest preferences, attraction data,
    and real-time content updates to create personalized experiences.
    """
    
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        """
        Initialize the recommendation service.
        
        Args:
            db: Database session
            ai_service: Optional AI service for embeddings
        """
        self.db = db
        self.ai_service = ai_service or AIService()
        self.vector_service = VectorService(db, self.ai_service)
        self.graph_service = GraphService()
        self.candidates_service = RecommendationCandidates(db, self.vector_service, self.graph_service)
        self.builders_service = RecommendationBuilders(db)
    
    # Core Recommendation Generation
    async def generate_recommendations(self, guest_group_id: uuid.UUID, host_id: uuid.UUID, 
                                     request_data: RecommendationRequestCreate) -> Optional[RecommendationSetResponse]:
        """
        Generate personalized recommendations for a guest group.
        
        Args:
            guest_group_id: Guest group UUID
            host_id: Host UUID
            request_data: Recommendation request parameters
            
        Returns:
            RecommendationSetResponse: Complete recommendation set
        """
        start_time = datetime.utcnow()
        
        try:
            # Create recommendation request
            request = await self._create_recommendation_request(
                guest_group_id, host_id, request_data
            )
            
            if not request:
                logger.error("Failed to create recommendation request")
                return None
            
            # Get guest group and preferences
            guest_group = await self._get_guest_group_with_preferences(guest_group_id)
            if not guest_group:
                logger.error(f"Guest group not found: {guest_group_id}")
                return None
            
            # Get host information
            host = await self._get_host_info(host_id)
            if not host:
                logger.error(f"Host not found: {host_id}")
                return None
            
            # Generate candidate attractions using vector search + graph relationships + traditional filtering
            candidates = await self.candidates_service.get_candidate_attractions_advanced(
                request, guest_group, host
            )
            
            # Score and rank recommendations
            scored_recommendations = await self._score_recommendations(
                request, guest_group, host, candidates
            )
            
            # Create recommendation set
            recommendation_set = await self.builders_service.create_recommendation_set(
                request, scored_recommendations, start_time
            )
            
            if recommendation_set:
                logger.info(f"Generated {len(scored_recommendations)} recommendations for group {guest_group_id}")
                return recommendation_set
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return None
    
    async def _create_recommendation_request(self, guest_group_id: uuid.UUID, host_id: uuid.UUID, 
                                           request_data: RecommendationRequestCreate) -> Optional[RecommendationRequest]:
        """Create a recommendation request record."""
        try:
            # Determine season from target date or current date
            target_date = request_data.target_date or date.today()
            season = self._get_season_from_date(target_date)
            
            request = RecommendationRequest(
                guest_group_id=guest_group_id,
                host_id=host_id,
                request_type=request_data.request_type,
                target_date=request_data.target_date,
                current_location=request_data.current_location,
                preferred_radius_km=request_data.preferred_radius_km,
                group_size=request_data.group_size,
                duration_hours=request_data.duration_hours,
                budget_range=request_data.budget_range,
                weather_context=request_data.weather_context,
                season=season,
                temperature_celsius=request_data.temperature_celsius,
                preferred_categories=request_data.preferred_categories,
                excluded_categories=request_data.excluded_categories,
                accessibility_requirements=request_data.accessibility_requirements,
                response_language=request_data.response_language
            )
            
            self.db.add(request)
            await self.db.commit()
            await self.db.refresh(request)
            
            return request
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating recommendation request: {e}")
            return None
    
    async def _get_guest_group_with_preferences(self, guest_group_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get guest group with all preferences."""
        try:
            # Get guest group
            guest_group_stmt = select(GuestGroup).where(GuestGroup.id == guest_group_id)
            guest_group_result = await self.db.execute(guest_group_stmt)
            guest_group = guest_group_result.scalar_one_or_none()
            
            if not guest_group:
                return None
            
            # Get individual guest preferences
            preferences_stmt = select(GuestPreference).where(
                GuestPreference.guest_group_id == guest_group_id
            )
            preferences_result = await self.db.execute(preferences_stmt)
            preferences = preferences_result.scalars().all()
            
            return {
                'group': guest_group,
                'preferences': preferences
            }
            
        except Exception as e:
            logger.error(f"Error getting guest group with preferences: {e}")
            return None
    
    async def _get_host_info(self, host_id: uuid.UUID) -> Optional[Host]:
        """Get host information."""
        try:
            stmt = select(Host).where(Host.id == host_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting host info: {e}")
            return None
    
    
    async def _get_candidate_seasonal_events(self, request: RecommendationRequest) -> List[SeasonalEvent]:
        """Get candidate seasonal events."""
        try:
            stmt = select(SeasonalEvent).where(SeasonalEvent.is_active == True)
            
            # Filter by date if target date is specified
            if request.target_date:
                stmt = stmt.where(
                    or_(
                        SeasonalEvent.start_date.is_(None),  # No specific date
                        and_(
                            SeasonalEvent.start_date <= request.target_date,
                            or_(
                                SeasonalEvent.end_date.is_(None),
                                SeasonalEvent.end_date >= request.target_date
                            )
                        )
                    )
                )
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting seasonal events: {e}")
            return []
    
    async def _score_recommendations(self, request: RecommendationRequest, 
                                   guest_group: Dict[str, Any], 
                                   host: Host, 
                                   candidates: List[Attraction]) -> List[Dict[str, Any]]:
        """Score and rank candidate attractions."""
        scored_recommendations = []
        
        for attraction in candidates:
            try:
                # Calculate individual scores
                preference_score = RecommendationScoring.calculate_preference_score(attraction, guest_group, request)
                host_insight_score = RecommendationScoring.calculate_host_insight_score(attraction, host)
                popularity_score = RecommendationScoring.calculate_popularity_score(attraction)
                seasonal_score = RecommendationScoring.calculate_seasonal_score(attraction, request)
                location_score = RecommendationScoring.calculate_location_score(attraction, request, host)
                
                # Calculate vector similarity score if embeddings exist
                vector_score = RecommendationScoring.calculate_vector_similarity_score(
                    attraction, guest_group.get('group')
                )
                
                # Calculate weighted total score (including vector similarity)
                total_score = RecommendationScoring.calculate_total_score(
                    preference_score, host_insight_score, popularity_score,
                    seasonal_score, location_score, vector_score
                )
                
                # Determine priority
                priority = self._determine_priority(total_score, attraction, request)
                
                # Create recommendation data
                recommendation_data = {
                    'attraction': attraction,
                    'total_score': total_score,
                    'priority': priority,
                    'scores': {
                        'preference': preference_score,
                        'host_insight': host_insight_score,
                        'popularity': popularity_score,
                        'seasonal': seasonal_score,
                        'location': location_score,
                        'vector_similarity': vector_score
                    },
                    'host_insight': self._generate_host_insight(attraction, host),
                    'host_tip': self._generate_host_tip(attraction, host),
                    'why_recommended': self._generate_explanation(attraction, guest_group, total_score)
                }
                
                scored_recommendations.append(recommendation_data)
                
            except Exception as e:
                logger.error(f"Error scoring attraction {attraction.id}: {e}")
                continue
        
        # Sort by total score
        scored_recommendations.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Add rank order
        for i, rec in enumerate(scored_recommendations):
            rec['rank_order'] = i + 1
        
        return scored_recommendations[:10]  # Return top 10 recommendations
    
    
    def _determine_priority(self, total_score: float, attraction: Attraction, 
                          request: RecommendationRequest) -> str:
        """Determine recommendation priority."""
        if total_score >= 0.8:
            return RecommendationPriority.HIGH
        elif total_score >= 0.6:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    def _generate_host_insight(self, attraction: Attraction, host: Host) -> Optional[str]:
        """Generate host insight for the recommendation."""
        insights = []
        
        if attraction.host_personal_tip:
            insights.append(attraction.host_personal_tip)
        
        if attraction.host_favorite_time:
            insights.append(f"Best time to visit: {attraction.host_favorite_time}")
        
        if attraction.host_recommended_duration:
            insights.append(f"Recommended duration: {attraction.host_recommended_duration}")
        
        return " | ".join(insights) if insights else None
    
    def _generate_host_tip(self, attraction: Attraction, host: Host) -> Optional[str]:
        """Generate specific host tip."""
        if attraction.host_insider_info:
            return attraction.host_insider_info
        return None
    
    def _generate_explanation(self, attraction: Attraction, 
                            guest_group: Dict[str, Any], 
                            total_score: float) -> str:
        """Generate explanation for why this was recommended."""
        reasons = []
        
        group = guest_group['group']
        
        # Check interest matches
        if group.interests:
            matching_interests = set(group.interests) & set(attraction.category_tags)
            if matching_interests:
                reasons.append(f"Matches your interests: {', '.join(matching_interests)}")
        
        # Check group suitability
        if group.group_dynamics == "family" and "family_friendly" in attraction.category_tags:
            reasons.append("Perfect for families")
        elif group.group_dynamics == "romantic" and "romantic" in attraction.category_tags:
            reasons.append("Ideal for couples")
        
        # Host knowledge
        if attraction.host_personal_tip:
            reasons.append("Your host has special insights about this place")
        
        # Popularity
        if attraction.guest_rating and attraction.guest_rating >= 4.0:
            reasons.append(f"Highly rated by other guests ({attraction.guest_rating:.1f}/5)")
        
        if not reasons:
            reasons.append("Selected based on your preferences and local expertise")
        
        return ". ".join(reasons) + "."
    
    
    def _get_season_from_date(self, target_date: date) -> str:
        """Determine season from date."""
        month = target_date.month
        
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"
    
    # Feedback and Analytics
    async def get_host_analytics(self, host_id: uuid.UUID, days: int = 30) -> RecommendationAnalytics:
        """
        Aggregate recommendation analytics for the host dashboard.

        Uses existing recommendation-set stats where available; otherwise returns zeros.
        """
        _ = days
        stats = await self.get_host_recommendation_stats(host_id)
        total_sets = int(stats.get("total_recommendation_sets") or 0)
        total_recs = int(stats.get("total_recommendations_generated") or 0)
        avg_sat = float(stats.get("average_satisfaction") or 0.0)
        accept_rate = float(stats.get("recommendations_accepted_rate") or 0.0)
        return RecommendationAnalytics(
            total_recommendations=total_recs if total_recs else total_sets,
            average_rating=avg_sat,
            guest_satisfaction=accept_rate,
            top_categories=[],
            performance_metrics=stats,
            time_period={"window_days": days},
            host_contribution_impact=float(stats.get("host_insights_helpful_rate") or 0.0),
        )

    def _explorer_attraction_to_response(
        self,
        attraction: Attraction,
        relevance_score: float,
        rank_order: int,
        why_recommended: str,
    ) -> RecommendationResponse:
        """Build API recommendation rows for public explorer endpoints (no DB persistence)."""
        now = datetime.utcnow()
        rs = max(0.0, min(1.0, float(relevance_score)))
        if rs >= 0.65:
            priority = RecommendationPriority.HIGH
        elif rs >= 0.35:
            priority = RecommendationPriority.MEDIUM
        else:
            priority = RecommendationPriority.LOW
        desc = attraction.description or attraction.short_description or ""
        return RecommendationResponse(
            id=attraction.id,
            title=attraction.name,
            description=desc,
            recommendation_type=RecommendationType.ATTRACTION.value,
            relevance_score=round(rs, 3),
            priority=priority.value,
            rank_order=rank_order,
            why_recommended=why_recommended,
            estimated_duration=getattr(attraction, "host_recommended_duration", None),
            best_time_to_visit=getattr(attraction, "host_favorite_time", None),
            estimated_cost=getattr(attraction, "admission_fee", None),
            booking_required=bool(getattr(attraction, "booking_required", False)),
            created_at=now,
        )

    async def _fetch_approved_attractions_for_city(
        self,
        city: Optional[str],
        fetch_limit: int = 80,
    ) -> List[Attraction]:
        """
        Attractions for public seasonal/weather endpoints.

        Matches public city search: draft/pending included, rejected/archived excluded.
        """
        visible = (
            AttractionStatus.APPROVED,
            AttractionStatus.DRAFT,
            AttractionStatus.PENDING,
        )
        stmt = select(Attraction).where(Attraction.status.in_(visible))
        if city and city.strip():
            stmt = stmt.where(Attraction.city.ilike(f"%{city.strip()}%"))
        stmt = stmt.limit(fetch_limit)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        if rows or not (city and city.strip()):
            return rows
        stmt_all = select(Attraction).where(Attraction.status.in_(visible)).limit(fetch_limit)
        r2 = await self.db.execute(stmt_all)
        return list(r2.scalars().all())

    async def get_seasonal_recommendations(
        self,
        season: str,
        city: Optional[str] = None,
        limit: int = 20,
    ) -> List[RecommendationResponse]:
        """Seasonal picks from approved attractions (Croatian seasonal model)."""
        lim = max(1, min(int(limit), 50))
        fake_request = SimpleNamespace(season=season, weather_context=None)
        attractions = await self._fetch_approved_attractions_for_city(
            city, fetch_limit=max(lim * 5, 40)
        )
        scored: List[Tuple[Attraction, float]] = []
        for a in attractions:
            score = RecommendationScoring.calculate_seasonal_score(
                a, fake_request  # type: ignore[arg-type]
            )
            if score < 0.12 and (getattr(a, "seasonal_availability", None) or "") == "year_round":
                score = 0.35
            scored.append((a, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        out: List[RecommendationResponse] = []
        for i, (a, s) in enumerate(scored[:lim]):
            out.append(
                self._explorer_attraction_to_response(
                    a,
                    s,
                    i + 1,
                    f"Selected for {season} visits along the Croatian coast.",
                )
            )
        return out

    async def get_weather_based_recommendations(
        self,
        city: str,
        limit: int = 10,
    ) -> List[RecommendationResponse]:
        """Lightweight weather-friendly ranking for a city (public endpoint)."""
        lim = max(1, min(int(limit), 50))
        attractions = await self._fetch_approved_attractions_for_city(
            city, fetch_limit=max(lim * 5, 40)
        )
        scored: List[Tuple[Attraction, float]] = []
        for a in attractions:
            tags = a.category_tags or []
            s = 0.42
            if "outdoor" in tags or (a.attraction_type or "") == "natural":
                s += 0.28
            if "indoor" in tags or (a.attraction_type or "") in (
                "cultural",
                "historic",
                "culinary",
            ):
                s += 0.12
            if a.guest_rating and getattr(a, "total_ratings", 0):
                s += min(0.18, max(0.0, (float(a.guest_rating) - 3.0) * 0.06))
            scored.append((a, min(1.0, s)))
        scored.sort(key=lambda x: x[1], reverse=True)
        out: List[RecommendationResponse] = []
        for i, (a, s) in enumerate(scored[:lim]):
            out.append(
                self._explorer_attraction_to_response(
                    a,
                    s,
                    i + 1,
                    "Suggested for typical fair-weather days in this area.",
                )
            )
        return out

    async def record_recommendation_feedback(self, feedback: RecommendationSetFeedback) -> bool:
        """Record guest feedback on recommendations."""
        try:
            # Update recommendation set
            stmt = update(RecommendationSet).where(
                RecommendationSet.id == feedback.recommendation_set_id
            ).values(
                overall_satisfaction=feedback.overall_satisfaction,
                feedback_comment=feedback.feedback_comment,
                would_recommend_host=feedback.would_recommend_host,
                host_insights_helpful=feedback.host_insights_helpful,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(stmt)
            
            # Update individual recommendations
            for individual_feedback in feedback.individual_feedback:
                rec_stmt = update(Recommendation).where(
                    Recommendation.id == individual_feedback.recommendation_id
                ).values(
                    accepted=individual_feedback.accepted,
                    feedback_rating=individual_feedback.feedback_rating,
                    feedback_comment=individual_feedback.feedback_comment,
                    accepted_at=datetime.utcnow() if individual_feedback.accepted else None,
                    updated_at=datetime.utcnow()
                )
                
                await self.db.execute(rec_stmt)
            
            await self.db.commit()
            
            logger.info(f"Recorded feedback for recommendation set {feedback.recommendation_set_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording recommendation feedback: {e}")
            return False
    
    async def get_host_recommendation_stats(self, host_id: uuid.UUID) -> Dict[str, Any]:
        """Get recommendation performance stats for a host."""
        try:
            # Get recommendation sets for this host
            sets_stmt = select(RecommendationSet).where(RecommendationSet.host_id == host_id)
            sets_result = await self.db.execute(sets_stmt)
            sets = sets_result.scalars().all()
            
            if not sets:
                return {
                    "total_recommendation_sets": 0,
                    "average_satisfaction": 0.0,
                    "recommendations_accepted_rate": 0.0,
                    "host_insights_helpful_rate": 0.0
                }
            
            # Calculate statistics
            total_sets = len(sets)
            total_satisfaction = sum(s.overall_satisfaction for s in sets if s.overall_satisfaction)
            satisfaction_count = sum(1 for s in sets if s.overall_satisfaction)
            
            total_recommendations = sum(s.total_recommendations for s in sets)
            total_accepted = sum(s.recommendations_accepted for s in sets)
            
            insights_helpful = sum(1 for s in sets if s.host_insights_helpful is True)
            insights_rated = sum(1 for s in sets if s.host_insights_helpful is not None)
            
            return {
                "total_recommendation_sets": total_sets,
                "average_satisfaction": total_satisfaction / satisfaction_count if satisfaction_count > 0 else 0.0,
                "recommendations_accepted_rate": total_accepted / total_recommendations if total_recommendations > 0 else 0.0,
                "host_insights_helpful_rate": insights_helpful / insights_rated if insights_rated > 0 else 0.0,
                "total_recommendations_generated": total_recommendations
            }
            
        except Exception as e:
            logger.error(f"Error getting host recommendation stats: {e}")
            return {}
    
    async def get_recommendation_set_by_id(self, set_id: uuid.UUID) -> Optional[RecommendationSetResponse]:
        """Get a recommendation set by ID."""
        try:
            # Get recommendation set
            set_stmt = select(RecommendationSet).where(RecommendationSet.id == set_id)
            set_result = await self.db.execute(set_stmt)
            rec_set = set_result.scalar_one_or_none()
            
            if not rec_set:
                return None
            
            # Get individual recommendations
            recs_stmt = select(Recommendation).where(
                Recommendation.request_id == rec_set.request_id
            ).order_by(Recommendation.rank_order)
            recs_result = await self.db.execute(recs_stmt)
            recommendations = recs_result.scalars().all()
            
            # Create response
            rec_responses = [RecommendationResponse.model_validate(rec) for rec in recommendations]
            
            return RecommendationSetResponse(
                id=rec_set.id,
                title=rec_set.title,
                description=rec_set.description,
                total_recommendations=rec_set.total_recommendations,
                algorithm_version=rec_set.algorithm_version,
                processing_time_ms=rec_set.processing_time_ms,
                personalization_factors=rec_set.personalization_factors,
                host_contribution_weight=rec_set.host_contribution_weight,
                recommendations=rec_responses,
                created_at=rec_set.created_at
            )
            
        except Exception as e:
            logger.error(f"Error getting recommendation set: {e}")
            return None

    def _weather_context_api_to_str(self, wc: Optional[Any]) -> Optional[str]:
        if wc is None:
            return None
        if isinstance(wc, str):
            return wc[:20] if wc else None
        if isinstance(wc, dict):
            raw = wc.get("condition") or wc.get("summary") or wc.get("description")
            if raw is None:
                return None
            s = str(raw).strip()
            return s[:20] if s else None
        return None

    async def get_personalized_recommendations(
        self,
        guest_group_id: uuid.UUID,
        request_data: RecommendationRequestAPI,
    ) -> RecommendationBatch:
        """Build a RecommendationBatch for a guest group (guest + host preview endpoints)."""
        now = datetime.utcnow()
        empty = RecommendationBatch(
            recommendations=[],
            total_count=0,
            generated_at=now,
            guest_group_id=guest_group_id,
            request_context={},
            personalization_factors={},
        )

        gg = await self._get_guest_group_with_preferences(guest_group_id)
        if not gg or not gg.get("group"):
            logger.warning("get_personalized_recommendations: guest group %s not found", guest_group_id)
            return empty

        host_id = gg["group"].host_id
        weather_str = self._weather_context_api_to_str(request_data.weather_context)

        create = RecommendationRequestCreate(
            target_date=request_data.target_date,
            current_location=request_data.current_location,
            preferred_radius_km=request_data.preferred_radius_km,
            preferred_categories=list(request_data.preferred_categories or []),
            excluded_categories=list(request_data.excluded_categories or []),
            accessibility_requirements=list(request_data.accessibility_requirements or []),
            response_language=request_data.language or "en",
            weather_context=weather_str,
        )

        try:
            rec_set = await self.generate_recommendations(guest_group_id, host_id, create)
        except Exception as e:
            logger.error("get_personalized_recommendations: generate_recommendations failed: %s", e)
            return empty

        if not rec_set or not rec_set.recommendations:
            return empty

        max_n = max(1, min(request_data.max_recommendations, 50))
        recs = list(rec_set.recommendations)[:max_n]
        return RecommendationBatch(
            recommendations=recs,
            total_count=len(recs),
            generated_at=now,
            guest_group_id=guest_group_id,
            request_context={
                "include_weather": request_data.include_weather,
                "include_seasonal": request_data.include_seasonal,
            },
            personalization_factors=rec_set.personalization_factors or {},
        )

    async def get_recommendation_history(
        self,
        guest_group_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecommendationResponse]:
        """List past recommendations for a guest group (newest first)."""
        try:
            stmt = (
                select(Recommendation)
                .join(
                    RecommendationRequest,
                    Recommendation.request_id == RecommendationRequest.id,
                )
                .where(RecommendationRequest.guest_group_id == guest_group_id)
                .order_by(desc(Recommendation.created_at))
                .offset(max(skip, 0))
                .limit(min(max(limit, 1), 200))
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            return [RecommendationResponse.model_validate(r) for r in rows]
        except Exception as e:
            logger.error("get_recommendation_history failed: %s", e)
            return []

    async def submit_feedback(
        self,
        guest_group_id: uuid.UUID,
        feedback_data: RecommendationFeedbackCreate,
    ) -> Optional[RecommendationFeedbackResponse]:
        """Attach thumbs feedback to a recommendation row scoped to the guest group."""
        try:
            stmt = (
                select(Recommendation)
                .join(
                    RecommendationRequest,
                    Recommendation.request_id == RecommendationRequest.id,
                )
                .where(
                    Recommendation.id == feedback_data.recommendation_id,
                    RecommendationRequest.guest_group_id == guest_group_id,
                )
            )
            result = await self.db.execute(stmt)
            rec = result.scalar_one_or_none()
            if not rec:
                return None

            rec.feedback_rating = feedback_data.rating
            if feedback_data.feedback_text:
                rec.feedback_comment = feedback_data.feedback_text
            rec.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(rec)

            return RecommendationFeedbackResponse(
                id=uuid.uuid4(),
                recommendation_id=feedback_data.recommendation_id,
                rating=feedback_data.rating,
                feedback_text=feedback_data.feedback_text,
                visited=feedback_data.visited,
                helpful_factors=list(feedback_data.helpful_factors or []),
                improvement_suggestions=feedback_data.improvement_suggestions,
                guest_group_id=guest_group_id,
                created_at=rec.updated_at or datetime.utcnow(),
            )
        except Exception as e:
            await self.db.rollback()
            logger.error("submit_feedback failed: %s", e)
            return None