"""Business intelligence API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BiRevenueTrackingResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    host_id: str
    period_days: int = 0
    group_by: str = "day"
    total_revenue: float = 0
    total_commission: float = 0
    total_bookings: int = 0
    average_booking_value: float = 0
    growth_rate: float = 0
    revenue_by_period: Dict[str, Any] = Field(default_factory=dict)
    forecast: Dict[str, Any] = Field(default_factory=dict)


class BiGuestLtvResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    host_id: str
    period_days: Optional[int] = None
    total_guests: int = 0
    total_revenue: float = 0
    average_ltv: float = 0


class BiRecommendationRoiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    host_id: str
    period_days: int = 0
    total_recommendations: int = 0
    total_accepted: int = 0
    acceptance_rate: float = 0
    average_satisfaction: float = 0
    estimated_revenue: float = 0
    roi_percentage: float = 0


class BiSeasonalTrendsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    host_id: str
    years: int = 0
    seasonal_revenue: Dict[str, float] = Field(default_factory=dict)
    seasonal_bookings: Dict[str, int] = Field(default_factory=dict)
    peak_season: Optional[str] = None


class BiDashboardSummary(BaseModel):
    total_revenue: float = 0
    average_ltv: float = 0
    roi_percentage: float = 0
    peak_season: Optional[str] = None


class BiDashboardResponse(BaseModel):
    host_id: str
    period_days: int
    revenue: BiRevenueTrackingResponse
    ltv: BiGuestLtvResponse
    roi: BiRecommendationRoiResponse
    seasonal_trends: BiSeasonalTrendsResponse
    summary: BiDashboardSummary


class BiExportJsonResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    revenue: BiRevenueTrackingResponse
    ltv: BiGuestLtvResponse
    roi: BiRecommendationRoiResponse
    trends: BiSeasonalTrendsResponse
