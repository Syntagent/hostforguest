"""Booking API response models (frontend TS parity)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BookingResponse(BaseModel):
    """Created booking response."""

    id: str
    guest_group_id: str
    partner_id: str
    booking_amount: float
    currency: str
    commission_rate: float
    commission_amount: float
    status: str
    booking_date: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingMutationResponse(BaseModel):
    success: bool
    message: str


class BookingSummaryRow(BaseModel):
    id: str
    guest_group_id: str
    partner_id: str
    booking_amount: float
    currency: str
    commission_amount: float
    status: str
    booking_date: Optional[str] = None


class HostBookingsListResponse(BaseModel):
    bookings: List[BookingSummaryRow]
    count: int


class PartnerPayoutCurrencyRow(BaseModel):
    currency: str
    total_commission: float
    total_bookings: int


class PartnerPayoutResponse(BaseModel):
    partner_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    payouts_by_currency: List[PartnerPayoutCurrencyRow] = Field(default_factory=list)
    total_all_currencies: Dict[str, float] = Field(default_factory=dict)


class BookingStatusMetrics(BaseModel):
    count: int = 0
    revenue: float = 0
    commission: float = 0


class BookingAnalyticsTotals(BaseModel):
    total_bookings: int = 0
    total_revenue: float = 0
    total_commission: float = 0


class BookingAnalyticsResponse(BaseModel):
    period_days: int
    start_date: str
    end_date: str
    by_status: Dict[str, BookingStatusMetrics] = Field(default_factory=dict)
    by_currency: Dict[str, BookingStatusMetrics] = Field(default_factory=dict)
    totals: BookingAnalyticsTotals
