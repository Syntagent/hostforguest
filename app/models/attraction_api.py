"""Attraction AI API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class AttractionAiEnhanceContextUsed(BaseModel):
    model_config = ConfigDict(extra="allow")

    attraction_details: bool = False
    host_location: bool = False
    nearby_places: int = 0
    google_places_data: bool = False


class AttractionAiEnhanceData(BaseModel):
    model_config = ConfigDict(extra="allow")

    enhanced_description: str
    enhancement_method: str
    ai_provider: str
    context_used: AttractionAiEnhanceContextUsed = Field(
        default_factory=AttractionAiEnhanceContextUsed
    )


class AttractionAiEnhanceResponse(BaseModel):
    """POST /attractions/ai-enhance success envelope."""

    success: bool
    data: AttractionAiEnhanceData


class AttractionGenerateContentResponse(BaseModel):
    """POST /attractions/generate-content success envelope."""

    model_config = ConfigDict(extra="allow")

    success: bool
    content: Dict[str, Any]
    data_source: str
    sources_used: int
    personalization_level: str
