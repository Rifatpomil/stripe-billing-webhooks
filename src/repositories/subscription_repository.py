"""Subscription model repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Subscription


class SubscriptionRepository:
    """Repository for subscription operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> Subscription | None:
        """Get subscription by Stripe subscription ID."""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: str) -> list[Subscription]:
        """Get all subscriptions for a customer."""
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.stripe_customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def upsert_subscription(
        self,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        status: str,
        previous_status: str | None = None,
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end: bool = False,
        metadata_json: str | None = None,
    ) -> Subscription:
        """Create or update subscription (state machine enforced by DB trigger)."""
        sub = await self.get_by_stripe_subscription_id(stripe_subscription_id)
        if sub:
            sub.status = status
            sub.previous_status = previous_status or sub.status
            sub.current_period_start = current_period_start or sub.current_period_start
            sub.current_period_end = current_period_end or sub.current_period_end
            sub.cancel_at_period_end = cancel_at_period_end
            sub.metadata_json = metadata_json or sub.metadata_json
            await self.db.flush()
            return sub
        sub = Subscription(
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=status,
            previous_status=previous_status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            metadata_json=metadata_json,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub
