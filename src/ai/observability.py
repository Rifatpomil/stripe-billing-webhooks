"""AI observability: structured log analysis and metric anomaly detection."""

from typing import Any


def analyze_metric_trend(
    values: list[float],
    window: int = 5,
) -> dict[str, Any]:
    """
    Detect trend and anomalies in a metric series.
    Simple heuristic: compare recent window vs previous.
    """
    if len(values) < window * 2:
        return {"trend": "unknown", "anomaly": False, "reason": "insufficient_data"}

    recent = values[-window:]
    previous = values[-(window * 2) : -window]
    recent_avg = sum(recent) / len(recent)
    prev_avg = sum(previous) / len(previous)

    change_pct = ((recent_avg - prev_avg) / prev_avg * 100) if prev_avg else 0
    trend = "up" if change_pct > 5 else "down" if change_pct < -5 else "stable"
    anomaly = abs(change_pct) > 50

    return {
        "trend": trend,
        "change_percent": round(change_pct, 2),
        "anomaly": anomaly,
        "recent_avg": round(recent_avg, 2),
        "previous_avg": round(prev_avg, 2),
    }
