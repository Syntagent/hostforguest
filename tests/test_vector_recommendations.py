"""
Tests for vector-based recommendations.
"""

import uuid

import pytest
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.recommendation_service import RecommendationService
from app.services.ai_service import AIService
from app.services.recommendation_scoring import RecommendationScoring
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_recommendation_service_with_vector(db: AsyncSession):
    """Test recommendation service uses vector search."""
    ai_service = AIService()
    service = RecommendationService(db, ai_service)

    assert service is not None
    assert hasattr(service, "vector_service")


@pytest.mark.asyncio
async def test_vector_similarity_score_calculation(db: AsyncSession):
    """Vector similarity uses RecommendationScoring (not RecommendationService internals)."""
    attraction = Attraction(
        name="Test Attraction",
        description="Test description",
        embedding="[0.1, 0.2, 0.3]",
    )

    guest_group = GuestGroup(
        host_id=uuid.uuid4(),
        group_name="Test Group",
        group_size=2,
        preference_embedding="[0.1, 0.2, 0.3]",
    )

    score = RecommendationScoring.calculate_vector_similarity_score(attraction, guest_group)

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_cosine_similarity_helper(db: AsyncSession):
    """Cosine similarity is normalized to 0–1 on RecommendationScoring."""
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]

    similarity = RecommendationScoring.cosine_similarity(vec1, vec2)

    assert 0.0 <= similarity <= 1.0
