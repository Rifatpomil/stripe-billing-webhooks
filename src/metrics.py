"""Prometheus metrics."""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response


# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Webhook metrics
WEBHOOK_RECEIVED = Counter(
    "webhook_events_received_total",
    "Total webhook events received",
    ["event_type", "status"],
)
WEBHOOK_PROCESSED = Counter(
    "webhook_events_processed_total",
    "Total webhook events successfully processed",
    ["event_type"],
)
WEBHOOK_FAILED = Counter(
    "webhook_events_failed_total",
    "Total webhook events failed",
    ["event_type", "reason"],
)


def get_metrics_response() -> Response:
    """Return Prometheus metrics as HTTP response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
