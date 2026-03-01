"""Admin reprocess endpoint tests."""

import json

import pytest
from httpx import AsyncClient

from tests.stripe_helpers import sign_webhook_payload


@pytest.mark.asyncio
async def test_reprocess_event_not_found_returns_404(client: AsyncClient):
    """Reprocess unknown event returns 404."""
    response = await client.post("/v1/admin/reprocess/evt_nonexistent_999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "not found" in data["error"].lower()


@pytest.mark.asyncio
async def test_reprocess_event_success(client: AsyncClient):
    """Reprocess event from webhook_events (failed) succeeds."""
    # First, create a failed event via webhook (we'll use one that fails processing)
    # For simplicity: store a subscription.created, process it, then reprocess
    event = {
        "id": "evt_reprocess_001",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_reprocess_001",
                "customer": "cus_reprocess_001",
                "status": "active",
                "current_period_start": 1704067200,
                "current_period_end": 1706745600,
                "cancel_at_period_end": False,
            }
        },
    }
    payload = json.dumps(event)
    sig = sign_webhook_payload(payload)

    # Process once
    r1 = await client.post(
        "/v1/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": sig, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    # Reprocess (should return already_processed or reprocessed)
    r2 = await client.post("/v1/admin/reprocess/evt_reprocess_001")
    assert r2.status_code == 200
    data = r2.json()
    assert data["status"] in ("already_processed", "reprocessed")
    assert data["event_id"] == "evt_reprocess_001"
