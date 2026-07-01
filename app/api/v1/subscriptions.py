"""
Subscription API endpoints for pricing tiers and billing.

Provides REST API for subscription management including
plan selection, payment processing, and usage limits.
"""

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.subscription_service import SubscriptionService
from app.api.v1.hosts import get_current_host
from app.models.host import Host
from app.models.subscription import SubscriptionTier, SubscriptionStatus, SubscriptionPayment
from app.models.subscription_api import (
    HostSubscriptionSummary,
    StripeCheckoutResponse,
    StripeWebhookResponse,
    SubscriptionCancelResponse,
    SubscriptionCreateResponse,
    SubscriptionCreatedSummary,
    SubscriptionCurrentResponse,
    SubscriptionPaymentRecord,
    SubscriptionPaymentsListResponse,
    SubscriptionPlanRecord,
    SubscriptionPlansListResponse,
    SubscriptionUpdateResponse,
    UsageLimitCheckResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class CreateSubscriptionRequest(BaseModel):
    """Request for creating a subscription."""
    plan_id: str
    billing_interval: str = "monthly"  # monthly, yearly
    start_trial: bool = True


class UpdateSubscriptionRequest(BaseModel):
    """Request for updating a subscription."""
    plan_id: Optional[str] = None
    status: Optional[str] = None


class CancelSubscriptionRequest(BaseModel):
    """Request for cancelling a subscription."""
    reason: Optional[str] = None


class CheckUsageRequest(BaseModel):
    """Request for checking usage limit."""
    limit_type: str
    increment: int = 1


class StripeCheckoutRequest(BaseModel):
    """Request for creating a Stripe Checkout session."""
    tier: str  # basic, premium, enterprise
    billing_interval: str = "monthly"  # monthly, yearly
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.get("/plans", response_model=SubscriptionPlansListResponse)
async def get_available_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available subscription plans.
    
    Args:
        db: Database session
        
    Returns:
        List of available plans
    """
    try:
        subscription_service = SubscriptionService(db)
        plans = await subscription_service.get_available_plans()
        
        return SubscriptionPlansListResponse(
            plans=[
                SubscriptionPlanRecord(
                    id=str(plan.id),
                    name=plan.name,
                    tier=plan.tier,
                    description=plan.description,
                    price_monthly=plan.price_monthly,
                    price_yearly=plan.price_yearly,
                    currency=plan.currency or "EUR",
                    trial_days=plan.trial_days or 0,
                    features=plan.features or {},
                    limits=plan.limits or {},
                )
                for plan in plans
            ]
        )
        
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plans: {str(e)}"
        )


@router.get("/current", response_model=SubscriptionCurrentResponse)
async def get_current_subscription(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current host subscription.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Current subscription details
    """
    try:
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_host_subscription(current_host.id)
        
        if not subscription:
            return SubscriptionCurrentResponse(has_subscription=False, subscription=None)

        return SubscriptionCurrentResponse(
            has_subscription=True,
            subscription=HostSubscriptionSummary(
                id=str(subscription.id),
                tier=subscription.tier,
                status=subscription.status,
                billing_interval=subscription.billing_interval,
                current_period_start=(
                    subscription.current_period_start.isoformat()
                    if subscription.current_period_start
                    else None
                ),
                current_period_end=(
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None
                ),
                is_trial=bool(subscription.is_trial),
                trial_end=(
                    subscription.trial_end.isoformat() if subscription.trial_end else None
                ),
                cancel_at_period_end=bool(subscription.cancel_at_period_end),
            ),
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription: {str(e)}"
        )


@router.post("/create", response_model=SubscriptionCreateResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription.
    
    Args:
        request: Subscription creation request
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Created subscription
    """
    try:
        subscription_service = SubscriptionService(db)
        
        subscription = await subscription_service.create_subscription(
            host_id=current_host.id,
            plan_id=uuid.UUID(request.plan_id),
            billing_interval=request.billing_interval,
            start_trial=request.start_trial
        )
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )
        
        return SubscriptionCreateResponse(
            success=True,
            subscription=SubscriptionCreatedSummary(
                id=str(subscription.id),
                tier=subscription.tier,
                status=subscription.status,
                is_trial=bool(subscription.is_trial),
                trial_end=(
                    subscription.trial_end.isoformat() if subscription.trial_end else None
                ),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.put("/update", response_model=SubscriptionUpdateResponse)
async def update_subscription(
    request: UpdateSubscriptionRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current subscription.
    
    Args:
        request: Update request
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Updated subscription
    """
    try:
        subscription_service = SubscriptionService(db)
        
        subscription = await subscription_service.get_host_subscription(current_host.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )
        
        updated_subscription = await subscription_service.update_subscription(
            subscription_id=subscription.id,
            plan_id=uuid.UUID(request.plan_id) if request.plan_id else None,
            status=SubscriptionStatus(request.status) if request.status else None
        )
        
        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription"
            )
        
        return SubscriptionUpdateResponse(
            success=True,
            subscription=SubscriptionCreatedSummary(
                id=str(updated_subscription.id),
                tier=updated_subscription.tier,
                status=updated_subscription.status,
                is_trial=bool(updated_subscription.is_trial),
                trial_end=(
                    updated_subscription.trial_end.isoformat()
                    if updated_subscription.trial_end
                    else None
                ),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel current subscription.
    
    Args:
        request: Cancellation request
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Success status
    """
    try:
        subscription_service = SubscriptionService(db)
        
        subscription = await subscription_service.get_host_subscription(current_host.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )
        
        success = await subscription_service.cancel_subscription(
            subscription_id=subscription.id,
            reason=request.reason
        )
        
        if success:
            return SubscriptionCancelResponse(
                success=True,
                message="Subscription cancelled",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel subscription"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/check-usage", response_model=UsageLimitCheckResponse)
async def check_usage_limit(
    request: CheckUsageRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Check and update usage limit.
    
    Args:
        request: Usage check request
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Usage limit check result
    """
    try:
        subscription_service = SubscriptionService(db)
        
        result = await subscription_service.check_usage_limit(
            host_id=current_host.id,
            limit_type=request.limit_type,
            increment=request.increment
        )
        
        return UsageLimitCheckResponse.model_validate(result)

    except Exception as e:
        logger.error(f"Error checking usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check usage: {str(e)}"
        )


@router.post("/stripe-checkout", response_model=StripeCheckoutResponse)
async def create_stripe_checkout(
    request: StripeCheckoutRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Checkout Session for subscription payment.

    Redirects the host to Stripe's hosted checkout page.
    Supports Basic, Premium, and Enterprise tiers with monthly/yearly billing.

    Args:
        request: Checkout request with tier and billing interval
        current_host: Current authenticated host
        db: Database session

    Returns:
        Checkout URL for Stripe redirect
    """
    try:
        from app.services.stripe_service import StripeService, StripeServiceError

        stripe_service = StripeService(db)
        checkout_url = await stripe_service.create_checkout_session(
            host=current_host,
            tier=request.tier,
            billing_interval=request.billing_interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )

        return StripeCheckoutResponse(
            success=True,
            checkout_url=checkout_url,
            tier=request.tier,
            billing_interval=request.billing_interval,
        )

    except StripeServiceError as e:
        logger.error(f"Stripe checkout error for host {current_host.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout: {str(e)}"
        )


@router.post("/webhook", response_model=StripeWebhookResponse, include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Stripe webhook endpoint for processing subscription events.

    Handles checkout.session.completed, invoice.payment_succeeded,
    invoice.payment_failed, customer.subscription.deleted, and
    customer.subscription.updated events.

    This endpoint is called by Stripe directly, NOT by the frontend.
    It is excluded from OpenAPI schema for security.
    """
    import stripe

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )

    try:
        from app.services.stripe_service import StripeService, StripeServiceError

        stripe_service = StripeService(db)
        await stripe_service.handle_webhook(payload, sig_header)

        return StripeWebhookResponse(received=True)

    except StripeServiceError as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.get("/invoices", response_model=SubscriptionPaymentsListResponse)
async def get_payment_history(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment history for the current host's subscription.

    Args:
        current_host: Current authenticated host
        db: Database session

    Returns:
        List of payments
    """
    try:
        from sqlalchemy import select, desc

        stmt = select(SubscriptionPayment).where(
            SubscriptionPayment.host_id == current_host.id
        ).order_by(desc(SubscriptionPayment.created_at)).limit(50)

        result = await db.execute(stmt)
        payments = result.scalars().all()

        return SubscriptionPaymentsListResponse(
            payments=[
                SubscriptionPaymentRecord(
                    id=str(p.id),
                    amount=p.amount,
                    currency=p.currency or "EUR",
                    status=p.status,
                    payment_method=p.payment_method,
                    payment_date=(
                        p.payment_date.isoformat() if p.payment_date else None
                    ),
                    stripe_invoice_id=p.stripe_invoice_id,
                    created_at=p.created_at.isoformat() if p.created_at else None,
                )
                for p in payments
            ]
        )

    except Exception as e:
        logger.error(f"Error fetching payment history: {e}")
        return SubscriptionPaymentsListResponse(payments=[])
