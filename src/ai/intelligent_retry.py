"""Intelligent retry scheduling with adaptive backoff."""

import math
from datetime import datetime, timedelta, timezone


def compute_next_retry(
    attempt: int,
    base_delay_seconds: int = 60,
    max_delay_seconds: int = 3600,
    jitter: bool = True,
) -> datetime:
    """
    Exponential backoff with optional jitter.
    attempt 0 -> base_delay, 1 -> 2x, 2 -> 4x, etc.
    """
    delay = min(
        base_delay_seconds * (2**attempt),
        max_delay_seconds,
    )
    if jitter:
        delay = delay * (0.5 + 0.5 * (hash(str(attempt)) % 1000) / 1000)
    return datetime.now(timezone.utc) + timedelta(seconds=int(delay))


def estimate_success_probability(attempt: int, max_attempts: int = 5) -> float:
    """Heuristic: later attempts have lower success probability."""
    return max(0.1, 1.0 - (attempt / max_attempts) * 0.8)
