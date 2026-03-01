"""Retry worker: process failed webhooks from retry queue."""

import asyncio
import json
from datetime import datetime, timezone
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import async_session_factory
from src.models import WebhookRetry, WebhookDLQ
from src.services.webhook_processor import WebhookProcessor, WebhookProcessorError


async def process_retry_queue_once() -> dict:
    """Process one batch of retry queue. Returns stats."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    processed = 0
    failed_to_dlq = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(WebhookRetry)
            .where(WebhookRetry.next_retry_at <= now)
            .order_by(WebhookRetry.next_retry_at)
            .limit(100)
        )
        items = list(result.scalars().all())

        for retry in items:
            try:
                processor = WebhookProcessor(db)
                event_dict = json.loads(retry.raw_payload)
                await processor.process_event(event_dict)
                await db.delete(retry)
                processed += 1
            except WebhookProcessorError:
                # Illegal transition - move to DLQ
                dlq = WebhookDLQ(
                    event_id=retry.event_id,
                    raw_payload=retry.raw_payload,
                    event_type=retry.event_type,
                    final_error="Invalid state transition",
                    failed_attempts=retry.attempt,
                )
                db.add(dlq)
                await db.delete(retry)
                failed_to_dlq += 1
            except Exception as e:
                retry.attempt += 1
                retry.last_error = str(e)
                retry.next_retry_at = now + timedelta(
                    seconds=settings.webhook_retry_delay_seconds
                )
                if retry.attempt >= retry.max_attempts:
                    dlq = WebhookDLQ(
                        event_id=retry.event_id,
                        raw_payload=retry.raw_payload,
                        event_type=retry.event_type,
                        final_error=str(e),
                        failed_attempts=retry.attempt,
                    )
                    db.add(dlq)
                    await db.delete(retry)
                    failed_to_dlq += 1

        await db.commit()

    return {"processed": processed, "moved_to_dlq": failed_to_dlq}


async def run_retry_worker(interval_seconds: int = 60) -> None:
    """Run retry worker loop."""
    while True:
        await process_retry_queue_once()
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_retry_worker())
