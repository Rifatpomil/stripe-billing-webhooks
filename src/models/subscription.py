"""Subscription model with state machine."""

from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


# Valid subscription states (Stripe-aligned)
SUBSCRIPTION_STATES = frozenset({
    "trialing",
    "active",
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
})

# Valid state transitions (from -> to)
# Terminal states: canceled, unpaid, incomplete_expired
VALID_TRANSITIONS = {
    ("incomplete", "active"),
    ("incomplete", "canceled"),
    ("incomplete", "incomplete_expired"),
    ("trialing", "active"),
    ("trialing", "canceled"),
    ("trialing", "past_due"),
    ("active", "past_due"),
    ("active", "canceled"),
    ("active", "trialing"),
    ("past_due", "active"),
    ("past_due", "canceled"),
    ("past_due", "unpaid"),
    ("unpaid", "canceled"),
    ("unpaid", "active"),
}


class Subscription(Base):
    """Customer subscription with state machine enforcement."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ledger_entries = relationship("LedgerEntry", back_populates="subscription", lazy="selectin")
