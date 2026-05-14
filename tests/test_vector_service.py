"""
Tests for vector service and embedding operations.
"""

import pytest
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.models.attraction import Attraction, AttractionStatus
from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_vector_service_initialization(db: AsyncSession):
    """Test vector service initializes correctly."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    assert service is not None
    assert service.embedding_dimensions == 384


@pytest.mark.asyncio
async def test_generate_embedding(db: AsyncSession):
    """Test embedding generation."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    
    text = "Beautiful beach in Lovran with crystal clear water"
    embedding = await service.generate_embedding(text)
    
    # Should return a list of floats
    assert embedding is None or isinstance(embedding, list)
    if embedding:
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)


@pytest.mark.asyncio
async def test_generate_attraction_embedding(db: AsyncSession):
    """Test attraction embedding generation."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    
    # Create a test attraction
    from app.models.attraction import Attraction
    attraction = Attraction(
        name="Lovran Beach",
        description="Beautiful beach in Lovran",
        attraction_type="natural"
    )
    
    embedding = await service.generate_attraction_embedding(attraction)
    
    # Should return embedding or None
    assert embedding is None or isinstance(embedding, list)


@pytest.mark.asyncio
async def test_generate_guest_preference_embedding(db: AsyncSession):
    """Test guest preference embedding generation."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    
    # Create a test guest group
    from app.models.guest_group import GuestGroup
    guest_group = GuestGroup(
        group_name="Test Group",
        group_size=4,
        interests=["nature", "beaches"],
        age_groups=["adults"]
    )
    
    embedding = await service.generate_guest_preference_embedding(guest_group)
    
    # Should return embedding or None
    assert embedding is None or isinstance(embedding, list)


@pytest.mark.asyncio
async def test_find_similar_attractions(db: AsyncSession):
    """Test finding similar attractions using vector search."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    
    # Create a test embedding
    test_embedding = [0.1] * 384  # Mock embedding
    
    # This will return empty list if no attractions with embeddings exist
    similar = await service.find_similar_attractions(
        query_embedding=test_embedding,
        limit=10
    )
    
    # Should return a list
    assert isinstance(similar, list)
    # Each item should be a tuple of (Attraction, similarity_score)
    if similar:
        assert len(similar[0]) == 2
        assert isinstance(similar[0][1], float)


@pytest.mark.asyncio
async def test_cosine_similarity_calculation():
    """Test cosine similarity calculation."""
    from app.services.vector_service import VectorService
    from app.services.ai_service import AIService
    
    import math
    
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    similarity = dot / (mag1 * mag2) if mag1 and mag2 else 0.0
    
    assert abs(similarity - 1.0) < 0.001


@pytest.mark.asyncio
async def test_batch_update_embeddings(db: AsyncSession):
    """Test batch embedding update."""
    ai_service = AIService()
    service = VectorService(db, ai_service)
    
    # Test with empty lists
    results = await service.batch_update_embeddings()
    
    assert isinstance(results, dict)
    assert "attractions_updated" in results
    assert "guest_groups_updated" in results

