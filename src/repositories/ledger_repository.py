"""Ledger entry repository."""

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
