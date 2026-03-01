"""Subscription API tests."""

import json

import pytest
from httpx import AsyncClient

from tests.stripe_helpers import sign_webhook_payload


@pytest.mark.asyncio
async def test_get_subscriptions_empty(client: AsyncClient):
    """GET /v1/subscriptions/{customer_id} returns empty list for unknown customer."""
    response = await client.get("/v1/subscriptions/cus_unknown_123")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_subscriptions_after_webhook(client: AsyncClient):
    """GET /v1/subscriptions/{customer_id} returns subscriptions after webhook creates them."""
    event = {
        "id": "evt_sub_api_001",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_api_001",
                "customer": "cus_api_001",
                "status": "active",
                "current_period_start": 1704067200,
                "current_period_end": 1706745600,
                "cancel_at_period_end": False,
            }
        },
    }
    payload = json.dumps(event)
    sig = sign_webhook_payload(payload)
    await client.post(
        "/v1/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": sig, "Content-Type": "application/json"},
    )

    response = await client.get("/v1/subscriptions/cus_api_001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(s["stripe_customer_id"] == "cus_api_001" for s in data)
