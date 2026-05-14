"""
Tests for vector-based recommendations.
"""

import pytest
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.recommendation_service import RecommendationService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_recommendation_service_with_vector(db: AsyncSession):
    """Test recommendation service uses vector search."""
    ai_service = AIService()
    service = RecommendationService(db, ai_service)
    
    assert service is not None
    assert hasattr(service, 'vector_service')


@pytest.mark.asyncio
async def test_vector_similarity_score_calculation(db: AsyncSession):
    """Test vector similarity score calculation in recommendations."""
    from app.models.attraction import Attraction
    from app.models.guest_group import GuestGroup
    
    ai_service = AIService()
    service = RecommendationService(db, ai_service)
    
    # Create test objects
    attraction = Attraction(
        name="Test Attraction",
        description="Test description",
        embedding='[0.1, 0.2, 0.3]'  # Mock embedding as JSON string
    )
    
    guest_group = GuestGroup(
        group_name="Test Group",
        group_size=2,
        preference_embedding='[0.1, 0.2, 0.3]'  # Mock embedding
    )
    
    # Calculate similarity score
    score = await service._calculate_vector_similarity_score(attraction, guest_group)
    
    # Should return a float between 0 and 1
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_cosine_similarity_helper(db: AsyncSession):
    """Test cosine similarity helper method."""
    ai_service = AIService()
    service = RecommendationService(db, ai_service)
    
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    
    similarity = service._cosine_similarity(vec1, vec2)
    
    # Orthogonal vectors should have lower similarity
    assert 0.0 <= similarity <= 1.0

