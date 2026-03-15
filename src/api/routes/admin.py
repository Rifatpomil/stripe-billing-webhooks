"""Admin endpoints (P1): reprocess events."""

import json

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.exceptions import NotFoundError, UnprocessableError
from src.logging_config import get_logger
from src.models import WebhookDLQ, WebhookRetry
from src.repositories.webhook_repository import WebhookRepository
from src.services.webhook_processor import WebhookProcessor, WebhookProcessorError

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger("admin")


@router.post("/reprocess/{event_id}", status_code=status.HTTP_200_OK)
async def reprocess_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reprocess a webhook event by ID. Looks up from webhook_events, retry queue, or DLQ.
    Useful for retrying failed events after fixing issues.
    """
    webhook_repo = WebhookRepository(db)

    # 1. Try webhook_events
    existing = await webhook_repo.get_by_event_id(event_id)
    if existing:
        if existing.processing_status == "processed":
            return {"status": "already_processed", "event_id": event_id}
        raw_payload = existing.raw_payload
    else:
        # 2. Try retry queue
        retry = await webhook_repo.get_retry_by_event_id(event_id)
        if retry:
            raw_payload = retry.raw_payload
        else:
            # 3. Try DLQ
            result = await db.execute(
                select(WebhookDLQ).where(WebhookDLQ.event_id == event_id)
            )
            dlq = result.scalar_one_or_none()
            if dlq:
                raw_payload = dlq.raw_payload
            else:
                raise NotFoundError(f"Event {event_id} not found", resource="webhook_event")

    try:
        event_dict = json.loads(raw_payload)
        processor = WebhookProcessor(db)
        await processor.process_event(event_dict)
        if existing is not None:
            await webhook_repo.mark_processed(existing)
        logger.info("event_reprocessed", event_id=event_id)
    except WebhookProcessorError as e:
        raise UnprocessableError(str(e), details={"event_id": event_id})

    return {"status": "reprocessed", "event_id": event_id}
