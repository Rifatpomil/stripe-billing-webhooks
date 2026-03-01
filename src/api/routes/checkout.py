"""Checkout session endpoint (optional)."""

import stripe

from fastapi import APIRouter
from pydantic import BaseModel

from src.config import get_settings
from src.exceptions import ServiceUnavailableError, StripeError
from src.logging_config import get_logger

router = APIRouter(prefix="/checkout", tags=["checkout"])
logger = get_logger("checkout")


class CheckoutSessionRequest(BaseModel):
    """Checkout session creation request."""

    customer_id: str
    price_id: str
    success_url: str = "https://example.com/success"
    cancel_url: str = "https://example.com/cancel"


class CheckoutSessionResponse(BaseModel):
    """Checkout session response."""

    session_id: str
    url: str | None


@router.post("/session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    body: CheckoutSessionRequest,
) -> CheckoutSessionResponse:
    """
    Create Stripe Checkout session for subscription.
    Requires STRIPE_SECRET_KEY to be configured.
    """
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise ServiceUnavailableError("Stripe not configured", service="stripe")

    stripe.api_key = settings.stripe_secret_key
    try:
        session = stripe.checkout.Session.create(
            customer=body.customer_id,
            mode="subscription",
            line_items=[{"price": body.price_id, "quantity": 1}],
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        logger.info("checkout_session_created", session_id=session.id, customer_id=body.customer_id)
        return CheckoutSessionResponse(
            session_id=session.id,
            url=session.url,
        )
    except stripe.error.StripeError as e:
        raise StripeError(str(e), stripe_error=str(e))
