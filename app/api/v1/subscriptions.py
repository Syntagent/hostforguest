"""
Subscription API endpoints for pricing tiers and billing.

Provides REST API for subscription management including
plan selection, payment processing, and usage limits.
"""

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.subscription_service import SubscriptionService
from app.api.v1.hosts import get_current_host
from app.models.host import Host
from app.models.subscription import SubscriptionTier, SubscriptionStatus

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


@router.get("/plans")
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
        
        return {
            "plans": [
                {
                    "id": str(plan.id),
                    "name": plan.name,
                    "tier": plan.tier,
                    "description": plan.description,
                    "price_monthly": plan.price_monthly,
                    "price_yearly": plan.price_yearly,
                    "currency": plan.currency,
                    "trial_days": plan.trial_days,
                    "features": plan.features,
                    "limits": plan.limits
                }
                for plan in plans
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plans: {str(e)}"
        )


@router.get("/current")
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
            return {
                "has_subscription": False,
                "subscription": None
            }
        
        return {
            "has_subscription": True,
            "subscription": {
                "id": str(subscription.id),
                "tier": subscription.tier,
                "status": subscription.status,
                "billing_interval": subscription.billing_interval,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "is_trial": subscription.is_trial,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription: {str(e)}"
        )


@router.post("/create")
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
        
        return {
            "success": True,
            "subscription": {
                "id": str(subscription.id),
                "tier": subscription.tier,
                "status": subscription.status,
                "is_trial": subscription.is_trial,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.put("/update")
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
        
        return {
            "success": True,
            "subscription": {
                "id": str(updated_subscription.id),
                "tier": updated_subscription.tier,
                "status": updated_subscription.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )


@router.post("/cancel")
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
            return {"success": True, "message": "Subscription cancelled"}
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


@router.post("/check-usage")
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
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check usage: {str(e)}"
        )

