"""Stripe test helpers."""

import json
import time
import stripe

WEBHOOK_SECRET = "whsec_test_secret_12345"


def sign_webhook_payload(payload: str | bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Generate Stripe-Signature header for payload."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    timestamp = int(time.time())
    payload_to_sign = f"{timestamp}.{payload}"
    signature = stripe.WebhookSignature._compute_signature(payload_to_sign, secret)
    return f"t={timestamp},v1={signature}"
