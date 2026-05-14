"""
Subscription service for managing pricing tiers, billing, and usage limits.

Handles subscription management including:
- Plan management
- Subscription creation and updates
- Payment processing (Stripe integration)
- Usage limit tracking
- Trial period management
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.subscription import (
    SubscriptionPlan, HostSubscription, SubscriptionPayment, UsageLimit,
    SubscriptionTier, SubscriptionStatus, PaymentStatus
)
from app.models.host import Host

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for managing host subscriptions.
    
    Handles subscription plans, billing, usage limits,
    and payment processing with Stripe integration.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the subscription service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_available_plans(self) -> List[SubscriptionPlan]:
        """
        Get all available subscription plans.
        
        Returns:
            List of available subscription plans
        """
        try:
            stmt = select(SubscriptionPlan).where(
                and_(
                    SubscriptionPlan.is_active == True,
                    SubscriptionPlan.is_visible == True
                )
            ).order_by(SubscriptionPlan.price_monthly)
            
            result = await self.db.execute(stmt)
            plans = result.scalars().all()
            
            return plans
            
        except Exception as e:
            logger.error(f"Error getting available plans: {e}")
            return []
    
    async def get_host_subscription(
        self,
        host_id: uuid.UUID
    ) -> Optional[HostSubscription]:
        """
        Get host's current subscription.
        
        Args:
            host_id: Host ID
            
        Returns:
            Host subscription or None
        """
        try:
            stmt = select(HostSubscription).where(
                HostSubscription.host_id == host_id
            )
            
            result = await self.db.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error getting host subscription: {e}")
            return None
    
    async def create_subscription(
        self,
        host_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_interval: str = "monthly",
        start_trial: bool = True
    ) -> Optional[HostSubscription]:
        """
        Create a new subscription for a host.
        
        Args:
            host_id: Host ID
            plan_id: Subscription plan ID
            billing_interval: Billing interval (monthly, yearly)
            start_trial: Whether to start trial period
            
        Returns:
            Created subscription or None
        """
        try:
            # Get plan
            stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
            result = await self.db.execute(stmt)
            plan = result.scalar_one_or_none()
            
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return None
            
            # Check if host already has subscription
            existing = await self.get_host_subscription(host_id)
            if existing:
                logger.warning(f"Host {host_id} already has subscription")
                return existing
            
            # Calculate billing period
            now = datetime.utcnow()
            if billing_interval == "yearly":
                period_end = now + timedelta(days=365)
            else:
                period_end = now + timedelta(days=30)
            
            # Handle trial period
            trial_start = None
            trial_end = None
            is_trial = False
            status = SubscriptionStatus.ACTIVE
            
            if start_trial and plan.trial_days > 0:
                trial_start = now
                trial_end = now + timedelta(days=plan.trial_days)
                is_trial = True
                status = SubscriptionStatus.TRIAL
                period_end = trial_end  # Extend period to trial end
            
            # Create subscription
            subscription = HostSubscription(
                id=uuid.uuid4(),
                host_id=host_id,
                plan_id=plan_id,
                tier=plan.tier,
                status=status,
                billing_interval=billing_interval,
                current_period_start=now,
                current_period_end=period_end,
                trial_start=trial_start,
                trial_end=trial_end,
                is_trial=is_trial,
                usage_stats={}
            )
            
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            
            # Initialize usage limits
            await self._initialize_usage_limits(subscription, plan)
            
            logger.info(f"Created subscription {subscription.id} for host {host_id}")
            return subscription
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            await self.db.rollback()
            return None
    
    async def update_subscription(
        self,
        subscription_id: uuid.UUID,
        plan_id: Optional[uuid.UUID] = None,
        status: Optional[SubscriptionStatus] = None
    ) -> Optional[HostSubscription]:
        """
        Update a subscription.
        
        Args:
            subscription_id: Subscription ID
            plan_id: Optional new plan ID
            status: Optional new status
            
        Returns:
            Updated subscription or None
        """
        try:
            stmt = select(HostSubscription).where(HostSubscription.id == subscription_id)
            result = await self.db.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.error(f"Subscription {subscription_id} not found")
                return None
            
            # Update plan if provided
            if plan_id:
                stmt_plan = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
                result_plan = await self.db.execute(stmt_plan)
                plan = result_plan.scalar_one_or_none()
                
                if plan:
                    subscription.plan_id = plan_id
                    subscription.tier = plan.tier
                    # Update usage limits
                    await self._update_usage_limits(subscription, plan)
            
            # Update status if provided
            if status:
                subscription.status = status
            
            subscription.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(subscription)
            
            logger.info(f"Updated subscription {subscription_id}")
            return subscription
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            await self.db.rollback()
            return None
    
    async def cancel_subscription(
        self,
        subscription_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a subscription (at period end).
        
        Args:
            subscription_id: Subscription ID
            reason: Optional cancellation reason
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            stmt = select(HostSubscription).where(HostSubscription.id == subscription_id)
            result = await self.db.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.error(f"Subscription {subscription_id} not found")
                return False
            
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = datetime.utcnow()
            subscription.cancellation_reason = reason
            subscription.status = SubscriptionStatus.CANCELLED
            
            await self.db.commit()
            
            logger.info(f"Cancelled subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            await self.db.rollback()
            return False
    
    async def check_usage_limit(
        self,
        host_id: uuid.UUID,
        limit_type: str,
        increment: int = 1
    ) -> Dict[str, Any]:
        """
        Check and update usage limit.
        
        Args:
            host_id: Host ID
            limit_type: Type of limit (guest_groups, attractions, ai_requests, etc.)
            increment: Amount to increment usage
            
        Returns:
            Limit check result with remaining usage
        """
        try:
            # Get subscription
            subscription = await self.get_host_subscription(host_id)
            if not subscription:
                return {
                    "allowed": False,
                    "reason": "No subscription found"
                }
            
            # Get usage limit
            stmt = select(UsageLimit).where(
                and_(
                    UsageLimit.host_id == host_id,
                    UsageLimit.limit_type == limit_type,
                    UsageLimit.period_end >= datetime.utcnow()
                )
            )
            
            result = await self.db.execute(stmt)
            usage_limit = result.scalar_one_or_none()
            
            if not usage_limit:
                # No limit set for this type - allow
                return {
                    "allowed": True,
                    "remaining": None,
                    "limit": None
                }
            
            # Check if limit exceeded
            new_usage = usage_limit.current_usage + increment
            allowed = new_usage <= usage_limit.limit_value
            
            if allowed:
                # Update usage
                usage_limit.current_usage = new_usage
                usage_limit.updated_at = datetime.utcnow()
                await self.db.commit()
            
            return {
                "allowed": allowed,
                "current_usage": usage_limit.current_usage,
                "limit": usage_limit.limit_value,
                "remaining": max(0, usage_limit.limit_value - usage_limit.current_usage)
            }
            
        except Exception as e:
            logger.error(f"Error checking usage limit: {e}")
            return {
                "allowed": False,
                "reason": str(e)
            }
    
    async def record_payment(
        self,
        subscription_id: uuid.UUID,
        host_id: uuid.UUID,
        amount: float,
        currency: str = "EUR",
        stripe_payment_intent_id: Optional[str] = None,
        status: PaymentStatus = PaymentStatus.SUCCEEDED
    ) -> Optional[SubscriptionPayment]:
        """
        Record a payment transaction.
        
        Args:
            subscription_id: Subscription ID
            host_id: Host ID
            amount: Payment amount
            currency: Currency code
            stripe_payment_intent_id: Optional Stripe payment intent ID
            status: Payment status
            
        Returns:
            Created payment record or None
        """
        try:
            payment = SubscriptionPayment(
                id=uuid.uuid4(),
                subscription_id=subscription_id,
                host_id=host_id,
                amount=amount,
                currency=currency,
                status=status,
                stripe_payment_intent_id=stripe_payment_intent_id,
                payment_date=datetime.utcnow() if status == PaymentStatus.SUCCEEDED else None
            )
            
            self.db.add(payment)
            await self.db.commit()
            await self.db.refresh(payment)
            
            logger.info(f"Recorded payment {payment.id} for subscription {subscription_id}")
            return payment
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            await self.db.rollback()
            return None
    
    async def _initialize_usage_limits(
        self,
        subscription: HostSubscription,
        plan: SubscriptionPlan
    ) -> None:
        """
        Initialize usage limits for a subscription.
        
        Args:
            subscription: Subscription instance
            plan: Subscription plan
        """
        try:
            limits = plan.limits or {}
            now = datetime.utcnow()
            
            # Calculate period end based on billing interval
            if subscription.billing_interval == "yearly":
                period_end = now + timedelta(days=365)
            else:
                period_end = now + timedelta(days=30)
            
            for limit_type, limit_value in limits.items():
                usage_limit = UsageLimit(
                    id=uuid.uuid4(),
                    host_id=subscription.host_id,
                    subscription_id=subscription.id,
                    limit_type=limit_type,
                    current_usage=0,
                    limit_value=limit_value,
                    reset_period=subscription.billing_interval,
                    period_start=now,
                    period_end=period_end,
                    last_reset=now
                )
                
                self.db.add(usage_limit)
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error initializing usage limits: {e}")
            await self.db.rollback()
    
    async def _update_usage_limits(
        self,
        subscription: HostSubscription,
        plan: SubscriptionPlan
    ) -> None:
        """
        Update usage limits when plan changes.
        
        Args:
            subscription: Subscription instance
            plan: New subscription plan
        """
        try:
            # Delete old limits
            stmt = select(UsageLimit).where(
                UsageLimit.subscription_id == subscription.id
            )
            result = await self.db.execute(stmt)
            old_limits = result.scalars().all()
            
            for old_limit in old_limits:
                await self.db.delete(old_limit)
            
            # Initialize new limits
            await self._initialize_usage_limits(subscription, plan)
            
        except Exception as e:
            logger.error(f"Error updating usage limits: {e}")
            await self.db.rollback()

