"""
Recommendation service for the Croatian tourist host platform.

Integrates host knowledge, guest preferences, attraction data, and
automated content updates to provide personalized recommendations.
"""

import logging
import time
from datetime import datetime, date
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.exc import IntegrityError

from app.models.recommendation_api import (
    RecommendationAlgorithmTestResponse,
    RecommendationPerformanceMetricsResponse,
)
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
    ExplorerRecommendationPublicResponse,
    RecommendationSetResponse,
    RecommendationFeedback,
    RecommendationSetFeedback,
    RecommendationBatch,
    GuestRecommendationBatch,
    GuestRecommendationItem,
    GuestAttractionSummary,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
    RecommendationAnalytics,
    RECOMMENDATION_WEIGHTS,
    PREFERENCE_CATEGORIES,
    CROATIAN_SEASONAL_FACTORS,
)
from app.models.attraction import Attraction, AttractionStatus, SeasonalEvent
from app.models.partner import Partner, PartnerStatus
from app.models.guest_group import GuestGroup, GuestPreference
from app.models.host import Host
from app.models.content_source import ContentUpdate
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.services.recommendation_scoring import RecommendationScoring, _wow_multiplier
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
        self.candidates_service = RecommendationCandidates(db, self.vector_service)
        self.builders_service = RecommendationBuilders(db)
    
    # Core Recommendation Generation
    async def generate_recommendations(
        self,
        guest_group_id: uuid.UUID,
        host_id: uuid.UUID,
        request_data: RecommendationRequestCreate,
        max_price_level: Optional[int] = None,
        food_type: Optional[str] = None,
        query_terms: Optional[str] = None,
    ) -> Optional[RecommendationSetResponse]:
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
                request, guest_group, host, max_price_level=max_price_level,
                query_terms=query_terms,
            )
            candidates = [
                c for c in candidates
                if self._is_guest_visible_attraction(c)
            ]

            # Score and rank recommendations
            scored_recommendations = await self._score_recommendations(
                request, guest_group, host, candidates, query_terms=query_terms
            )
            
            # Enrich with partners for dining/food categories
            if request.preferred_categories or food_type:
                pref_lower = [c.lower() for c in (request.preferred_categories or [])]
                # Only add partners for dedicated dining/food/wine queries
                dining_cats = {'dining', 'food', 'restaurant', 'wine'}
                is_dining_query = bool(dining_cats & set(pref_lower))
                # Also check if dining is the primary category (not mixed with beach/nature)
                is_primary_dining = is_dining_query and len(set(pref_lower) - dining_cats) <= 1
                if is_primary_dining or food_type:
                    partner_recs = await self._get_partner_recommendations(
                        request,
                        host,
                        food_type=food_type,
                        query_terms=query_terms,
                    )
                    scored_recommendations.extend(partner_recs)
                    scored_recommendations.sort(key=lambda x: x.get('total_score', 0), reverse=True)
                    for i, rec in enumerate(scored_recommendations):
                        rec['rank_order'] = i + 1
                    logger.info(f"Added {len(partner_recs)} partner recommendations, total now {len(scored_recommendations)}")
            
            # Create recommendation set
            recommendation_set = await self.builders_service.create_recommendation_set(
                request, scored_recommendations, start_time
            )
            
            if recommendation_set:
                await self.db.commit()
                logger.info(f"Generated {len(scored_recommendations)} recommendations for group {guest_group_id}")
                return recommendation_set
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return None
    
    async def _get_partner_recommendations(
        self,
        request,
        host,
        *,
        food_type: Optional[str] = None,
        query_terms: Optional[str] = None,
    ):
        # Fetch and score partner recommendations for dining/food categories
        try:
            partner_types = []
            pref_lower = [c.lower() for c in (request.preferred_categories or [])]
            if any(c in pref_lower for c in ('dining', 'food', 'restaurant')) or food_type:
                partner_types.extend(['restaurant', 'wine_bar', 'cafe'])
            if 'wine' in pref_lower and 'wine_bar' not in partner_types:
                partner_types.append('wine_bar')
            if not partner_types:
                return []

            search_terms: List[str] = []
            if query_terms:
                for qt in query_terms.strip().lower().split():
                    if qt and qt not in search_terms:
                        search_terms.append(qt)
            # Deduplicate while preserving order
            seen_terms: set[str] = set()
            unique_terms: List[str] = []
            for term in search_terms:
                if term not in seen_terms:
                    seen_terms.add(term)
                    unique_terms.append(term)
            search_terms = unique_terms
            
            # Search ALL partners of matching type, filter by Haversine distance from host
            host_lat = getattr(host, 'latitude', None) or 45.293
            host_lng = getattr(host, 'longitude', None) or 14.276

            # Vector search: semantic match on partner embeddings
            vector_hits: Dict[Any, float] = {}
            query_parts: List[str] = list(search_terms)
            if food_type:
                query_parts.append(food_type)
            if request.preferred_categories:
                query_parts.extend(request.preferred_categories)
            query_text = " ".join(p for p in query_parts if p).strip()
            if query_text:
                try:
                    query_embedding = await self.vector_service.generate_embedding(query_text)
                    if query_embedding:
                        for partner, sim in await self.vector_service.find_similar_partners(
                            query_embedding=query_embedding,
                            limit=15,
                            partner_types=partner_types,
                            host_lat=host_lat,
                            host_lng=host_lng,
                        ):
                            vector_hits[partner.id] = sim
                except Exception as e:
                    logger.warning("Partner vector search failed: %s", e)

            stmt = select(Partner).where(
                Partner.status == PartnerStatus.ACTIVE,
                Partner.partner_type.in_(partner_types)
            )
            if search_terms:
                term_filters = []
                for term in search_terms:
                    pattern = f"%{term}%"
                    term_filters.append(Partner.name.ilike(pattern))
                    term_filters.append(Partner.description.ilike(pattern))
                stmt = stmt.where(or_(*term_filters))
            stmt = stmt.order_by(Partner.name).limit(50)
            
            result = await self.db.execute(stmt)
            partners = result.scalars().all()
            
            # Filter by Haversine distance from host (15km radius)
            import math as _m
            def _hdist(lat1, lng1, lat2, lng2):
                if None in (lat1, lng1, lat2, lng2): return 999.0
                R = 6371
                dlat = _m.radians(lat2 - lat1)
                dlng = _m.radians(lng2 - lng1)
                a = _m.sin(dlat/2)**2 + _m.cos(_m.radians(lat1)) * _m.cos(_m.radians(lat2)) * _m.sin(dlng/2)**2
                return R * 2 * _m.atan2(_m.sqrt(a), _m.sqrt(1-a))
            
            nearby = []
            for p in partners:
                d = _hdist(host_lat, host_lng, p.latitude, p.longitude)
                if d <= 15.0:
                    nearby.append((p, d))
            nearby.sort(key=lambda x: x[1])
            partners = [p for p, _ in nearby[:10]]

            # Merge vector hits (may include partners outside ILIKE filter)
            if vector_hits:
                seen_ids = {p.id for p in partners}
                extra_ids = [pid for pid in vector_hits if pid not in seen_ids]
                if extra_ids:
                    extra_result = await self.db.execute(
                        select(Partner).where(Partner.id.in_(extra_ids))
                    )
                    for p in extra_result.scalars().all():
                        d = _hdist(host_lat, host_lng, p.latitude, p.longitude)
                        if d <= 15.0:
                            partners.append(p)
            
            scored = []
            for partner in partners:
                score = 0.5
                vector_sim = vector_hits.get(partner.id, 0.0)
                if vector_sim:
                    score += min(0.35, vector_sim * 0.35)
                if partner.partner_type == 'wine_bar' and 'wine' in pref_lower:
                    score += 0.3
                if partner.partner_type == 'restaurant' and any(c in pref_lower for c in ('dining', 'food', 'restaurant')):
                    score += 0.2
                if search_terms:
                    haystack = f"{partner.name or ''} {partner.description or ''}".lower()
                    matched = False
                    for term in search_terms:
                        if term in haystack:
                            matched = True
                            break
                        # Also match prefix (e.g. "pizza" in "pizzeria")
                        if len(term) >= 4:
                            prefix = term[:4]
                            if prefix in haystack:
                                matched = True
                                break
                    if matched:
                        score += 0.50
                
                from types import SimpleNamespace
                wrapper = SimpleNamespace(
                    id=partner.id, name=partner.name, description=partner.description,
                    attraction_type=partner.partner_type, city=partner.city,
                    category_tags=[partner.partner_type], age_suitability=[],
                    guest_rating=float(partner.google_rating or 4.0), created_by_host_id=host.id,
                    google_rating=partner.google_rating,
                    google_user_ratings_total=partner.google_user_ratings_total,
                    google_price_level=partner.google_price_level,
                    google_website=partner.google_website,
                    google_phone=partner.google_phone,
                    latitude=partner.latitude, longitude=partner.longitude,
                    host_personal_tip=None, host_insider_info=None, host_story=None,
                    host_recommended_duration='1-2 hours',
                    host_favorite_time='evening' if partner.partner_type in ('restaurant', 'wine_bar') else 'anytime',
                    admission_fee=None, best_months=[], status='approved'
                )
                
                rec = {
                    'attraction': wrapper, 'total_score': min(1.0, score),
                    'priority': 'high' if score >= 0.7 else 'medium',
                    'scores': {'preference': score, 'host_insight': 0.5, 'popularity': 0.5, 'seasonal': 0.5, 'location': 0.5, 'vector_similarity': vector_sim},
                    'host_insight': None, 'host_tip': None,
                    'why_recommended': f"Local {partner.partner_type.replace('_', ' ')} in {host.city}"
                }
                scored.append(rec)
            
            logger.info(f"Fetched {len(scored)} partner recommendations")
            return scored
        except Exception as e:
            logger.error(f"Error fetching partner recommendations: {e}")
            return []

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
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
            try:
                await self.db.refresh(request)
            except Exception:
                pass  # RLS may block SELECT after flush

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
                                   candidates: List[Attraction],
                                   query_terms: Optional[str] = None) -> List[Dict[str, Any]]:
        """Score and rank candidate attractions."""
        scored_recommendations = []
        query_driven = bool(query_terms and query_terms.strip())
        
        for attraction in candidates:
            try:
                # Calculate individual scores
                preference_score = RecommendationScoring.calculate_preference_score(attraction, guest_group, request)
                host_insight_score = RecommendationScoring.calculate_host_insight_score(attraction, host)
                popularity_score = RecommendationScoring.calculate_popularity_score(attraction)
                seasonal_score = RecommendationScoring.calculate_seasonal_score(attraction, request)
                location_score = RecommendationScoring.calculate_location_score(attraction, request, host)
                
                # Calculate vector similarity score if embeddings exist
                query_vector_sim = getattr(attraction, "_query_vector_sim", None)
                if query_vector_sim is not None:
                    vector_score = float(query_vector_sim)
                else:
                    vector_score = RecommendationScoring.calculate_vector_similarity_score(
                        attraction, guest_group.get('group')
                    )
                
                # Calculate distance and wow factors
                dist_score, dist_km = RecommendationScoring.calculate_location_score_with_distance(
                    attraction, request, host
                )
                location_score = max(location_score, dist_score)
                wow_factor = _wow_multiplier(attraction)  # from scoring module
                
                # Weighted total score with distance + wow multipliers
                total_score = RecommendationScoring.calculate_total_score(
                    preference_score, host_insight_score, popularity_score,
                    seasonal_score, location_score, vector_score,
                    distance_penalty=dist_score,
                    wow_factor=wow_factor
                )
                
                # Determine priority
                priority = self._determine_priority(total_score, attraction, request)
                
                # Create recommendation data
                recommendation_data = {
                    'attraction': attraction,
                    'total_score': total_score,
                    'distance_km': dist_km,
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
                    'why_recommended': self._generate_explanation(
                        attraction, guest_group, total_score, host
                    )
                }
                
                scored_recommendations.append(recommendation_data)
                
            except Exception as e:
                logger.error(f"Error scoring attraction {attraction.id}: {e}")
                continue
        
        # Sort: query-driven requests prioritize semantic vector match, then blended score
        if query_driven:
            scored_recommendations.sort(
                key=lambda x: (
                    x["scores"].get("vector_similarity", 0.0),
                    x["total_score"],
                ),
                reverse=True,
            )
        else:
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
    
    def _attraction_owned_by_host(self, attraction: Attraction, host: Host) -> bool:
        """True when the stay host created this attraction (insider fields may be shared)."""
        return attraction.created_by_host_id == host.id

    def _generate_host_insight(self, attraction: Attraction, host: Host) -> Optional[str]:
        """Generate host insight for the recommendation."""
        if not self._attraction_owned_by_host(attraction, host):
            return None
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
        if not self._attraction_owned_by_host(attraction, host):
            return None
        if attraction.host_insider_info:
            return attraction.host_insider_info
        return None
    
    def _guest_safe_rec_text(
        self,
        text: Optional[str],
        attraction: Optional[Attraction],
        owner_view: bool,
        rec: Optional[RecommendationResponse] = None,
    ) -> Optional[str]:
        """Drop recommendation copy that echoes another host's insider fields."""
        from app.services.host_offerings_for_guest import scrub_contact_from_text

        if not text:
            return text
        if not owner_view:
            low = text.casefold()
            fragments: list[Optional[str]] = []
            if rec is not None:
                fragments.extend([rec.host_insight, rec.host_tip])
            if attraction is not None:
                fragments.extend(
                    [
                        attraction.host_personal_tip,
                        attraction.host_insider_info,
                        attraction.host_recommended_duration,
                        attraction.host_favorite_time,
                    ]
                )
            for frag in fragments:
                if frag and str(frag).casefold() in low:
                    return None
        return scrub_contact_from_text(text)

    def _generate_explanation(
        self,
        attraction: Attraction,
        guest_group: Dict[str, Any],
        total_score: float,
        host: Host,
    ) -> str:
        """Generate explanation for why this was recommended."""
        reasons = []
        
        group = guest_group['group']
        
        # Check interest matches
        if group.interests:
            matching_interests = set(group.interests or []) & set(getattr(attraction, "category_tags", []) or [])
            if matching_interests:
                reasons.append(f"Matches your interests: {', '.join(matching_interests)}")
        
        # Check group suitability
        if group.group_dynamics == "family" and "family_friendly" in (getattr(attraction, "category_tags", []) or []):
            reasons.append("Perfect for families")
        elif group.group_dynamics == "romantic" and "romantic" in (getattr(attraction, "category_tags", []) or []):
            reasons.append("Ideal for couples")
        
        # Host knowledge — only for attractions owned by the stay host
        if self._attraction_owned_by_host(attraction, host) and attraction.host_personal_tip:
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
    async def get_guest_group_analytics(self, guest_group_id: uuid.UUID) -> Dict[str, Any]:
        """Recommendation analytics for a single guest group."""
        gg = await self._get_guest_group_with_preferences(guest_group_id)
        if not gg:
            return {
                "guest_group_id": str(guest_group_id),
                "recommendations_given": 0,
                "recommendations_accepted": 0,
                "acceptance_rate": 0.0,
                "satisfaction_rating": None,
            }
        group = gg["group"]
        given = int(group.recommendations_given or 0)
        accepted = int(group.recommendations_accepted or 0)
        rate = (accepted / given) if given else 0.0
        return {
            "guest_group_id": str(guest_group_id),
            "recommendations_given": given,
            "recommendations_accepted": accepted,
            "acceptance_rate": round(rate, 3),
            "satisfaction_rating": group.satisfaction_rating,
            "group_name": group.group_name,
            "status": group.status,
        }

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
    ) -> ExplorerRecommendationPublicResponse:
        """Build API recommendation rows for public explorer endpoints (no DB persistence)."""
        from app.services.host_offerings_for_guest import scrub_contact_from_text

        desc = attraction.description or attraction.short_description or ""
        duration_hours = getattr(attraction, "duration_hours", None)
        estimated_duration = (
            f"{duration_hours:g} hours" if duration_hours is not None else None
        )
        return ExplorerRecommendationPublicResponse(
            id=attraction.id,
            title=scrub_contact_from_text(attraction.name) or attraction.name,
            description=scrub_contact_from_text(desc) or "",
            recommendation_type=RecommendationType.ATTRACTION.value,
            why_recommended=scrub_contact_from_text(why_recommended),
            estimated_duration=estimated_duration,
            best_time_to_visit=scrub_contact_from_text(
                getattr(attraction, "best_time_to_visit", None)
            ),
            estimated_cost=scrub_contact_from_text(
                getattr(attraction, "admission_fee", None)
            ),
            booking_required=bool(getattr(attraction, "booking_required", False)),
        )

    async def _fetch_approved_attractions_for_city(
        self,
        city: Optional[str],
        fetch_limit: int = 80,
    ) -> List[Attraction]:
        """
        Attractions for public seasonal/weather endpoints.

        Approved only — matches public city listing and anonymous attraction reads.
        """
        visible = (AttractionStatus.APPROVED,)
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
    ) -> List[ExplorerRecommendationPublicResponse]:
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
        out: List[ExplorerRecommendationPublicResponse] = []
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
    ) -> List[ExplorerRecommendationPublicResponse]:
        """Lightweight weather-friendly ranking for a city (public endpoint)."""
        lim = max(1, min(int(limit), 50))
        attractions = await self._fetch_approved_attractions_for_city(
            city, fetch_limit=max(lim * 5, 40)
        )
        scored: List[Tuple[Attraction, float]] = []
        for a in attractions:
            tags = getattr(a, "category_tags", []) or []
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
        out: List[ExplorerRecommendationPublicResponse] = []
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
            
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
            
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
            rec_set = await self.generate_recommendations(
                guest_group_id,
                host_id,
                create,
                max_price_level=request_data.max_price_level,
                food_type=request_data.food_type,
                query_terms=request_data.query_terms,
            )
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

    _INTERNAL_FACTOR_KEYS = frozenset(
        {
            "algorithm_weights",
            "request_type",
            "season",
            "weather_context",
            "group_size",
            "duration_hours",
            "budget_range",
        }
    )

    _FACTOR_LABELS = {
        "preferred_categories": "Good for you",
        "interests": "Matches your interests",
    }

    @classmethod
    def _guest_safe_factor_dict(cls, raw: Any) -> Dict[str, Any]:
        """Strip internal scoring keys from batch-level personalization_factors."""
        from app.services.host_offerings_for_guest import _scrub_safe_value

        if not isinstance(raw, dict):
            return {}
        safe: Dict[str, Any] = {}
        for k, v in raw.items():
            if k in cls._INTERNAL_FACTOR_KEYS:
                continue
            safe[k] = _scrub_safe_value(v)
        return safe

    @classmethod
    def _guest_safe_factor_chips(cls, chips: List[str]) -> List[str]:
        from app.services.host_offerings_for_guest import scrub_contact_from_text

        out: List[str] = []
        for chip in chips:
            scrubbed = scrub_contact_from_text(chip)
            if scrubbed:
                out.append(scrubbed)
        return out

    @classmethod
    def _personalization_factor_strings(cls, raw: Any) -> List[str]:
        """Flatten batch personalization_factors into short guest-facing chips."""
        if not raw:
            return []
        if isinstance(raw, list):
            return cls._guest_safe_factor_chips(
                [
                    s
                    for s in (str(x).strip() for x in raw)
                    if s and "algorithm" not in s.lower() and "request type" not in s.lower()
                ]
            )
        if isinstance(raw, dict):
            out: List[str] = []
            for key, val in raw.items():
                if key in cls._INTERNAL_FACTOR_KEYS:
                    continue
                if key == "preferred_categories" and isinstance(val, list):
                    for item in val[:4]:
                        t = str(item).strip().replace("_", " ")
                        if t:
                            out.append(t.title())
                    continue
                if isinstance(val, list):
                    for item in val[:3]:
                        t = str(item).strip().replace("_", " ")
                        if t and len(t) < 40:
                            out.append(t.title())
                elif val is not None:
                    text = str(val).strip()
                    if not text or text.startswith("{") or "algorithm" in text.lower():
                        continue
                    label = cls._FACTOR_LABELS.get(key) or str(key).replace("_", " ").strip().title()
                    if key in cls._FACTOR_LABELS:
                        out.append(label)
                    elif len(text) < 36:
                        out.append(text.title())
            return cls._guest_safe_factor_chips(out[:6])
        text = str(raw).strip()
        if text and "algorithm" not in text.lower():
            return cls._guest_safe_factor_chips([text])
        return []

    @staticmethod
    def _is_guest_visible_attraction(attraction: Optional[Attraction]) -> bool:
        if not attraction:
            return False
        blob = f"{attraction.name or ''} {attraction.description or ''}".lower()
        blocked = (
            "ben component",
            "ben qa",
            "full-component",
            "full component qa",
            "qa attraction",
            "test attraction",
            "slash-test",
            "verify ",
        )
        return not any(b in blob for b in blocked)

    @staticmethod
    def _attraction_to_guest_summary(
        attraction: Attraction,
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> GuestAttractionSummary:
        from app.services.host_offerings_for_guest import (
            scrub_contact_from_text,
            _scrub_safe_value,
            _scrub_opening_hours,
            _guest_safe_best_months,
        )

        tags = list(getattr(attraction, "category_tags", []) or [])
        category_raw = (tags[0] if tags else None) or attraction.attraction_type or "experience"
        category = scrub_contact_from_text(str(category_raw)) or "experience"
        parts = [p for p in (attraction.address, attraction.city, attraction.region) if p]
        location = ", ".join(parts) if parts else (attraction.city or "")
        description = scrub_contact_from_text(
            (attraction.description or attraction.short_description or "").strip()
        )
        address = scrub_contact_from_text(attraction.address)
        location = scrub_contact_from_text(location)
        coords: Optional[List[float]] = None
        if attraction.latitude is not None and attraction.longitude is not None:
            coords = [float(attraction.latitude), float(attraction.longitude)]
        opening = attraction.opening_hours if isinstance(attraction.opening_hours, dict) else {}
        gallery = list(attraction.image_gallery or []) if isinstance(attraction.image_gallery, list) else []
        scrubbed_gallery = [
            scrub_contact_from_text(str(u), scrub_urls=True) or str(u) for u in gallery
        ]
        featured_url = scrub_contact_from_text(
            attraction.featured_image_url, scrub_urls=True
        )
        owner_view = (
            viewer_host_id is not None
            and getattr(attraction, "created_by_host_id", None) == viewer_host_id
        )
        host_tip = attraction.host_personal_tip if owner_view else None
        host_fav_time = attraction.host_favorite_time if owner_view else None
        host_insider = attraction.host_insider_info if owner_view else None
        scrubbed_opening = _scrub_opening_hours(opening)
        admission_fee = scrub_contact_from_text(attraction.admission_fee)
        scrubbed_name = scrub_contact_from_text(attraction.name) or attraction.name
        from app.services.google_places_enrichment import GooglePlacesEnrichmentService

        maps_fields = GooglePlacesEnrichmentService.computed_maps_fields(attraction)
        google_photos = list(attraction.google_photos or []) if isinstance(attraction.google_photos, list) else []
        scrubbed_photos = [
            scrub_contact_from_text(str(u), scrub_urls=True) or str(u) for u in google_photos
        ]
        google_rating = attraction.google_rating
        avg_rating = google_rating if google_rating is not None else attraction.guest_rating
        review_count = (
            int(attraction.google_user_ratings_total or 0)
            if attraction.google_user_ratings_total
            else int(attraction.total_ratings or 0)
        )
        return GuestAttractionSummary(
            id=attraction.id,
            name=scrubbed_name,
            description=description or "",
            category=category,
            location=location or "",
            coordinates=coords,
            opening_hours=scrubbed_opening,
            cost_estimate=(admission_fee or "").strip(),
            authenticity_level="local",
            seasonal_info={},
            attraction_type=scrub_contact_from_text(attraction.attraction_type),
            city=scrub_contact_from_text(attraction.city),
            address=address,
            region=scrub_contact_from_text(attraction.region),
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            featured_image_url=featured_url or (scrubbed_photos[0] if scrubbed_photos else None),
            image_gallery=scrubbed_gallery or scrubbed_photos,
            best_months=_guest_safe_best_months(list(attraction.best_months or [])),
            average_rating=avg_rating,
            review_count=review_count,
            host_personal_tip=scrub_contact_from_text(host_tip) if host_tip else None,
            host_favorite_time=scrub_contact_from_text(host_fav_time) if host_fav_time else None,
            host_insider_info=scrub_contact_from_text(host_insider) if host_insider else None,
            host_recommended_duration=(
                scrub_contact_from_text(attraction.host_recommended_duration)
                if owner_view and attraction.host_recommended_duration
                else None
            ),
            admission_fee=admission_fee,
            seasonal_availability=scrub_contact_from_text(attraction.seasonal_availability),
            seasonal_notes=scrub_contact_from_text(attraction.seasonal_notes),
            google_place_id=attraction.google_place_id,
            google_rating=google_rating,
            google_user_ratings_total=attraction.google_user_ratings_total,
            google_price_level=attraction.google_price_level,
            google_photos=scrubbed_photos,
            google_website=scrub_contact_from_text(attraction.google_website, scrub_urls=True),
            google_phone=scrub_contact_from_text(attraction.google_phone),
            google_maps_url=maps_fields.get("google_maps_url"),
            static_map_image_url=maps_fields.get("static_map_image_url"),
        )

    async def _load_attractions_by_ids(
        self, attraction_ids: List[uuid.UUID]
    ) -> Dict[uuid.UUID, Attraction]:
        if not attraction_ids:
            return {}
        stmt = select(Attraction).where(Attraction.id.in_(attraction_ids))
        result = await self.db.execute(stmt)
        return {a.id: a for a in result.scalars().all()}

    def _build_guest_item(
        self,
        rec: RecommendationResponse,
        guest_group_id: uuid.UUID,
        attraction: Optional[Attraction],
        factor_strings: List[str],
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> GuestRecommendationItem:
        from app.services.host_offerings_for_guest import scrub_contact_from_text

        owner_view = False
        if attraction is not None and viewer_host_id is not None:
            owner_view = getattr(attraction, 'created_by_host_id', None) == viewer_host_id

        reason = ""
        if owner_view and attraction:
            tip = (attraction.host_personal_tip or attraction.host_insider_info or "").strip()
            if tip and len(tip) > 12 and "qa" not in tip.lower():
                reason = tip
            else:
                reason = (
                    self._guest_safe_rec_text(
                        (rec.why_recommended or rec.description or rec.title or "").strip(),
                        attraction,
                        owner_view,
                        rec,
                    )
                    or ""
                )
                if not reason or "special insights" in reason.lower():
                    name = scrub_contact_from_text(
                        (attraction.name or "this place").strip()
                    ) or "this place"
                    city = scrub_contact_from_text(
                        (attraction.city or "the area").strip()
                    ) or "the area"
                    reason = f"Your host recommends {name} while you stay in {city}."
        else:
            reason = (
                self._guest_safe_rec_text(
                    (rec.why_recommended or rec.description or rec.title or "").strip(),
                    attraction,
                    owner_view,
                    rec,
                )
                or ""
            )
            if attraction and (not reason or "special insights" in reason.lower()):
                city = scrub_contact_from_text(
                    (attraction.city or "the area").strip()
                ) or "the area"
                reason = f"Recommended while you stay in {city}."
        if not reason:
            reason = "Recommended for your stay."
        summary = (
            self._attraction_to_guest_summary(attraction, viewer_host_id)
            if attraction
            else None
        )

        guest_insight = (
            scrub_contact_from_text(rec.host_insight) if owner_view and rec.host_insight else None
        )
        guest_tip = (
            scrub_contact_from_text(rec.host_tip) if owner_view and rec.host_tip else None
        )
        guest_description = self._guest_safe_rec_text(
            rec.description, attraction, owner_view, rec
        )
        guest_why = self._guest_safe_rec_text(
            rec.why_recommended, attraction, owner_view, rec
        )
        guest_title = self._guest_safe_rec_text(rec.title, attraction, owner_view, rec)
        safe_reason = self._guest_safe_rec_text(reason, attraction, owner_view, rec)
        if safe_reason is not None:
            reason = safe_reason
        elif not owner_view:
            if attraction:
                city = scrub_contact_from_text(
                    (attraction.city or "the area").strip()
                ) or "the area"
                reason = f"Recommended while you stay in {city}."
            else:
                reason = "Recommended for your stay."
        else:
            reason = scrub_contact_from_text(reason) or "Recommended for your stay."
        return GuestRecommendationItem(
            id=rec.id,
            attraction_id=rec.attraction_id,
            reason=reason,
            personalization_factors=factor_strings,
            attraction=summary,
            title=guest_title,
            description=guest_description,
            why_recommended=guest_why,
            host_insight=guest_insight,
            host_tip=guest_tip,
        )

    async def enrich_batch_for_guest(
        self,
        batch: RecommendationBatch,
        guest_group_id: uuid.UUID,
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> GuestRecommendationBatch:
        """Attach attraction cards and guest UI aliases to a recommendation batch."""
        recs = list(batch.recommendations or [])
        ids = [r.attraction_id for r in recs if r.attraction_id]
        # Re-apply worker bypass — pipeline commits may have cleared it
        from app.services.rls_service import RLSService
        try:
            await RLSService(self.db).set_bypass("worker")
        except Exception:
            pass
        by_id = await self._load_attractions_by_ids(ids)
        
        # Load partners for recommendations without attraction_id
        partner_titles = [r.title for r in recs if r.title and not r.attraction_id]
        by_partner_title: Dict[str, Any] = {}
        if partner_titles:
            from app.models.partner import Partner
            from sqlalchemy import select as sa_select
            pstmt = sa_select(Partner).where(Partner.name.in_(partner_titles), Partner.status == 'active')
            presult = await self.db.execute(pstmt)
            for p in presult.scalars().all():
                by_partner_title[p.name] = p
        
        factors = self._personalization_factor_strings(batch.personalization_factors)
        items: List[GuestRecommendationItem] = []
        for r in recs:
            att = by_id.get(r.attraction_id) if r.attraction_id else None
            if att is None and r.title and r.title in by_partner_title:
                partner = by_partner_title[r.title]
                # Build synthetic GuestAttractionSummary from partner
                from app.services.google_places_enrichment import GooglePlacesEnrichmentService
                maps_url = None
                if partner.latitude and partner.longitude:
                    maps_url = f"https://maps.google.com/?q={partner.latitude},{partner.longitude}"
                att = GuestAttractionSummary(
                    id=partner.id,
                    name=partner.name,
                    description=partner.description or "",
                    category=partner.category or "dining",
                    location=partner.city or "",
                    city=partner.city,
                    address=partner.address,
                    latitude=partner.latitude,
                    longitude=partner.longitude,
                    google_rating=partner.google_rating,
                    google_user_ratings_total=partner.google_user_ratings_total,
                    google_price_level=partner.google_price_level,
                    google_website=partner.google_website,
                    google_phone=partner.google_phone,
                    google_maps_url=maps_url,
                    created_by_host_id=None,
                    category_tags=[],
                )
            if att is not None and not self._is_guest_visible_attraction(att):
                continue
            items.append(
                self._build_guest_item(r, guest_group_id, att, factors, viewer_host_id)
            )
        return GuestRecommendationBatch(
            recommendations=items,
            total_count=len(items),
            personalization_factors=self._guest_safe_factor_dict(
                batch.personalization_factors
            ),
        )

    async def enrich_list_for_guest(
        self,
        recs: List[RecommendationResponse],
        guest_group_id: uuid.UUID,
        personalization_factors: Optional[Dict[str, Any]] = None,
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> List[GuestRecommendationItem]:
        """Enrich history rows with embedded attractions for guest UI."""
        ids = [r.attraction_id for r in recs if r.attraction_id]
        by_id = await self._load_attractions_by_ids(ids)
        factors = self._personalization_factor_strings(personalization_factors or {})
        items: List[GuestRecommendationItem] = []
        for r in recs:
            att = by_id.get(r.attraction_id) if r.attraction_id else None
            if att is not None and not self._is_guest_visible_attraction(att):
                continue
            items.append(
                self._build_guest_item(r, guest_group_id, att, factors, viewer_host_id)
            )
        return items

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
            await self.db.flush()  # was commit(); flush keeps RLS bypass alive
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

    async def test_algorithm(
        self,
        test_data: RecommendationRequestAPI,
        host_id: uuid.UUID,
    ) -> RecommendationAlgorithmTestResponse:
        """Dry-run or live algorithm test for host tuning."""
        started = time.perf_counter()
        params = test_data.model_dump(mode="json")
        sample_titles: List[str] = []
        rec_count = 0
        message = "Dry-run completed using approved attraction candidates"
        success = True
        guest_group_id = test_data.guest_group_id

        if guest_group_id:
            gg_stmt = select(GuestGroup).where(
                GuestGroup.id == guest_group_id,
                GuestGroup.host_id == host_id,
            )
            gg_result = await self.db.execute(gg_stmt)
            group = gg_result.scalar_one_or_none()
            if not group:
                return RecommendationAlgorithmTestResponse(
                    success=False,
                    message="Guest group not found for this host",
                    guest_group_id=guest_group_id,
                    parameters_used=params,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            request = RecommendationRequestCreate(
                preferred_radius_km=test_data.preferred_radius_km,
                preferred_categories=test_data.preferred_categories,
                excluded_categories=test_data.excluded_categories,
                accessibility_requirements=test_data.accessibility_requirements,
                response_language=test_data.language,
                target_date=test_data.target_date,
                current_location=test_data.current_location,
            )
            batch = await self.generate_recommendations(
                guest_group_id=guest_group_id,
                host_id=host_id,
                request_data=request,
            )
            rec_count = len(batch.recommendations) if batch and batch.recommendations else 0
            sample_titles = [
                rec.title[:80]
                for rec in (batch.recommendations[:3] if batch and batch.recommendations else [])
                if rec.title
            ]
            message = "Live algorithm test completed"
        else:
            attractions = await self._fetch_approved_attractions_for_city(
                test_data.current_location,
                fetch_limit=max(test_data.max_recommendations * 3, 15),
            )
            rec_count = min(len(attractions), test_data.max_recommendations)
            sample_titles = [a.name[:80] for a in attractions[:3]]

        return RecommendationAlgorithmTestResponse(
            success=success,
            message=message,
            guest_group_id=guest_group_id,
            recommendations_count=rec_count,
            duration_ms=int((time.perf_counter() - started) * 1000),
            parameters_used=params,
            sample_titles=sample_titles,
        )

    async def get_performance_metrics(
        self,
        host_id: uuid.UUID,
    ) -> RecommendationPerformanceMetricsResponse:
        stats = await self.get_host_recommendation_stats(host_id)
        return RecommendationPerformanceMetricsResponse(
            total_recommendation_sets=int(stats.get("total_recommendation_sets") or 0),
            total_recommendations_generated=int(
                stats.get("total_recommendations_generated") or 0
            ),
            average_satisfaction=float(stats.get("average_satisfaction") or 0.0),
            recommendations_accepted_rate=float(
                stats.get("recommendations_accepted_rate") or 0.0
            ),
            host_insights_helpful_rate=float(
                stats.get("host_insights_helpful_rate") or 0.0
            ),
        )