"""Usage records API (P2)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.jobs.usage_aggregation import aggregate_usage_by_customer
from src.models import UsageRecord

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageAggregationResponse(BaseModel):
    """Usage aggregation response."""

    customer_id: str
    meter_name: str
    total_quantity: int
    record_count: int
    since: str
    until: str


@router.get("/aggregate/{customer_id}", response_model=UsageAggregationResponse)
async def get_usage_aggregation(
    customer_id: str,
    meter_name: str = Query(..., description="Meter name to aggregate"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
) -> UsageAggregationResponse:
    """Get aggregated usage for a customer and meter."""
    until = datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    result = await aggregate_usage_by_customer(
        customer_id=customer_id,
        meter_name=meter_name,
        since=since,
        until=until,
        db=db,
    )
    return UsageAggregationResponse(**result)


class UsageRecordCreate(BaseModel):
    """Create usage record request."""

    stripe_customer_id: str
    stripe_subscription_item_id: str
    meter_name: str
    quantity: int = 1


@router.post("/records", status_code=201)
async def create_usage_record(
    body: UsageRecordCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a usage record (for metered billing sample data)."""
    record = UsageRecord(
        stripe_customer_id=body.stripe_customer_id,
        stripe_subscription_item_id=body.stripe_subscription_item_id,
        meter_name=body.meter_name,
        quantity=body.quantity,
    )
    db.add(record)
    await db.flush()
    return {"id": record.id, "meter_name": body.meter_name, "quantity": body.quantity}
