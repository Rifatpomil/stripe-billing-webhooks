"""Usage aggregation job (P2): aggregate usage records for metered billing."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_factory
from src.models import UsageRecord


async def aggregate_usage_by_customer(
    customer_id: str,
    meter_name: str,
    since: datetime | None = None,
    until: datetime | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """
    Aggregate usage for a customer and meter. Returns total quantity and record count.
    If db is provided, use it; otherwise create from factory.
    """
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    if until is None:
        until = datetime.now(timezone.utc)

    async def _run(session: AsyncSession):
        result = await session.execute(
            select(
                func.sum(UsageRecord.quantity).label("total_quantity"),
                func.count(UsageRecord.id).label("record_count"),
            )
            .where(UsageRecord.stripe_customer_id == customer_id)
            .where(UsageRecord.meter_name == meter_name)
            .where(UsageRecord.timestamp >= since)
            .where(UsageRecord.timestamp <= until)
        )
        row = result.one()
        return {
            "customer_id": customer_id,
            "meter_name": meter_name,
            "total_quantity": row.total_quantity or 0,
            "record_count": row.record_count or 0,
            "since": since.isoformat(),
            "until": until.isoformat(),
        }

    if db is not None:
        return await _run(db)
    async with async_session_factory() as session:
        return await _run(session)


async def run_usage_aggregation_job(
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict]:
    """
    Run aggregation for all (customer, meter) combinations in the period.
    Returns list of aggregation results.
    """
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=1)
    if until is None:
        until = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        result = await db.execute(
            select(
                UsageRecord.stripe_customer_id,
                UsageRecord.meter_name,
                func.sum(UsageRecord.quantity).label("total_quantity"),
                func.count(UsageRecord.id).label("record_count"),
            )
            .where(UsageRecord.timestamp >= since)
            .where(UsageRecord.timestamp <= until)
            .group_by(UsageRecord.stripe_customer_id, UsageRecord.meter_name)
        )
        rows = result.all()
        return [
            {
                "customer_id": r.stripe_customer_id,
                "meter_name": r.meter_name,
                "total_quantity": r.total_quantity or 0,
                "record_count": r.record_count or 0,
                "since": since.isoformat(),
                "until": until.isoformat(),
            }
            for r in rows
        ]
