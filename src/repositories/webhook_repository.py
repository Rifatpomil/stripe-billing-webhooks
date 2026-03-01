"""Webhook event repository."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WebhookEvent, WebhookRetry, WebhookDLQ


class WebhookRepository:
    """Repository for webhook events and retry/DLQ."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_event_id(self, event_id: str) -> WebhookEvent | None:
        """Get webhook event by Stripe event ID."""
        result = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def create_event(
        self,
        event_id: str,
        event_type: str,
        raw_payload: str,
        processing_status: str = "pending",
    ) -> WebhookEvent:
        """Create new webhook event (append-only)."""
        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            raw_payload=raw_payload,
            processing_status=processing_status,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def mark_processed(self, event: WebhookEvent) -> None:
        """Mark event as processed."""
        event.processed_at = datetime.utcnow()
        event.processing_status = "processed"
        await self.db.flush()

    async def mark_failed(self, event: WebhookEvent) -> None:
        """Mark event as failed."""
        event.processing_status = "failed"
        await self.db.flush()

    async def add_to_retry_queue(
        self,
        event_id: str,
        raw_payload: str,
        event_type: str,
        error: str,
        next_retry_at: datetime,
        attempt: int = 1,
        max_attempts: int = 5,
    ) -> WebhookRetry:
        """Add failed event to retry queue."""
        retry = WebhookRetry(
            event_id=event_id,
            raw_payload=raw_payload,
            event_type=event_type,
            attempt=attempt,
            max_attempts=max_attempts,
            last_error=error,
            next_retry_at=next_retry_at,
        )
        self.db.add(retry)
        await self.db.flush()
        return retry

    async def get_retry_by_event_id(self, event_id: str) -> WebhookRetry | None:
        """Get retry entry by event ID."""
        result = await self.db.execute(
            select(WebhookRetry).where(WebhookRetry.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def add_to_dlq(
        self,
        event_id: str,
        raw_payload: str,
        event_type: str,
        final_error: str,
        failed_attempts: int = 0,
    ) -> WebhookDLQ:
        """Add event to dead letter queue."""
        dlq = WebhookDLQ(
            event_id=event_id,
            raw_payload=raw_payload,
            event_type=event_type,
            final_error=final_error,
            failed_attempts=failed_attempts,
        )
        self.db.add(dlq)
        await self.db.flush()
        return dlq
