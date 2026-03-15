"""Churn risk scoring for subscriptions."""

from typing import Any


def compute_churn_score(
    subscription: dict[str, Any],
    ledger_amounts: list[int],
    past_due_count: int = 0,
) -> dict[str, Any]:
    """
    Compute churn risk score (0-100) from subscription state and payment history.
    Heuristic-based; can be replaced with trained model.
    """
    score = 0.0
    factors = []

    status = subscription.get("status", "").lower()
    if status in ("canceled", "unpaid"):
        score = 100.0
        factors.append({"factor": "status", "weight": 1.0, "value": status})
    elif status == "past_due":
        score += 40
        factors.append({"factor": "past_due", "weight": 0.4, "value": "yes"})
    elif status == "incomplete":
        score += 25
        factors.append({"factor": "incomplete", "weight": 0.25, "value": "yes"})

    cancel_at_period_end = subscription.get("cancel_at_period_end", False)
    if cancel_at_period_end:
        score += 30
        factors.append({"factor": "cancel_scheduled", "weight": 0.3, "value": "yes"})

    if past_due_count > 0:
        score += min(past_due_count * 10, 30)
        factors.append({"factor": "past_due_history", "value": past_due_count})

    # Payment consistency: high variance in amounts might indicate instability
    if len(ledger_amounts) >= 3:
        avg = sum(ledger_amounts) / len(ledger_amounts)
        variance = sum((x - avg) ** 2 for x in ledger_amounts) / len(ledger_amounts)
        if variance > avg * avg:
            score += 10
            factors.append({"factor": "payment_variance", "value": "high"})

    score = min(100.0, score)
    risk_tier = "high" if score >= 70 else "medium" if score >= 40 else "low"

    return {
        "churn_score": round(score, 1),
        "risk_tier": risk_tier,
        "factors": factors,
    }
