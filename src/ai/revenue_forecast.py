"""Revenue forecasting using simple time-series heuristics."""

from datetime import datetime, timedelta, timezone
from typing import Any


def forecast_revenue(
    historical_amounts: list[tuple[datetime, int]],
    horizon_days: int = 30,
) -> dict[str, Any]:
    """
    Simple moving average forecast. For production, use ARIMA, Prophet, or LSTM.
    """
    if not historical_amounts:
        return {"forecast_daily_avg": 0, "forecast_total": 0, "method": "empty"}

    amounts = [a for _, a in historical_amounts]
    avg_daily = sum(amounts) / len(amounts)
    # Assume one transaction per period; scale by horizon
    forecast_total = avg_daily * horizon_days

    return {
        "forecast_daily_avg": round(avg_daily, 2),
        "forecast_total": round(forecast_total, 2),
        "horizon_days": horizon_days,
        "data_points": len(amounts),
        "method": "moving_average",
    }
