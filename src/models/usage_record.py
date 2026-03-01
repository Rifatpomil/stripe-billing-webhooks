"""Metered billing usage records (P2)."""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class UsageRecord(Base):
    """Sample usage records for metered billing aggregation."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    stripe_subscription_item_id: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    meter_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
