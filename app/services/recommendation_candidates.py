"""
Candidate attraction retrieval for recommendation engine.

Handles fetching candidate attractions using vector search,
preference overlap on relational attraction fields, and traditional filtering.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_

from app.models.attraction import Attraction, AttractionStatus
from app.models.recommendation import RecommendationRequest
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

_SEASON_MONTHS: dict[str, set[int]] = {
    "spring": {3, 4, 5},
    "summer": {6, 7, 8},
    "autumn": {9, 10, 11},
    "winter": {12, 1, 2},
}


def _attraction_matches_request_season(attraction: Attraction, season: str) -> bool:
    """True when attraction is suitable for the requested season (not wall-clock month)."""
    if attraction.seasonal_availability == "year_round":
        return True
    season_key = (season or "").strip().lower()
    if not season_key:
        return True
    if (attraction.seasonal_availability or "").lower() == season_key:
        return True
    months = _SEASON_MONTHS.get(season_key)
    if not months:
        return True
    best = set(attraction.best_months or [])
    return bool(best & months)


class RecommendationCandidates:
    """
    Candidate attraction retrieval logic.

    Combines vector search, guest-preference overlap against host attractions,
    and traditional filtering.
    """

    def __init__(self, db: AsyncSession, vector_service: VectorService):
        """
        Initialize candidate retrieval service.

        Args:
            db: Database session
            vector_service: Vector service for semantic search
        """
        self.db = db
        self.vector_service = vector_service
    
    async def get_candidate_attractions_advanced(
        self,
        request: RecommendationRequest,
        guest_group: Dict[str, Any],
        host: Host
    ) -> List[Attraction]:
        """
        Get candidate attractions using vector search, preference overlap, and traditional filtering.
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
            
            # Step 3: Preference overlap (same DB as attractions; replaces legacy graph DB)
            try:
                if group and hasattr(group, "id"):
                    overlap_recs = await self._preference_overlap_recommendations(
                        group.id, host, limit=20
                    )
                    overlap_ids = [rec.get("id") for rec in overlap_recs if rec.get("id")]
                    if overlap_ids:
                        stmt = select(Attraction).where(
                            Attraction.id.in_(
                                [uuid.UUID(i) for i in overlap_ids if i]
                            )
                        )
                        result = await self.db.execute(stmt)
                        overlap_candidates = result.scalars().all()
                        candidate_ids = {c.id for c in candidates}
                        for candidate in overlap_candidates:
                            if candidate.id not in candidate_ids:
                                candidates.append(candidate)
                                candidate_ids.add(candidate.id)
            except Exception as e:
                logger.warning(f"Preference-overlap recommendations failed: {e}")
            
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
                if request.season and not _attraction_matches_request_season(
                    attraction, request.season
                ):
                    continue
                filtered.append(attraction)
            
            return filtered[:50]
            
        except Exception as e:
            logger.error(f"Error getting candidate attractions: {e}")
            await self.db.rollback()
            return await self.get_candidate_attractions_traditional(request, guest_group, host)

    @staticmethod
    def _collect_preference_keywords(group: GuestGroup) -> Set[str]:
        """Lowercased tokens from guest JSON preference fields."""
        out: Set[str] = set()
        for field in (group.interests, group.preferred_activities, group.interested_regions):
            if field is None:
                continue
            if isinstance(field, dict):
                items = list(field.values())
            elif isinstance(field, list):
                items = field
            else:
                continue
            for x in items:
                s = str(x).strip().lower()
                if len(s) >= 2:
                    out.add(s)
        return out

    @staticmethod
    def _keyword_match_score(attraction: Attraction, keywords: Set[str]) -> int:
        """How many distinct preference tokens match this attraction (type, tags, text)."""
        tags = {
            str(t).strip().lower()
            for t in (attraction.category_tags or [])
            if str(t).strip()
        }
        atype = (attraction.attraction_type or "").lower()
        blob = " ".join(
            [
                atype,
                (attraction.name or "").lower(),
                (attraction.description or "").lower(),
                (attraction.short_description or "").lower(),
                (attraction.city or "").lower(),
                (attraction.region or "").lower(),
                *tags,
            ]
        )
        matched = 0
        for kw in keywords:
            if kw in tags or kw == atype:
                matched += 1
            elif kw in blob:
                matched += 1
        return matched

    async def _preference_overlap_recommendations(
        self,
        guest_group_id: uuid.UUID,
        host: Host,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Attractions for this host ranked by overlap with guest interests / activities / regions.

        Returns dicts shaped like the old graph helper: ``id`` (str) and ``matching_interests`` (int).
        """
        stmt = select(GuestGroup).where(
            GuestGroup.id == guest_group_id,
            GuestGroup.host_id == host.id,
        )
        result = await self.db.execute(stmt)
        gg = result.scalar_one_or_none()
        if not gg:
            return []
        keywords = self._collect_preference_keywords(gg)
        if not keywords:
            return []

        stmt = select(Attraction).where(
            Attraction.created_by_host_id == host.id,
            or_(
                Attraction.status == AttractionStatus.APPROVED,
                and_(
                    Attraction.created_by_host_id == host.id,
                    Attraction.status.in_(
                        [AttractionStatus.DRAFT, AttractionStatus.PENDING]
                    ),
                ),
            ),
        )
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        scored: List[Tuple[int, Attraction]] = []
        for a in rows:
            score = self._keyword_match_score(a, keywords)
            if score > 0:
                scored.append((score, a))
        scored.sort(
            key=lambda t: (
                -t[0],
                -(t[1].guest_rating or 0.0),
                t[1].name or "",
            )
        )
        return [
            {"id": str(a.id), "matching_interests": s}
            for s, a in scored[:limit]
        ]

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
                rows = [
                    a
                    for a in rows
                    if _attraction_matches_request_season(a, request.season)
                ][:50]
            else:
                rows = rows[:50]
            return rows
        except Exception as e:
            logger.error(f"Error getting traditional candidate attractions: {e}")
            await self.db.rollback()
            return []

