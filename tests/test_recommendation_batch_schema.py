"""RecommendationBatch must accept real personalization metadata (nested dicts, strings)."""

from datetime import datetime, timezone
import uuid

from app.models.recommendation import RecommendationBatch


def test_recommendation_batch_personalization_factors_allow_nested_metadata():
    batch = RecommendationBatch(
        recommendations=[],
        total_count=0,
        generated_at=datetime.now(timezone.utc),
        guest_group_id=uuid.uuid4(),
        request_context={"include_weather": True},
        personalization_factors={
            "season": "spring",
            "weather_context": None,
            "algorithm_weights": {"vector_similarity": 0.15, "host_insights": 0.3},
        },
    )
    assert batch.personalization_factors["season"] == "spring"
    assert batch.personalization_factors["algorithm_weights"]["host_insights"] == 0.3
