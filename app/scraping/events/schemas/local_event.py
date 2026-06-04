"""Pydantic schemas for parsed local events."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LocalEventDraft(BaseModel):
    """Normalized event extracted from a tourism source."""

    title: str = Field(min_length=2, max_length=500)
    description: str = ""
    url: Optional[str] = None
    language: str = "hr"
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    city: Optional[str] = None
    region: Optional[str] = None
    venue_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    external_id: Optional[str] = None
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
