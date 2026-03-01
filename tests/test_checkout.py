"""Checkout endpoint tests."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_checkout_stripe_not_configured_returns_503(client: AsyncClient):
    """When Stripe is not configured, returns 503."""
    with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
        response = await client.post(
            "/v1/checkout/session",
            json={
                "customer_id": "cus_123",
                "price_id": "price_123",
            },
        )
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert "stripe" in data["error"].lower()


@pytest.mark.asyncio
async def test_checkout_creates_session_when_configured(client: AsyncClient):
    """When Stripe is configured, creates checkout session."""
    mock_session = MagicMock()
    mock_session.id = "cs_test_123"
    mock_session.url = "https://checkout.stripe.com/..."

    with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}, clear=False):
        with patch("src.api.routes.checkout.stripe.checkout.Session.create", return_value=mock_session):
            response = await client.post(
                "/v1/checkout/session",
                json={
                    "customer_id": "cus_123",
                    "price_id": "price_123",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "cs_test_123"
            assert data["url"] == "https://checkout.stripe.com/..."
