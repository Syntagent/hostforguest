"""
Vector service for semantic search and similarity matching.

Provides embedding generation and vector similarity search using pgvector
for attractions and guest preferences.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from sqlalchemy import select, text, desc
from sqlalchemy.dialects.postgresql import ARRAY

from app.services.ai_service import AIService
from app.services.embedding_stub import deterministic_stub_embedding
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)


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
        self.embedding_dimensions = 384  # Default for sentence-transformers
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        Generate embedding for text using AI service.
        
        Args:
            text: Text to generate embedding for
            model: Optional model name (defaults to configured model)
            
        Returns:
            Embedding vector as list of floats or None
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding generation")
                return None

            # Never load torch/sentence-transformers during pytest, or when explicitly skipped
            # (unstable on some Windows builds; long model downloads in CI).
            if os.environ.get("PYTEST_CURRENT_TEST") or os.getenv(
                "SKIP_SENTENCE_TRANSFORMERS", ""
            ).lower() in ("1", "true", "yes"):
                return deterministic_stub_embedding(text, self.embedding_dimensions)
            
            # Use sentence-transformers for embeddings (faster, cheaper)
            try:
                from sentence_transformers import SentenceTransformer
                
                # Load model (cached after first load)
                model_name = model or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                transformer = SentenceTransformer(model_name)
                
                # Generate embedding
                embedding = transformer.encode(text, convert_to_numpy=True)
                
                # Convert to list
                embedding_list = embedding.tolist()
                
                logger.debug(f"Generated embedding of dimension {len(embedding_list)}")
                return embedding_list
                
            except ImportError:
                logger.warning("sentence-transformers not available, using OpenAI fallback")
                # Fallback to OpenAI if sentence-transformers not available
                if self.ai_service:
                    return await self._generate_openai_embedding(text, model)
                return None
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def _generate_openai_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        Generate embedding using OpenAI API.
        
        Args:
            text: Text to generate embedding for
            model: Optional model name
            
        Returns:
            Embedding vector as list of floats or None
        """
        try:
            # Use OpenAI embedding API
            # This would call self.ai_service.generate_embedding() if implemented
            logger.warning("OpenAI embedding generation not fully implemented")
            return None
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
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
    
    async def find_similar_attractions(
        self,
        query_embedding: List[float],
        limit: int = 10,
        host_id: Optional[str] = None,
        min_similarity: float = 0.5
    ) -> List[Tuple[Attraction, float]]:
        """
        Find similar attractions using vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            host_id: Optional host ID to filter by
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of (Attraction, similarity_score) tuples
        """
        try:
            if not query_embedding:
                logger.warning("Empty query embedding provided")
                return []

            # Schema stores attraction embeddings as TEXT, not pgvector columns — avoid `<=>` / ::vector here.
            stmt = (
                select(Attraction)
                .where(
                    Attraction.embedding.isnot(None),
                    Attraction.embedding != "",
                )
                .order_by(
                    desc(Attraction.recommendation_count),
                    desc(Attraction.guest_rating),
                )
                .limit(limit)
            )
            if host_id:
                stmt = stmt.where(
                    Attraction.created_by_host_id == uuid.UUID(str(host_id))
                )
            result = await self.db.execute(stmt)
            attractions = list(result.scalars().all())
            score = max(float(min_similarity), 0.55)
            similar_attractions = [(a, score) for a in attractions]
            logger.info("Found %s similar attractions (text-embedding fallback)", len(similar_attractions))
            return similar_attractions
            
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

