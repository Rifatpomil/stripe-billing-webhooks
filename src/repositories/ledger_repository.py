"""Ledger entry repository."""

from datetime import datetime, timedelta, timezone, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import LedgerEntry


class LedgerRepository:
    """Repository for append-only ledger entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_entry(
        self,
        stripe_customer_id: str,
        event_type: str,
        stripe_event_id: str,
        subscription_id: int | None = None,
        amount_cents: int | None = None,
        currency: str | None = None,
        description: str | None = None,
        metadata_json: str | None = None,
    ) -> LedgerEntry:
        """Append ledger entry."""

        entry = LedgerEntry(
            subscription_id=subscription_id,
            stripe_customer_id=stripe_customer_id,
            event_type=event_type,
            stripe_event_id=stripe_event_id,
            amount_cents=amount_cents,
            currency=currency,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_amounts_by_customer(
        self, customer_id: str, limit: int = 1000
    ) -> list[int]:
        """Get historical amount_cents for a customer (for anomaly detection)."""
        result = await self.db.execute(
            select(LedgerEntry.amount_cents)
            .where(LedgerEntry.stripe_customer_id == customer_id)
            .where(LedgerEntry.amount_cents.isnot(None))
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
        )
        return [r[0] for r in result.all() if r[0] is not None]

    async def get_entries_recent(
        self, limit: int = 100
    ) -> list[dict]:
        """Get recent ledger entries for semantic search (event_type, description, amount)."""
        result = await self.db.execute(
            select(
                LedgerEntry.event_type,
                LedgerEntry.description,
                LedgerEntry.stripe_customer_id,
                LedgerEntry.amount_cents,
                LedgerEntry.created_at,
            )
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "event_type": r[0],
                "description": r[1],
                "stripe_customer_id": r[2],
                "amount_cents": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]

    async def get_historical_amounts_for_forecast(
        self, customer_id: str, limit: int = 90
    ) -> list[tuple[datetime, int]]:
        """Get (created_at, amount_cents) for a customer for revenue forecasting."""
        since = datetime.now(timezone.utc) - timedelta(days=limit)
        result = await self.db.execute(
            select(LedgerEntry.created_at, LedgerEntry.amount_cents)
            .where(LedgerEntry.stripe_customer_id == customer_id)
            .where(LedgerEntry.amount_cents.isnot(None))
            .where(LedgerEntry.created_at >= since)
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
        )
        rows = [(r[0], r[1]) for r in result.all() if r[1]]
        return list(reversed(rows))

    async def get_aggregated_summary(
        self, limit: int = 100
    ) -> dict[str, int]:
        """Get total amount_cents per customer for NL query context."""
        result = await self.db.execute(
            select(
                LedgerEntry.stripe_customer_id,
                func.coalesce(func.sum(LedgerEntry.amount_cents), 0).label("total"),
            )
            .where(LedgerEntry.amount_cents.isnot(None))
            .group_by(LedgerEntry.stripe_customer_id)
            .limit(limit)
        )
        return {r[0]: int(r[1]) for r in result.all()}
