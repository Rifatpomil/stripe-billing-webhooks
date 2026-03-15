"""AI-powered webhook event classification and routing hints."""

import re
from typing import Any


# Priority mapping: critical billing events get higher priority
EVENT_PRIORITY: dict[str, int] = {
    "invoice.payment_failed": 10,
    "customer.subscription.deleted": 9,
    "customer.subscription.updated": 7,
    "invoice.paid": 6,
    "customer.subscription.created": 5,
    "invoice.created": 4,
    "invoice.finalized": 3,
}


def classify_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Classify webhook event: priority, category, suggested actions.
    No external API calls - rule-based for reliability.
    """
    event_type = event.get("type", "")
    data = event.get("data", {})
    obj = data.get("object", {})

    priority = EVENT_PRIORITY.get(event_type, 1)
    category = _infer_category(event_type)

    # Suggest reprocess if previously failed
    suggestions = []
    if "payment_failed" in event_type or "past_due" in str(obj.get("status", "")):
        suggestions.append("review_payment_method")
    if "deleted" in event_type or "canceled" in str(obj.get("status", "")):
        suggestions.append("check_churn_reason")

    return {
        "event_type": event_type,
        "priority": priority,
        "category": category,
        "suggested_actions": suggestions,
        "requires_ledger": category in ("billing", "subscription"),
    }


def _infer_category(event_type: str) -> str:
    if "subscription" in event_type:
        return "subscription"
    if "invoice" in event_type:
        return "billing"
    if "payment" in event_type:
        return "payment"
    if "customer" in event_type:
        return "customer"
    return "other"
