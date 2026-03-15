"""AI anomaly detection for billing patterns using statistical methods."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    is_anomaly: bool
    score: float
    threshold: float
    message: str
    details: dict[str, Any]


class AnomalyDetector:
    """
    Detects anomalies in billing/usage data using Z-score and IQR methods.
    Suitable for real-time webhook streams and batch analysis.
    """

    def __init__(self, z_threshold: float = 3.0, iqr_multiplier: float = 1.5) -> None:
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier

    def detect_amount_anomaly(
        self, amount_cents: float, historical_amounts: Sequence[float]
    ) -> AnomalyResult:
        """Detect if an amount is anomalous compared to historical data."""
        if not historical_amounts:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=self.z_threshold,
                message="Insufficient historical data",
                details={},
            )
        arr = np.array(historical_amounts, dtype=float)
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        if std == 0:
            return AnomalyResult(
                is_anomaly=amount_cents != mean,
                score=float("inf") if amount_cents != mean else 0.0,
                threshold=self.z_threshold,
                message="No variance in historical data" if amount_cents != mean else "Normal",
                details={"mean": mean, "std": 0},
            )
        z_score = abs((amount_cents - mean) / std)
        is_anomaly = z_score > self.z_threshold
        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=float(z_score),
            threshold=self.z_threshold,
            message=f"Anomaly detected (z={z_score:.2f})" if is_anomaly else "Normal",
            details={"mean": mean, "std": std, "z_score": float(z_score)},
        )

    def detect_volume_anomaly(
        self, event_count: int, historical_counts: Sequence[int]
    ) -> AnomalyResult:
        """Detect if event volume is anomalous (e.g. spike in webhook traffic)."""
        if not historical_counts:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                threshold=self.z_threshold,
                message="Insufficient historical data",
                details={},
            )
        arr = np.array(historical_counts, dtype=float)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1
        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr
        is_anomaly = event_count < lower or event_count > upper
        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=float(event_count),
            threshold=float(upper),
            message=f"Volume anomaly (outside IQR [{lower:.0f}, {upper:.0f}])" if is_anomaly else "Normal",
            details={"q1": q1, "q3": q3, "iqr": iqr, "value": event_count},
        )
