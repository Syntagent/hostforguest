"""Analytics API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SatisfactionDailyRating(BaseModel):
    date: str
    average_rating: float = 0
    guest_count: int = 0


class SatisfactionTrendsResponse(BaseModel):
    daily_ratings: List[SatisfactionDailyRating] = Field(default_factory=list)
    overall_average: float = 0
    total_guests: int = 0


class RecommendationEffectivenessResponse(BaseModel):
    total_recommendation_sets: int = 0
    total_recommendations: int = 0
    total_accepted: int = 0
    acceptance_rate: float = 0
    average_satisfaction: float = 0
    period_days: int = 30


class PartnerPerformanceRow(BaseModel):
    partner_id: str
    partner_name: str
    partner_type: str
    bookings_count: int = 0
    revenue_generated: float = 0
    commission_earned: float = 0
    average_rating: Optional[float] = None
    status: Optional[str] = None


class AnalyticsRevenueDailyRow(BaseModel):
    date: str
    revenue: float = 0


class AnalyticsRevenueTrackingResponse(BaseModel):
    total_commission_revenue: float = 0
    period_days: int = 30
    daily_revenue: List[AnalyticsRevenueDailyRow] = Field(default_factory=list)
    average_daily_revenue: float = 0


class AnalyticsExportResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    format: str
    data: Dict[str, Any] = Field(default_factory=dict)
