"""
Candidate attraction retrieval for recommendation engine.

Handles fetching candidate attractions using vector search,
graph relationships, and traditional filtering.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_

from app.models.attraction import Attraction, AttractionStatus
from app.models.recommendation import RecommendationRequest
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.vector_service import VectorService
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class RecommendationCandidates:
    """
    Candidate attraction retrieval logic.
    
    Combines vector search, graph relationships, and traditional filtering.
    """
    
    def __init__(self, db: AsyncSession, vector_service: VectorService, graph_service: GraphService):
        """
        Initialize candidate retrieval service.
        
        Args:
            db: Database session
            vector_service: Vector service for semantic search
            graph_service: Graph service for relationship queries
        """
        self.db = db
        self.vector_service = vector_service
        self.graph_service = graph_service
    
    async def get_candidate_attractions_advanced(
        self,
        request: RecommendationRequest,
        guest_group: Dict[str, Any],
        host: Host
    ) -> List[Attraction]:
        """
        Get candidate attractions using vector search + graph relationships + traditional filtering.
        """
        try:
            candidates = []
            
            # Step 1: Vector search
            group = guest_group.get('group')
            if group and hasattr(group, 'preference_embedding') and group.preference_embedding:
                try:
                    import json
                    query_embedding = json.loads(group.preference_embedding) if isinstance(group.preference_embedding, str) else group.preference_embedding
                    similar_attractions = await self.vector_service.find_similar_attractions(
                        query_embedding=query_embedding,
                        limit=30,
                        host_id=str(host.id),
                        min_similarity=0.5
                    )
                    vector_candidates = [attraction for attraction, _ in similar_attractions]
                    candidates.extend(vector_candidates)
                    logger.info(f"Found {len(vector_candidates)} candidates via vector search")
                except Exception as e:
                    logger.warning(f"Vector search failed: {e}")
            
            # Step 2: Generate embedding if not exists
            if not candidates and group:
                try:
                    embedding = await self.vector_service.generate_guest_preference_embedding(group)
                    if embedding:
                        await self.vector_service.update_guest_group_embedding(str(group.id))
                        similar_attractions = await self.vector_service.find_similar_attractions(
                            query_embedding=embedding,
                            limit=30,
                            host_id=str(host.id),
                            min_similarity=0.5
                        )
                        vector_candidates = [attraction for attraction, _ in similar_attractions]
                        candidates.extend(vector_candidates)
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")
            
            # Step 3: Graph-based recommendations
            try:
                if group and hasattr(group, 'id'):
                    graph_recommendations = await self.graph_service.get_recommendation_path(
                        guest_group_id=str(group.id),
                        limit=20
                    )
                    graph_attraction_ids = [rec.get('id') for rec in graph_recommendations if rec.get('id')]
                    if graph_attraction_ids:
                        stmt = select(Attraction).where(
                            Attraction.id.in_([uuid.UUID(id) for id in graph_attraction_ids if id])
                        )
                        result = await self.db.execute(stmt)
                        graph_candidates = result.scalars().all()
                        candidate_ids = {c.id for c in candidates}
                        for candidate in graph_candidates:
                            if candidate.id not in candidate_ids:
                                candidates.append(candidate)
                                candidate_ids.add(candidate.id)
            except Exception as e:
                logger.warning(f"Graph recommendations failed: {e}")
            
            # Step 4: Fallback to traditional if needed
            if len(candidates) < 10:
                traditional = await self.get_candidate_attractions_traditional(request, guest_group, host)
                candidate_ids = {c.id for c in candidates}
                for candidate in traditional:
                    if candidate.id not in candidate_ids:
                        candidates.append(candidate)
            
            # Step 5: Apply filters
            filtered = []
            for attraction in candidates:
                own_draft_or_pending = (
                    attraction.created_by_host_id == host.id
                    and attraction.status
                    in (AttractionStatus.DRAFT, AttractionStatus.PENDING)
                )
                if attraction.status != AttractionStatus.APPROVED and not own_draft_or_pending:
                    continue
                if request.current_location and host.city:
                    if attraction.city and attraction.city.lower() != host.city.lower():
                        continue
                if request.season:
                    current_month = datetime.now().month
                    if (attraction.seasonal_availability != "year_round" and
                        current_month not in (attraction.best_months or [])):
                        continue
                filtered.append(attraction)
            
            return filtered[:50]
            
        except Exception as e:
            logger.error(f"Error getting candidate attractions: {e}")
            await self.db.rollback()
            return await self.get_candidate_attractions_traditional(request, guest_group, host)
    
    async def get_candidate_attractions_traditional(
        self,
        request: RecommendationRequest,
        guest_group: Dict[str, Any],
        host: Host
    ) -> List[Attraction]:
        """Traditional candidate attraction retrieval (fallback method)."""
        try:
            stmt = select(Attraction).where(
                or_(
                    Attraction.status == AttractionStatus.APPROVED,
                    and_(
                        Attraction.created_by_host_id == host.id,
                        Attraction.status.in_(
                            [
                                AttractionStatus.DRAFT,
                                AttractionStatus.PENDING,
                            ]
                        ),
                    ),
                )
            )
            if request.current_location and host.city:
                stmt = stmt.where(Attraction.city == host.city)
            stmt = stmt.order_by(
                desc(Attraction.recommendation_count),
                desc(Attraction.guest_rating)
            ).limit(80 if request.season else 50)
            result = await self.db.execute(stmt)
            rows = list(result.scalars().all())
            if request.season:
                current_month = datetime.now().month

                def _season_ok(a: Attraction) -> bool:
                    if a.seasonal_availability == "year_round":
                        return True
                    return current_month in (a.best_months or [])

                rows = [a for a in rows if _season_ok(a)][:50]
            else:
                rows = rows[:50]
            return rows
        except Exception as e:
            logger.error(f"Error getting traditional candidate attractions: {e}")
            await self.db.rollback()
            return []

