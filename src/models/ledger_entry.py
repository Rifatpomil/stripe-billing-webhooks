"""Append-only billing ledger."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class LedgerEntry(Base):
    """Append-only ledger for billing events."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stripe_event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscription = relationship("Subscription", back_populates="ledger_entries")
