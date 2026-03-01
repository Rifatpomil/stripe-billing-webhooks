"""Stripe webhook event processor."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.repositories.ledger_repository import LedgerRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.repositories.webhook_repository import WebhookRepository

# Billing-related events that write to ledger
BILLING_EVENT_TYPES = frozenset({
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "invoice.created",
    "invoice.finalized",
})


class WebhookProcessorError(Exception):
    """Raised when webhook processing fails (e.g. illegal state transition)."""

    pass


class WebhookProcessor:
    """Process Stripe webhook events: update subscriptions, write ledger."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sub_repo = SubscriptionRepository(db)
        self.ledger_repo = LedgerRepository(db)

    async def process_event(self, event: dict[str, Any]) -> None:
        """Process a verified Stripe event. Idempotent by event_id."""
        event_id = event.get("id") or ""
        event_type = event.get("type") or ""
        data = event.get("data", {})
        obj = data.get("object", {})

        try:
            # 1. Handle subscription events (DB trigger enforces valid transitions)
            if event_type.startswith("customer.subscription."):
                await self._process_subscription_event(event_type, obj)

            # 2. Write ledger for billing events
            if event_type in BILLING_EVENT_TYPES:
                await self._write_ledger_entry(event_id, event_type, obj)
        except IntegrityError as e:
            msg = str(e.orig) if hasattr(e, "orig") and e.orig else str(e)
            raise WebhookProcessorError(f"Invalid subscription state transition: {msg}") from e

    async def _process_subscription_event(
        self, event_type: str, obj: dict[str, Any]
    ) -> None:
        """Update subscription state. DB trigger enforces valid transitions."""
        sub_id = obj.get("id")
        if not sub_id:
            return
        customer_id = obj.get("customer", "")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id", "")
        status = obj.get("status", "")
        period_start = obj.get("current_period_start")
        period_end = obj.get("current_period_end")
        cancel_at_period_end = obj.get("cancel_at_period_end", False)

        if period_start:
            period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
        if period_end:
            period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

        existing = await self.sub_repo.get_by_stripe_subscription_id(sub_id)
        previous_status = existing.status if existing else None

        await self.sub_repo.upsert_subscription(
            stripe_subscription_id=sub_id,
            stripe_customer_id=customer_id,
            status=status,
            previous_status=previous_status,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=cancel_at_period_end,
            metadata_json=json.dumps(obj.get("metadata", {})) if obj.get("metadata") else None,
        )

    async def _write_ledger_entry(
        self, event_id: str, event_type: str, obj: dict[str, Any]
    ) -> None:
        """Append ledger entry for billing event."""
        customer_id = obj.get("customer", "")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id", "")
        if not customer_id and "subscription" in obj:
            sub_id = obj.get("subscription")
            sub = await self.sub_repo.get_by_stripe_subscription_id(sub_id) if sub_id else None
            customer_id = sub.stripe_customer_id if sub else ""

        amount_cents = None
        currency = None
        if "amount_paid" in obj:
            amount_cents = obj.get("amount_paid")
        elif "amount_due" in obj:
            amount_cents = obj.get("amount_due")
        if "currency" in obj:
            currency = obj.get("currency")

        subscription_id = None
        sub_id = obj.get("subscription")
        if sub_id:
            sub = await self.sub_repo.get_by_stripe_subscription_id(sub_id)
            subscription_id = sub.id if sub else None

        await self.ledger_repo.create_entry(
            stripe_customer_id=customer_id or "unknown",
            event_type=event_type,
            stripe_event_id=event_id,
            subscription_id=subscription_id,
            amount_cents=amount_cents,
            currency=currency,
            description=obj.get("description"),
            metadata_json=json.dumps(obj.get("metadata", {})) if obj.get("metadata") else None,
        )
