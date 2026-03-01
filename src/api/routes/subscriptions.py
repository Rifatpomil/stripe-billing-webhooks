"""Subscription API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.repositories.subscription_repository import SubscriptionRepository

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""

    stripe_subscription_id: str
    stripe_customer_id: str
    status: str
    previous_status: str | None
    current_period_start: str | None
    current_period_end: str | None
    cancel_at_period_end: bool


@router.get("/{customer_id}", response_model=list[SubscriptionResponse])
async def get_subscriptions_by_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionResponse]:
    """Get all subscriptions for a customer."""
    repo = SubscriptionRepository(db)
    subs = await repo.get_by_customer_id(customer_id)
    return [
        SubscriptionResponse(
            stripe_subscription_id=s.stripe_subscription_id,
            stripe_customer_id=s.stripe_customer_id,
            status=s.status,
            previous_status=s.previous_status,
            current_period_start=s.current_period_start.isoformat() if s.current_period_start else None,
            current_period_end=s.current_period_end.isoformat() if s.current_period_end else None,
            cancel_at_period_end=s.cancel_at_period_end,
        )
        for s in subs
    ]
