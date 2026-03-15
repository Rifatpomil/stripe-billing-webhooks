"""AI-powered alerting: detect when to alert based on patterns."""

from typing import Any


def should_alert(
    metric_name: str,
    value: float,
    baseline_mean: float,
    baseline_std: float,
    threshold_sigma: float = 3.0,
) -> dict[str, Any]:
    """
    Determine if a metric value warrants an alert (statistical outlier).
    Returns alert recommendation and severity.
    """
    if baseline_std <= 0:
        return {"alert": False, "reason": "insufficient_data", "severity": None}

    z_score = abs(value - baseline_mean) / baseline_std if baseline_std else 0
    alert = z_score >= threshold_sigma
    severity = "critical" if z_score >= 4 else "warning" if z_score >= 3 else None

    return {
        "alert": alert,
        "z_score": round(z_score, 2),
        "severity": severity,
        "metric": metric_name,
        "value": value,
        "baseline_mean": baseline_mean,
    }
