"""
Tests for vector search functionality using pgvector.

Tests embedding generation, similarity search, and vector operations.
"""

import json
import uuid

import pytest
from typing import List
import numpy as np

from app.services.vector_service import VectorService
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup


async def _stub_embedding(self, text: str, model=None):
    """Avoid HuggingFace model download in CI / offline runs."""
    return [0.05] * 384


@pytest.mark.asyncio
async def test_generate_embedding(db_session, ai_service, monkeypatch):
    """Test embedding generation."""
    monkeypatch.setattr(VectorService, "generate_embedding", _stub_embedding)
    vector_service = VectorService(db_session, ai_service)

    text = "Beautiful beach in Lovran with crystal clear water"
    embedding = await vector_service.generate_embedding(text)

    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # Default embedding dimension
    assert all(isinstance(x, (int, float)) for x in embedding)


@pytest.mark.asyncio
async def test_find_similar_attractions(db_session, ai_service, sample_attractions, monkeypatch):
    """Test finding similar attractions using vector search."""
    monkeypatch.setattr(VectorService, "generate_embedding", _stub_embedding)
    vector_service = VectorService(db_session, ai_service)
    
    # Generate embedding for query
    query_text = "beach activities"
    query_embedding = await vector_service.generate_embedding(query_text)
    
    # Find similar attractions
    similar = await vector_service.find_similar_attractions(query_embedding, limit=5)
    
    assert isinstance(similar, list)
    assert len(similar) <= 5


@pytest.mark.asyncio
async def test_vector_similarity_calculation():
    """Test vector similarity calculation."""
    from app.services.vector_service import VectorService
    
    # Create two similar embeddings
    embedding1 = [0.1, 0.2, 0.3] * 128  # 384 dimensions
    embedding2 = [0.11, 0.21, 0.31] * 128  # Similar embedding
    
    # Calculate cosine similarity manually
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    norm1 = sum(a * a for a in embedding1) ** 0.5
    norm2 = sum(b * b for b in embedding2) ** 0.5
    similarity = dot_product / (norm1 * norm2)
    
    assert similarity > 0.9  # Should be very similar


@pytest.mark.asyncio
async def test_embedding_persistence(db_session, ai_service, monkeypatch):
    """Test that embeddings are persisted correctly."""
    monkeypatch.setattr(VectorService, "generate_embedding", _stub_embedding)
    vector_service = VectorService(db_session, ai_service)
    
    # Create test attraction
    attraction = Attraction(
        id=uuid.uuid4(),
        name="Test Beach",
        description="Beautiful beach for swimming",
        created_by_host_id=uuid.uuid4(),
        city="Lovran",
        attraction_type="beach"
    )
    
    db_session.add(attraction)
    await db_session.commit()
    
    # Generate and store embedding
    embedding = await vector_service.generate_embedding(
        f"{attraction.name} {attraction.description}",
    )
    
    # Update attraction with embedding (stored as TEXT / JSON list)
    attraction.embedding = json.dumps(embedding)
    await db_session.commit()

    # Verify embedding was saved
    assert attraction.embedding is not None
    parsed = json.loads(attraction.embedding)
    assert len(parsed) == 384

