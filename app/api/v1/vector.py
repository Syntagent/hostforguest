"""
Vector search API endpoints for semantic similarity search.

Provides endpoints for generating embeddings and performing
vector similarity searches for attractions and guest preferences.
"""

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings."""
    text: str
    model: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    embedding: List[float]
    dimensions: int
    model: str


class SimilarAttractionsRequest(BaseModel):
    """Request model for finding similar attractions."""
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    host_id: Optional[str] = None
    limit: int = 10
    min_similarity: float = 0.5


class SimilarAttractionResponse(BaseModel):
    """Response model for similar attraction."""
    attraction_id: str
    name: str
    similarity_score: float


@router.post("/generate-embedding", response_model=EmbeddingResponse)
async def generate_embedding(
    request: EmbeddingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate embedding for text.
    
    Args:
        request: Embedding generation request
        db: Database session
        
    Returns:
        EmbeddingResponse: Generated embedding
    """
    try:
        ai_service = AIService()
        vector_service = VectorService(db, ai_service)
        
        embedding = await vector_service.generate_embedding(
            text=request.text,
            model=request.model
        )
        
        if not embedding:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embedding"
            )
        
        return EmbeddingResponse(
            embedding=embedding,
            dimensions=len(embedding),
            model=request.model or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding: {str(e)}"
        )


@router.post("/attractions/{attraction_id}/update-embedding")
async def update_attraction_embedding(
    attraction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Update embedding for an attraction.
    
    Args:
        attraction_id: Attraction ID
        db: Database session
        
    Returns:
        Success status
    """
    try:
        ai_service = AIService()
        vector_service = VectorService(db, ai_service)
        
        success = await vector_service.update_attraction_embedding(attraction_id)
        
        if success:
            return {"success": True, "message": "Embedding updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update embedding"
            )
            
    except Exception as e:
        logger.error(f"Error updating attraction embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update embedding: {str(e)}"
        )


@router.post("/guest-groups/{guest_group_id}/update-embedding")
async def update_guest_group_embedding(
    guest_group_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Update embedding for a guest group's preferences.
    
    Args:
        guest_group_id: Guest group ID
        db: Database session
        
    Returns:
        Success status
    """
    try:
        ai_service = AIService()
        vector_service = VectorService(db, ai_service)
        
        success = await vector_service.update_guest_group_embedding(guest_group_id)
        
        if success:
            return {"success": True, "message": "Embedding updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update embedding"
            )
            
    except Exception as e:
        logger.error(f"Error updating guest group embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update embedding: {str(e)}"
        )


@router.post("/find-similar", response_model=List[SimilarAttractionResponse])
async def find_similar_attractions(
    request: SimilarAttractionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find similar attractions using vector similarity search.
    
    Args:
        request: Similar attractions request
        db: Database session
        
    Returns:
        List of similar attractions with similarity scores
    """
    try:
        ai_service = AIService()
        vector_service = VectorService(db, ai_service)
        
        # Generate embedding from text if provided
        query_embedding = request.query_embedding
        if not query_embedding and request.query_text:
            query_embedding = await vector_service.generate_embedding(request.query_text)
        
        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either query_text or query_embedding must be provided"
            )
        
        # Find similar attractions
        similar_attractions = await vector_service.find_similar_attractions(
            query_embedding=query_embedding,
            limit=request.limit,
            host_id=request.host_id,
            min_similarity=request.min_similarity
        )
        
        # Convert to response format
        results = []
        for attraction, similarity in similar_attractions:
            results.append(SimilarAttractionResponse(
                attraction_id=str(attraction.id),
                name=attraction.name,
                similarity_score=similarity
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar attractions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar attractions: {str(e)}"
        )


@router.post("/batch-update-embeddings")
async def batch_update_embeddings(
    attraction_ids: Optional[List[str]] = None,
    guest_group_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch update embeddings for multiple attractions or guest groups.
    
    Args:
        attraction_ids: Optional list of attraction IDs
        guest_group_ids: Optional list of guest group IDs
        db: Database session
        
    Returns:
        Update results
    """
    try:
        ai_service = AIService()
        vector_service = VectorService(db, ai_service)
        
        results = await vector_service.batch_update_embeddings(
            attraction_ids=attraction_ids,
            guest_group_ids=guest_group_ids
        )
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch update embeddings: {str(e)}"
        )

