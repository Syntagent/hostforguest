"""
Vector service for semantic search and similarity matching.

Provides embedding generation and vector similarity search using pgvector
for attractions and guest preferences.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from sqlalchemy import select, text, desc
from sqlalchemy.dialects.postgresql import ARRAY

from app.services.ai_service import AIService
from app.services.embedding_stub import deterministic_stub_embedding
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup
from app.models.partner import Partner, PartnerStatus

logger = logging.getLogger(__name__)


def _parse_embedding_text(raw: Any) -> Optional[List[float]]:
    """Parse embedding stored as JSON list text."""
    if raw is None:
        return None
    try:
        import json
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return None
            parsed = json.loads(raw)
        else:
            parsed = raw
        if not isinstance(parsed, list) or not parsed:
            return None
        return [float(x) for x in parsed]
    except Exception:
        return None


class VectorService:
    """
    Service for vector operations and semantic search.
    
    Handles embedding generation, storage, and similarity search
    using pgvector for AI-powered recommendations.
    """
    
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        """
        Initialize the vector service.
        
        Args:
            db: Database session
            ai_service: AI service for embedding generation
        """
        self.db = db
        self.ai_service = ai_service or AIService()
        self.embedding_dimensions = 3072  # Gemini embedding-2

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        Generate embedding for text using Gemini embedding-2 (3072d).

        Falls back to deterministic stub under pytest or when API key is missing.
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding generation")
                return None

            if os.environ.get("PYTEST_CURRENT_TEST") or os.getenv(
                "SKIP_SENTENCE_TRANSFORMERS", ""
            ).lower() in ("1", "true", "yes"):
                return deterministic_stub_embedding(text, self.embedding_dimensions)

            gemini_embedding = await self._generate_gemini_embedding(text, model)
            if gemini_embedding:
                return gemini_embedding

            logger.warning("Gemini embedding unavailable, using deterministic stub")
            return deterministic_stub_embedding(text, self.embedding_dimensions)

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def _generate_gemini_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embedding using Gemini embedding-2 API (3072d)."""
        import json
        import urllib.request
        try:
            api_key = os.environ.get("GOOGLE_AI_API_KEY", "")
            if not api_key:
                logger.error("GOOGLE_AI_API_KEY not set")
                return None
            
            data = json.dumps({
                "model": "models/gemini-embedding-2",
                "content": {"parts": [{"text": text}]}
            }).encode()
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={api_key}"
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read())
            emb = result["embedding"]["values"]
            logger.info(f"Gemini embedding ({len(emb)}d) for: {text[:60]}...")
            return emb
        except Exception as e:
            logger.warning(f"Gemini embedding failed, using stub: {e}")
            try:
                from app.services.embedding_stub import deterministic_stub_embedding
                return deterministic_stub_embedding(text, 3072)
            except Exception:
                return None
    
    async def generate_attraction_embedding(
        self,
        attraction: Attraction
    ) -> Optional[List[float]]:
        """
        Generate embedding for an attraction.
        
        Args:
            attraction: Attraction model instance
            
        Returns:
            Embedding vector or None
        """
        try:
            # Combine attraction information for embedding
            text_parts = [
                attraction.name or "",
                attraction.description or "",
                attraction.short_description or "",
                str(attraction.attraction_type) if hasattr(attraction, 'attraction_type') else "",
            ]
            
            # Add category tags if available
            if hasattr(attraction, 'category_tags') and attraction.category_tags:
                text_parts.append(" ".join(attraction.category_tags))
            
            # Combine into single text
            combined_text = " ".join(text_parts).strip()
            
            if not combined_text:
                logger.warning(f"Attraction {attraction.id} has no text for embedding")
                return None
            
            return await self.generate_embedding(combined_text)
            
        except Exception as e:
            logger.error(f"Error generating attraction embedding: {e}")
            return None
    
    async def generate_guest_preference_embedding(
        self,
        guest_group: GuestGroup
    ) -> Optional[List[float]]:
        """
        Generate embedding for guest group preferences.
        
        Args:
            guest_group: GuestGroup model instance
            
        Returns:
            Embedding vector or None
        """
        try:
            # Combine guest preferences for embedding
            text_parts = []
            
            # Add interests
            if hasattr(guest_group, 'interests') and guest_group.interests:
                text_parts.append(" ".join(guest_group.interests))
            
            # Add age groups
            if hasattr(guest_group, 'age_groups') and guest_group.age_groups:
                text_parts.append(" ".join(guest_group.age_groups))
            
            # Add mobility requirements
            if hasattr(guest_group, 'mobility_requirements') and guest_group.mobility_requirements:
                text_parts.append(" ".join(guest_group.mobility_requirements))
            
            # Add dietary restrictions
            if hasattr(guest_group, 'dietary_restrictions') and guest_group.dietary_restrictions:
                text_parts.append(" ".join(guest_group.dietary_restrictions))
            
            # Combine into single text
            combined_text = " ".join(text_parts).strip()
            
            if not combined_text:
                logger.warning(f"Guest group {guest_group.id} has no preferences for embedding")
                return None
            
            return await self.generate_embedding(combined_text)
            
        except Exception as e:
            logger.error(f"Error generating guest preference embedding: {e}")
            return None

    async def generate_partner_embedding(
        self,
        partner: Partner,
    ) -> Optional[List[float]]:
        """Generate embedding for a partner (name + description + partner_type)."""
        try:
            text_parts = [
                partner.name or "",
                partner.description or "",
                str(partner.partner_type) if partner.partner_type else "",
            ]
            combined_text = " ".join(text_parts).strip()
            if not combined_text:
                logger.warning("Partner %s has no text for embedding", partner.id)
                return None
            return await self.generate_embedding(combined_text)
        except Exception as e:
            logger.error("Error generating partner embedding: %s", e)
            return None

    async def find_similar_partners(
        self,
        query_embedding: List[float],
        limit: int = 10,
        partner_types: Optional[List[str]] = None,
        min_similarity: float = 0.5,
        host_lat: Optional[float] = None,
        host_lng: Optional[float] = None,
        max_distance_km: float = 15.0,
    ) -> List[Tuple[Partner, float]]:
        """Find similar active partners using cosine similarity on stored embeddings."""
        try:
            if not query_embedding:
                return []

            from app.services.recommendation_scoring import RecommendationScoring
            import math as _m

            stmt = select(Partner).where(
                Partner.status == PartnerStatus.ACTIVE.value,
                Partner.embedding.isnot(None),
                Partner.embedding != "",
            )
            if partner_types:
                stmt = stmt.where(Partner.partner_type.in_(partner_types))
            stmt = stmt.limit(200)
            result = await self.db.execute(stmt)
            partners = list(result.scalars().all())

            scored: List[Tuple[Partner, float]] = []
            for partner in partners:
                partner_embedding = _parse_embedding_text(partner.embedding)
                if not partner_embedding:
                    continue
                if host_lat is not None and host_lng is not None:
                    plat, plng = partner.latitude, partner.longitude
                    if plat is None or plng is None:
                        continue
                    dlat = _m.radians(plng - host_lng)
                    dlng = _m.radians(plat - host_lat)
                    a = (
                        _m.sin(dlat / 2) ** 2
                        + _m.cos(_m.radians(host_lat))
                        * _m.cos(_m.radians(plat))
                        * _m.sin(dlng / 2) ** 2
                    )
                    dist_km = 6371 * 2 * _m.atan2(_m.sqrt(a), _m.sqrt(1 - a))
                    if dist_km > max_distance_km:
                        continue
                similarity = RecommendationScoring.cosine_similarity(
                    query_embedding, partner_embedding
                )
                if similarity >= min_similarity:
                    scored.append((partner, float(similarity)))

            scored.sort(key=lambda x: x[1], reverse=True)
            logger.info("Found %s similar partners via vector search", len(scored[:limit]))
            return scored[:limit]
        except Exception as e:
            logger.error("Error finding similar partners: %s", e)
            await self.db.rollback()
            return []
    
    async def find_similar_attractions(
        self,
        query_embedding: List[float],
        limit: int = 10,
        host_id: Optional[str] = None,
        min_similarity: float = 0.5,
        approved_only: bool = True,
    ) -> List[Tuple[Attraction, float]]:
        """
        Find similar attractions using cosine similarity on stored TEXT embeddings.

        Searches all attractions with embeddings (optionally scoped to one host).
        """
        try:
            if not query_embedding:
                logger.warning("Empty query embedding provided")
                return []

            from app.models.attraction import AttractionStatus
            from app.services.recommendation_scoring import RecommendationScoring

            stmt = select(Attraction).where(
                Attraction.embedding.isnot(None),
                Attraction.embedding != "",
            )
            if approved_only:
                stmt = stmt.where(Attraction.status == AttractionStatus.APPROVED)
            if host_id:
                stmt = stmt.where(
                    Attraction.created_by_host_id == uuid.UUID(str(host_id))
                )
            stmt = stmt.limit(500)
            result = await self.db.execute(stmt)
            attractions = list(result.scalars().all())

            scored: List[Tuple[Attraction, float]] = []
            for attraction in attractions:
                attraction_embedding = _parse_embedding_text(attraction.embedding)
                if not attraction_embedding:
                    continue
                if len(attraction_embedding) != len(query_embedding):
                    logger.warning(
                        "Skipping attraction %s: embedding dim %s != query dim %s",
                        attraction.id,
                        len(attraction_embedding),
                        len(query_embedding),
                    )
                    continue
                similarity = RecommendationScoring.cosine_similarity(
                    query_embedding, attraction_embedding
                )
                if similarity >= min_similarity:
                    scored.append((attraction, float(similarity)))

            scored.sort(key=lambda x: x[1], reverse=True)
            logger.info("Found %s similar attractions via vector search", len(scored[:limit]))
            return scored[:limit]

        except Exception as e:
            logger.error(f"Error finding similar attractions: {e}")
            await self.db.rollback()
            return []
    
    async def update_attraction_embedding(
        self,
        attraction_id: str
    ) -> bool:
        """
        Update embedding for an attraction.
        
        Args:
            attraction_id: Attraction ID
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Fetch attraction
            stmt = select(Attraction).where(Attraction.id == attraction_id)
            result = await self.db.execute(stmt)
            attraction = result.scalar_one_or_none()
            
            if not attraction:
                logger.warning(f"Attraction {attraction_id} not found")
                return False
            
            # Generate embedding
            embedding = await self.generate_attraction_embedding(attraction)
            
            if not embedding:
                logger.warning(f"Failed to generate embedding for attraction {attraction_id}")
                return False
            
            # Update attraction with embedding
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            update_query = text(
                "UPDATE attractions SET embedding = :embedding, updated_at = NOW() "
                "WHERE id = CAST(:attraction_id AS uuid)"
            )
            await self.db.execute(
                update_query,
                {"embedding": embedding_str, "attraction_id": str(attraction_id)},
            )
            
            await self.db.commit()
            logger.info(f"Updated embedding for attraction {attraction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating attraction embedding: {e}")
            await self.db.rollback()
            return False

    async def update_partner_embedding(self, partner_id: str) -> bool:
        """Update embedding for a partner."""
        try:
            stmt = select(Partner).where(Partner.id == partner_id)
            result = await self.db.execute(stmt)
            partner = result.scalar_one_or_none()
            if not partner:
                logger.warning("Partner %s not found", partner_id)
                return False

            embedding = await self.generate_partner_embedding(partner)
            if not embedding:
                logger.warning("Failed to generate embedding for partner %s", partner_id)
                return False

            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            update_query = text(
                "UPDATE partners SET embedding = :embedding, updated_at = NOW() "
                "WHERE id = CAST(:partner_id AS uuid)"
            )
            await self.db.execute(
                update_query,
                {"embedding": embedding_str, "partner_id": str(partner_id)},
            )
            await self.db.commit()
            logger.info("Updated embedding for partner %s", partner_id)
            return True
        except Exception as e:
            logger.error("Error updating partner embedding: %s", e)
            await self.db.rollback()
            return False
    
    async def update_guest_group_embedding(
        self,
        guest_group_id: str
    ) -> bool:
        """
        Update embedding for a guest group's preferences.
        
        Args:
            guest_group_id: Guest group ID
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Fetch guest group
            stmt = select(GuestGroup).where(GuestGroup.id == guest_group_id)
            result = await self.db.execute(stmt)
            guest_group = result.scalar_one_or_none()
            
            if not guest_group:
                logger.warning(f"Guest group {guest_group_id} not found")
                return False
            
            # Generate embedding
            embedding = await self.generate_guest_preference_embedding(guest_group)
            
            if not embedding:
                logger.warning(f"Failed to generate embedding for guest group {guest_group_id}")
                return False
            
            # Update guest group with embedding
            # guest_groups.preference_embedding is TEXT in the schema (see GuestGroup model).
            # Do not CAST to vector here — that requires $libdir/vector at query time and breaks on text columns.
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            update_query = text(
                "UPDATE guest_groups SET preference_embedding = :embedding, updated_at = NOW() "
                "WHERE id = CAST(:guest_group_id AS uuid)"
            )
            await self.db.execute(
                update_query,
                {"embedding": embedding_str, "guest_group_id": str(guest_group_id)},
            )
            
            await self.db.commit()
            logger.info(f"Updated embedding for guest group {guest_group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating guest group embedding: {e}")
            await self.db.rollback()
            return False
    
    async def batch_update_embeddings(
        self,
        attraction_ids: Optional[List[str]] = None,
        guest_group_ids: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Batch update embeddings for multiple attractions or guest groups.
        
        Args:
            attraction_ids: Optional list of attraction IDs to update
            guest_group_ids: Optional list of guest group IDs to update
            
        Returns:
            Dictionary with update counts
        """
        results = {
            "attractions_updated": 0,
            "attractions_failed": 0,
            "guest_groups_updated": 0,
            "guest_groups_failed": 0
        }
        
        # Update attractions
        if attraction_ids:
            for attraction_id in attraction_ids:
                if await self.update_attraction_embedding(attraction_id):
                    results["attractions_updated"] += 1
                else:
                    results["attractions_failed"] += 1
        
        # Update guest groups
        if guest_group_ids:
            for guest_group_id in guest_group_ids:
                if await self.update_guest_group_embedding(guest_group_id):
                    results["guest_groups_updated"] += 1
                else:
                    results["guest_groups_failed"] += 1
        
        logger.info(f"Batch update completed: {results}")
        return results

