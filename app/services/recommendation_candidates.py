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
    if attraction.seasonal_availability is None:
        return True
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
        host: Host,
        max_price_level: Optional[int] = None,
        query_terms: Optional[str] = None,
    ) -> List[Attraction]:
        """
        Get candidate attractions using vector search, preference overlap, and traditional filtering.
        """
        try:
            candidates = []
            vector_scores: Dict[Any, float] = {}

            # Step 0: Query-based vector search over ALL approved attractions (before category filter)
            if query_terms and query_terms.strip():
                try:
                    query_parts = [query_terms.strip()]
                    if request.preferred_categories:
                        query_parts.extend(request.preferred_categories)
                    query_text = " ".join(p for p in query_parts if p).strip()
                    query_embedding = await self.vector_service.generate_embedding(query_text)
                    if query_embedding:
                        similar_attractions = await self.vector_service.find_similar_attractions(
                            query_embedding=query_embedding,
                            limit=30,
                            host_id=str(host.id),
                            min_similarity=0.45,
                            approved_only=True,
                        )
                        for attraction, sim in similar_attractions:
                            candidates.append(attraction)
                            vector_scores[attraction.id] = sim
                        logger.info(
                            "Found %s candidates via query vector search (query=%r)",
                            len(similar_attractions),
                            query_text[:80],
                        )
                except Exception as e:
                    logger.warning(f"Query vector search failed: {e}")

            # Step 1: Guest preference vector search
            group = guest_group.get('group')
            if group and hasattr(group, 'preference_embedding') and group.preference_embedding:
                try:
                    import json
                    query_embedding = json.loads(group.preference_embedding) if isinstance(group.preference_embedding, str) else group.preference_embedding
                    similar_attractions = await self.vector_service.find_similar_attractions(
                        query_embedding=query_embedding,
                        limit=30,
                        host_id=str(host.id),
                        min_similarity=0.5,
                        approved_only=True,
                    )
                    for attraction, sim in similar_attractions:
                        if attraction.id not in vector_scores:
                            candidates.append(attraction)
                        vector_scores[attraction.id] = max(vector_scores.get(attraction.id, 0.0), sim)
                    logger.info(
                        "Found %s candidates via guest preference vector search",
                        len(similar_attractions),
                    )
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
                            min_similarity=0.5,
                            approved_only=True,
                        )
                        for attraction, sim in similar_attractions:
                            if attraction.id not in vector_scores:
                                candidates.append(attraction)
                            vector_scores[attraction.id] = max(
                                vector_scores.get(attraction.id, 0.0), sim
                            )
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
            if len(candidates) < 100:
                traditional = await self.get_candidate_attractions_traditional(request, guest_group, host)
                candidate_ids = {c.id for c in candidates}
                for candidate in traditional:
                    if candidate.id not in candidate_ids:
                        candidates.append(candidate)
            
            # Step 5: Deduplicate by ID
            seen_ids = set()
            unique_candidates = []
            for c in candidates:
                if c.id not in seen_ids:
                    seen_ids.add(c.id)
                    unique_candidates.append(c)
            candidates = unique_candidates
            logger.info(f"Candidates after dedup: {len(candidates)}")

            # Step 6: Apply location/season/price filters (categories are scoring factors, not hard filters)
            filtered = []
            preferred = [c.lower() for c in (request.preferred_categories or [])]

            for attraction in candidates:
                own_draft_or_pending = (
                    attraction.created_by_host_id == host.id
                    and attraction.status
                    in (AttractionStatus.DRAFT, AttractionStatus.PENDING)
                )
                if attraction.status != AttractionStatus.APPROVED and not own_draft_or_pending:
                    continue
                if request.current_location and host.city:
                    # Radius-based filter (15km default) with coordinate fallback
                    host_lat = getattr(host, "latitude", None)
                    host_lon = getattr(host, "longitude", None)
                    attr_lat = getattr(attraction, "latitude", None)
                    attr_lon = getattr(attraction, "longitude", None)
                    keep = False
                    if host_lat and host_lon and attr_lat and attr_lon:
                        from math import radians, sin, cos, sqrt, atan2
                        R = 6371.0
                        dlat = radians(attr_lat - host_lat)
                        dlon = radians(attr_lon - host_lon)
                        a = sin(dlat/2)**2 + cos(radians(host_lat)) * cos(radians(attr_lat)) * sin(dlon/2)**2
                        km = R * 2 * atan2(sqrt(a), sqrt(1-a))
                        radius = request.preferred_radius_km or 15.0
                        keep = km <= radius
                    if not keep:
                        # Coordinate fallback: nearby cities
                        nearby_map = {"lovran": "opatija", "opatija": "lovran"}
                        hcity = (host.city or "").lower()
                        acity = (attraction.city or "").lower()
                        if hcity in nearby_map and acity == nearby_map[hcity]:
                            keep = True
                    if not keep:
                        continue
                # Filter by requested city (when explicitly set)
                if request.current_location and request.current_location.strip():
                    req_city = request.current_location.strip().lower()
                    attr_city = (attraction.city or '').strip().lower()
                    if req_city != attr_city:
                        continue
                if request.season and not _attraction_matches_request_season(
                    attraction, request.season
                ):
                    continue

                if max_price_level is not None:
                    price_level = getattr(attraction, "google_price_level", None)
                    if price_level is not None and price_level > max_price_level:
                        continue
                
                filtered.append(attraction)
            
            # Minimum threshold: if too few, add approved fallbacks
            if len(filtered) < 3:
                filtered_ids = {a.id for a in filtered}
                for attraction in candidates:
                    if len(filtered) >= 5:
                        break
                    if attraction.id in filtered_ids:
                        continue
                    if attraction.status != AttractionStatus.APPROVED:
                        continue
                    if max_price_level is not None:
                        price_level = getattr(attraction, "google_price_level", None)
                        if price_level is not None and price_level > max_price_level:
                            continue
                    filtered.append(attraction)
                    filtered_ids.add(attraction.id)
                logger.info(f"Candidates after filter (relaxed): {len(filtered)} (preferred_categories={preferred})")
            else:
                logger.info(f"Candidates after filter: {len(filtered)} (preferred_categories={preferred})")
            # Attach vector scores for downstream scoring (stored on objects temporarily)
            for a in filtered:
                if a.id in vector_scores:
                    setattr(a, "_query_vector_sim", vector_scores[a.id])
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
                target = (request.current_location or host.city or '').strip()
                cities = [target]
                tcity = target.lower()
                if tcity == "lovran":
                    cities.append("Opatija")
                elif tcity == "opatija":
                    cities.append("Lovran")
                stmt = stmt.where(Attraction.city.in_(cities))
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

