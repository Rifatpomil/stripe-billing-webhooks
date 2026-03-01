"""Dead letter queue for permanently failed webhooks (P1)."""

from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class WebhookDLQ(Base):
    """Dead letter queue for webhooks that exceeded max retries."""

    __tablename__ = "webhook_dlq"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    final_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
