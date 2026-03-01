"""Usage API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_usage_record(client: AsyncClient):
    """POST /v1/usage/records creates a record."""
    response = await client.post(
        "/v1/usage/records",
        json={
            "stripe_customer_id": "cus_usage_001",
            "stripe_subscription_item_id": "si_001",
            "meter_name": "api_calls",
            "quantity": 42,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["meter_name"] == "api_calls"
    assert data["quantity"] == 42


@pytest.mark.asyncio
async def test_get_usage_aggregation(client: AsyncClient):
    """GET /v1/usage/aggregate/{customer_id} returns aggregation."""
    # Create a record first
    await client.post(
        "/v1/usage/records",
        json={
            "stripe_customer_id": "cus_agg_001",
            "stripe_subscription_item_id": "si_001",
            "meter_name": "api_calls",
            "quantity": 10,
        },
    )

    response = await client.get(
        "/v1/usage/aggregate/cus_agg_001",
        params={"meter_name": "api_calls", "days": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "cus_agg_001"
    assert data["meter_name"] == "api_calls"
    assert data["total_quantity"] >= 10
    assert data["record_count"] >= 1


@pytest.mark.asyncio
async def test_get_usage_aggregation_empty(client: AsyncClient):
    """GET aggregation for customer with no usage returns zeros."""
    response = await client.get(
        "/v1/usage/aggregate/cus_no_usage_999",
        params={"meter_name": "api_calls", "days": 7},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_quantity"] == 0
    assert data["record_count"] == 0
