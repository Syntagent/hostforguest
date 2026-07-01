"""
Stripe integration service for HostForGuest subscription billing.

Wraps the Stripe API to handle checkout sessions, webhook events,
customer creation, and subscription lifecycle management.
"""

import stripe
import os
import logging
import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.subscription import (
    HostSubscription, SubscriptionPlan, SubscriptionPayment,
    SubscriptionTier, SubscriptionStatus, PaymentStatus
)
from app.models.host import Host
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeServiceError(Exception):
    """Raised when a Stripe operation fails."""
    pass


class StripeService:
    """
    Service for processing Stripe payments and subscriptions.

    Handles:
    - Creating Stripe Checkout Sessions
    - Processing Stripe webhook events
    - Managing Stripe Customers
    - Recording payments in the local database
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        stripe.api_key = settings.stripe_secret_key

    async def create_or_get_customer(self, host: Host) -> str:
        """
        Get an existing Stripe customer ID for the host, or create one.

        Args:
            host: The host entity

        Returns:
            Stripe customer ID (cus_xxx)
        """
        # Check if host already has a Stripe customer ID
        stmt = select(HostSubscription).where(
            HostSubscription.host_id == host.id,
            HostSubscription.stripe_customer_id.isnot(None)
        ).order_by(HostSubscription.created_at.desc()).limit(1)

        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.stripe_customer_id:
            return existing.stripe_customer_id

        # Create a new Stripe customer
        try:
            name = host.full_name or host.email or "HostForGuest Host"
            customer = stripe.Customer.create(
                email=host.email,
                name=name,
                metadata={
                    "host_id": str(host.id),
                    "source": "hostforguest_pricing_page"
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for host {host.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for host {host.id}: {e}")
            raise StripeServiceError(f"Failed to create customer: {str(e)}")

    async def create_checkout_session(
        self,
        host: Host,
        tier: str,
        billing_interval: str = "monthly",
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """
        Create a Stripe Checkout Session for subscription purchase.

        Args:
            host: The host making the purchase
            tier: Subscription tier (basic, premium, enterprise)
            billing_interval: monthly or yearly
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancellation

        Returns:
            Checkout session URL for redirect

        Raises:
            StripeServiceError: If checkout session creation fails
        """
        # Try env var first, then fall back to DB stripe_price_id
        tier_upper = tier.upper()
        interval_upper = billing_interval.upper()
        env_var = f"STRIPE_PRICE_{tier_upper}_{interval_upper}"
        price_id = os.getenv(env_var, "")

        if not price_id:
            try:
                SubscriptionTier(tier)
            except ValueError:
                raise StripeServiceError(f"Invalid tier: {tier}")

            stmt = select(SubscriptionPlan).where(
                SubscriptionPlan.tier == tier,
                SubscriptionPlan.is_active == True
            ).limit(1)
            result = await self.db.execute(stmt)
            plan = result.scalar_one_or_none()

            if not plan:
                raise StripeServiceError(f"Plan not found for tier: {tier}")

            if billing_interval == "yearly" and plan.stripe_price_id_yearly:
                price_id = plan.stripe_price_id_yearly
            elif plan.stripe_price_id_monthly:
                price_id = plan.stripe_price_id_monthly
            else:
                raise StripeServiceError(
                    f"No Stripe price configured for {tier} ({billing_interval}). "
                    "Contact administrator to set up Stripe prices."
                )

        base_url = os.getenv("NEXT_PUBLIC_API_URL", "https://hostforguest.syntagent.com")
        success = success_url or f"{base_url}/dashboard?subscription=success"
        cancel = cancel_url or f"{base_url}/pricing?cancelled=true"

        try:
            customer_id = await self.create_or_get_customer(host)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                success_url=success,
                cancel_url=cancel,
                metadata={
                    "host_id": str(host.id),
                    "tier": tier,
                    "billing_interval": billing_interval,
                },
                subscription_data={
                    "metadata": {
                        "host_id": str(host.id),
                        "tier": tier,
                    },
                    "trial_period_days": 14 if tier in ("basic", "premium") else 0,
                },
                allow_promotion_codes=True,
            )

            logger.info(
                f"Created checkout session {session.id} for host {host.id} tier={tier}"
            )
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session error: {e}")
            raise StripeServiceError(f"Failed to create checkout: {str(e)}")

    async def handle_webhook(self, payload: bytes, sig_header: str) -> bool:
        """
        Process an incoming Stripe webhook event.

        Supported events:
        - checkout.session.completed
        - invoice.payment_succeeded
        - invoice.payment_failed
        - customer.subscription.deleted
        - customer.subscription.updated
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            raise StripeServiceError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise StripeServiceError("Invalid signature")

        logger.info(f"Stripe webhook received: {event.type} (id={event.id})")

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.payment_succeeded": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_failed,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "customer.subscription.updated": self._handle_subscription_updated,
        }

        handler = handlers.get(event.type)
        if handler:
            await handler(event.data.object)
            return True
        else:
            logger.info(f"Unhandled webhook event type: {event.type}")
            return True

    async def _handle_checkout_completed(self, session) -> None:
        """Handle checkout.session.completed — activates subscription."""
        host_id = session.get("metadata", {}).get("host_id", "")
        tier = session.get("metadata", {}).get("tier", "basic")
        billing_interval = session.get("metadata", {}).get("billing_interval", "monthly")

        if not host_id:
            logger.warning("Checkout completed without host_id in metadata")
            return

        stripe_subscription_id = session.get("subscription", "")
        customer_id = session.get("customer", "")

        try:
            host_uuid = uuid.UUID(host_id)
        except ValueError:
            logger.error(f"Invalid host_id in Stripe metadata: {host_id}")
            return

        stmt = select(HostSubscription).where(
            HostSubscription.host_id == host_uuid
        ).order_by(HostSubscription.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.stripe_customer_id = customer_id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.is_trial = False

            now = datetime.utcnow()
            if billing_interval == "yearly":
                subscription.current_period_end = now.replace(year=now.year + 1)
            else:
                subscription.current_period_end = now.replace(month=now.month + 1)

            await self.db.commit()
            logger.info(f"Activated subscription {subscription.id} via Stripe checkout")
        else:
            logger.warning(f"No pending subscription found for host {host_id}")

    async def _handle_invoice_paid(self, invoice) -> None:
        """Handle invoice.payment_succeeded — record payment."""
        subscription_id = invoice.get("subscription", "")
        if not subscription_id:
            return

        stmt = select(HostSubscription).where(
            HostSubscription.stripe_subscription_id == subscription_id
        ).limit(1)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"No local subscription for Stripe sub {subscription_id}")
            return

        amount = invoice.get("total", 0) / 100.0
        currency = invoice.get("currency", "eur").upper()
        payment_intent = invoice.get("payment_intent", "")
        stripe_invoice_id = invoice.get("id", "")

        payment = SubscriptionPayment(
            id=uuid.uuid4(),
            subscription_id=subscription.id,
            host_id=subscription.host_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.SUCCEEDED,
            stripe_payment_intent_id=payment_intent,
            stripe_invoice_id=stripe_invoice_id,
            payment_method="card",
            payment_date=datetime.utcnow(),
        )
        self.db.add(payment)

        period_end_timestamp = invoice.get("period_end", datetime.utcnow().timestamp())
        subscription.current_period_end = datetime.fromtimestamp(period_end_timestamp)
        subscription.status = SubscriptionStatus.ACTIVE

        await self.db.commit()
        logger.info(f"Recorded payment {payment.id} ({amount} {currency}) for sub {subscription.id}")

    async def _handle_invoice_failed(self, invoice) -> None:
        """Handle invoice.payment_failed — mark subscription past due."""
        subscription_id = invoice.get("subscription", "")
        if not subscription_id:
            return

        stmt = select(HostSubscription).where(
            HostSubscription.stripe_subscription_id == subscription_id
        ).limit(1)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        subscription.status = SubscriptionStatus.PAST_DUE

        amount = invoice.get("total", 0) / 100.0
        currency = invoice.get("currency", "eur").upper()
        stripe_invoice_id = invoice.get("id", "")

        payment = SubscriptionPayment(
            id=uuid.uuid4(),
            subscription_id=subscription.id,
            host_id=subscription.host_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.FAILED,
            stripe_invoice_id=stripe_invoice_id,
            failure_reason="Payment declined"
        )
        self.db.add(payment)
        await self.db.commit()
        logger.warning(f"Payment failed for subscription {subscription.id}")

    async def _handle_subscription_deleted(self, stripe_sub) -> None:
        """Handle customer.subscription.deleted — mark expired."""
        stripe_sub_id = stripe_sub.get("id", "")
        stmt = select(HostSubscription).where(
            HostSubscription.stripe_subscription_id == stripe_sub_id
        ).limit(1)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        subscription.status = SubscriptionStatus.EXPIRED
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Subscription {subscription.id} expired via Stripe")

    async def _handle_subscription_updated(self, stripe_sub) -> None:
        """Handle customer.subscription.updated — sync status."""
        stripe_sub_id = stripe_sub.get("id", "")
        stmt = select(HostSubscription).where(
            HostSubscription.stripe_subscription_id == stripe_sub_id
        ).limit(1)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        stripe_status = stripe_sub.get("status", "")
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELLED,
            "incomplete_expired": SubscriptionStatus.EXPIRED,
        }
        new_status = status_map.get(stripe_status)
        if new_status:
            subscription.status = new_status
        await self.db.commit()

    async def cancel_at_period_end(self, subscription: HostSubscription) -> bool:
        """Set Stripe subscription to cancel at period end."""
        if not subscription.stripe_subscription_id:
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = datetime.utcnow()
            subscription.status = SubscriptionStatus.CANCELLED
            await self.db.commit()
            return True

        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = datetime.utcnow()
            await self.db.commit()
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription: {e}")
            return False

    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve invoice details from Stripe."""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return {
                "id": invoice.id,
                "amount_due": invoice.amount_due / 100.0,
                "amount_paid": invoice.amount_paid / 100.0,
                "currency": invoice.currency.upper(),
                "status": invoice.status,
                "created": datetime.fromtimestamp(invoice.created).isoformat(),
                "pdf_url": invoice.invoice_pdf,
                "hosted_url": invoice.hosted_invoice_url,
                "period_start": datetime.fromtimestamp(invoice.period_start).isoformat(),
                "period_end": datetime.fromtimestamp(invoice.period_end).isoformat(),
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve invoice {invoice_id}: {e}")
            return None
