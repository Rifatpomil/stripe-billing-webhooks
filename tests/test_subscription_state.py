"""Subscription state machine tests (require Postgres with trigger)."""

import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# These tests require Postgres - skip if using SQLite
pytestmark = pytest.mark.skipif(
    "sqlite" in os.getenv("TEST_DATABASE_URL", "sqlite"),
    reason="Subscription state trigger requires Postgres",
)


@pytest.mark.asyncio
async def test_illegal_subscription_transition_rejected(db_session: AsyncSession):
    """
    Illegal state transition (e.g. active -> unpaid directly) is rejected by DB trigger.
    Valid: active -> past_due -> unpaid. Invalid: active -> unpaid.
    """
    from src.models import Subscription

    # Create subscription in 'active' state
    sub = Subscription(
        stripe_subscription_id="sub_test_001",
        stripe_customer_id="cus_001",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    # Attempt illegal transition: active -> unpaid (must go through past_due)
    sub.status = "unpaid"
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.flush()
    assert "transition" in str(exc_info.value).lower() or "check_violation" in str(exc_info.value).lower()
