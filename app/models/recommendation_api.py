"""Recommendation admin/test API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class RecommendationAlgorithmTestResponse(BaseModel):
    success: bool
    message: str
    guest_group_id: Optional[uuid.UUID] = None
    recommendations_count: int = 0
    duration_ms: int = 0
    parameters_used: Dict[str, Any] = Field(default_factory=dict)
    sample_titles: List[str] = Field(default_factory=list)


class RecommendationPerformanceMetricsResponse(BaseModel):
    total_recommendation_sets: int = 0
    total_recommendations_generated: int = 0
    average_satisfaction: float = 0.0
    recommendations_accepted_rate: float = 0.0
    host_insights_helpful_rate: float = 0.0
