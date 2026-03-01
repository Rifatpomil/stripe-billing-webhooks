"""Stripe webhook endpoint."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Webhook
from stripe.error import SignatureVerificationError

from src.api.deps import get_db
from src.config import get_settings
from src.exceptions import UnprocessableError, ValidationError
from src.logging_config import get_logger
from src.metrics import WEBHOOK_FAILED, WEBHOOK_PROCESSED, WEBHOOK_RECEIVED
from src.repositories.webhook_repository import WebhookRepository
from src.services.webhook_processor import WebhookProcessor, WebhookProcessorError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger("webhooks")


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Receive Stripe webhooks. Verifies signature, stores event, enforces idempotency,
    updates subscription state machine, writes ledger entries.
    """
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        return {"received": True, "message": "Webhook secret not configured (dev mode)"}

    # Must use raw body for signature verification
    payload = await request.body()
    payload_str = payload.decode("utf-8")
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = Webhook.construct_event(
            payload_str, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        WEBHOOK_RECEIVED.labels(event_type="unknown", status="invalid_payload").inc()
        raise ValidationError("Invalid payload", details={"hint": "Request body must be valid JSON"})
    except SignatureVerificationError:
        WEBHOOK_RECEIVED.labels(event_type="unknown", status="invalid_signature").inc()
        raise ValidationError("Invalid signature", details={"hint": "Check Stripe-Signature header"})

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    webhook_repo = WebhookRepository(db)

    # Idempotency: check if already processed
    existing = await webhook_repo.get_by_event_id(event_id)
    if existing:
        WEBHOOK_RECEIVED.labels(event_type=event_type, status="duplicate").inc()
        logger.info("webhook_duplicate", event_id=event_id, event_type=event_type)
        return {"received": True, "id": event_id, "duplicate": True}

    # Store raw event (append-only)
    stored = await webhook_repo.create_event(
        event_id=event_id,
        event_type=event_type,
        raw_payload=payload_str,
        processing_status="pending",
    )

    try:
        processor = WebhookProcessor(db)
        await processor.process_event(dict(event))
        await webhook_repo.mark_processed(stored)
        WEBHOOK_PROCESSED.labels(event_type=event_type).inc()
        logger.info("webhook_processed", event_id=event_id, event_type=event_type)
    except WebhookProcessorError as e:
        await webhook_repo.mark_failed(stored)
        WEBHOOK_FAILED.labels(event_type=event_type, reason="unprocessable").inc()
        logger.warning("webhook_unprocessable", event_id=event_id, event_type=event_type, error=str(e))
        raise UnprocessableError(str(e), details={"event_id": event_id})
    except Exception as e:
        await webhook_repo.mark_failed(stored)
        WEBHOOK_FAILED.labels(event_type=event_type, reason="retry").inc()
        logger.exception("webhook_failed_queued", event_id=event_id, event_type=event_type)
        # Add to retry queue - return 200 so Stripe doesn't retry; we handle retries
        next_retry = datetime.now(timezone.utc) + timedelta(
            seconds=get_settings().webhook_retry_delay_seconds
        )
        await webhook_repo.add_to_retry_queue(
            event_id=event_id,
            raw_payload=payload_str,
            event_type=event_type,
            error=str(e),
            next_retry_at=next_retry,
        )
        return {"received": True, "id": event_id, "queued_for_retry": True}

    WEBHOOK_RECEIVED.labels(event_type=event_type, status="processed").inc()
    return {"received": True, "id": event_id}
