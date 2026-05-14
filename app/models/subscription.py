"""
Subscription model for pricing tiers and billing.

Defines subscription plans, usage limits, trial periods,
and billing management for the platform.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.postgresql.connection import Base


class SubscriptionTier(str, Enum):
    """Subscription pricing tiers."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Status of a subscription."""
    TRIAL = "trial"              # In trial period
    ACTIVE = "active"            # Active subscription
    PAST_DUE = "past_due"        # Payment failed, grace period
    CANCELLED = "cancelled"      # Cancelled but still active until period end
    EXPIRED = "expired"         # Subscription expired
    SUSPENDED = "suspended"     # Suspended due to non-payment


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class SubscriptionPlan(Base):
    """
    Subscription plan definition.
    
    Defines pricing tiers with features, limits, and pricing.
    """
    
    __tablename__ = "subscription_plans"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Plan Information
    name = Column(String(100), nullable=False, unique=True, index=True)
    tier = Column(String(20), nullable=False, index=True)  # free, basic, premium, enterprise
    description = Column(Text, nullable=True)
    
    # Pricing
    price_monthly = Column(Float, nullable=False, default=0.0)  # Monthly price in EUR
    price_yearly = Column(Float, nullable=True)  # Yearly price in EUR (discounted)
    currency = Column(String(10), default="EUR")
    
    # Features and Limits
    features = Column(JSON, default={})  # Feature flags
    limits = Column(JSON, default={})  # Usage limits
    # Example limits: {"guest_groups": 10, "attractions": 50, "ai_requests": 100}
    
    # Trial Period
    trial_days = Column(Integer, default=0)  # Trial period in days
    
    # Billing
    billing_interval = Column(String(20), default="monthly")  # monthly, yearly
    stripe_price_id_monthly = Column(String(200), nullable=True)
    stripe_price_id_yearly = Column(String(200), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)  # Show in public pricing
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HostSubscription(Base):
    """
    Host subscription record.
    
    Tracks individual host subscriptions, billing cycles,
    and usage limits.
    """
    
    __tablename__ = "host_subscriptions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, unique=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)
    
    # Subscription Details
    tier = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default=SubscriptionStatus.TRIAL, index=True)
    
    # Billing Cycle
    billing_interval = Column(String(20), default="monthly")  # monthly, yearly
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    # Trial Period
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    is_trial = Column(Boolean, default=False)
    
    # Payment Information
    stripe_subscription_id = Column(String(200), nullable=True, unique=True, index=True)
    stripe_customer_id = Column(String(200), nullable=True, index=True)
    payment_method_id = Column(String(200), nullable=True)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Usage Tracking
    usage_stats = Column(JSON, default={})  # Current usage against limits
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SubscriptionPayment(Base):
    """
    Payment record for subscriptions.
    
    Tracks individual payment transactions and billing history.
    """
    
    __tablename__ = "subscription_payments"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("host_subscriptions.id"), nullable=False, index=True)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    
    # Payment Details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    status = Column(String(20), default=PaymentStatus.PENDING, index=True)
    
    # Stripe Integration
    stripe_payment_intent_id = Column(String(200), nullable=True, unique=True, index=True)
    stripe_invoice_id = Column(String(200), nullable=True, index=True)
    
    # Billing Period
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    
    # Payment Information
    payment_method = Column(String(50), nullable=True)  # card, bank_transfer, etc.
    payment_date = Column(DateTime, nullable=True)
    
    # Failure Information
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageLimit(Base):
    """
    Usage limit tracking for subscriptions.
    
    Tracks current usage against subscription limits.
    """
    
    __tablename__ = "usage_limits"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("host_subscriptions.id"), nullable=False, index=True)
    
    # Limit Type
    limit_type = Column(String(50), nullable=False, index=True)  # guest_groups, attractions, ai_requests, etc.
    
    # Usage Tracking
    current_usage = Column(Integer, default=0)
    limit_value = Column(Integer, nullable=False)
    reset_period = Column(String(20), default="monthly")  # monthly, yearly, never
    
    # Period Tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    last_reset = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

