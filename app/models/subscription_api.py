"""Subscription API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlanRecord(BaseModel):
    id: str
    name: str
    tier: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: Optional[float] = None
    currency: str = "EUR"
    trial_days: int = 0
    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionPlansListResponse(BaseModel):
    plans: List[SubscriptionPlanRecord]


class HostSubscriptionSummary(BaseModel):
    id: str
    tier: str
    status: str
    billing_interval: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    is_trial: bool = False
    trial_end: Optional[str] = None
    cancel_at_period_end: bool = False


class SubscriptionCurrentResponse(BaseModel):
    has_subscription: bool
    subscription: Optional[HostSubscriptionSummary] = None


class SubscriptionCreatedSummary(BaseModel):
    id: str
    tier: str
    status: str
    is_trial: bool = False
    trial_end: Optional[str] = None


class SubscriptionCreateResponse(BaseModel):
    success: bool = True
    subscription: SubscriptionCreatedSummary


class SubscriptionUpdateResponse(BaseModel):
    success: bool = True
    subscription: SubscriptionCreatedSummary


class SubscriptionCancelResponse(BaseModel):
    success: bool = True
    message: str


class UsageLimitCheckResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    allowed: bool
    reason: Optional[str] = None
    remaining: Optional[int] = None
    limit: Optional[int] = None
    current_usage: Optional[int] = None


class StripeCheckoutResponse(BaseModel):
    success: bool = True
    checkout_url: str
    tier: str
    billing_interval: str


class StripeWebhookResponse(BaseModel):
    received: bool = True


class SubscriptionPaymentRecord(BaseModel):
    id: str
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    payment_date: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    created_at: Optional[str] = None


class SubscriptionPaymentsListResponse(BaseModel):
    payments: List[SubscriptionPaymentRecord] = Field(default_factory=list)
