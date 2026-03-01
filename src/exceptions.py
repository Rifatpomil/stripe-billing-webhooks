"""Custom exceptions and error handling."""

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    """Validation failed (400)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="validation_error", status_code=400, details=details)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, message: str, resource: str | None = None) -> None:
        details = {"resource": resource} if resource else {}
        super().__init__(message, code="not_found", status_code=404, details=details)


class ConflictError(AppError):
    """Conflict with current state (409)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="conflict", status_code=409, details=details)


class UnprocessableError(AppError):
    """Cannot process (e.g. invalid state transition) (422)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="unprocessable", status_code=422, details=details)


class ServiceUnavailableError(AppError):
    """Service not configured or unavailable (503)."""

    def __init__(self, message: str, service: str | None = None) -> None:
        details = {"service": service} if service else {}
        super().__init__(message, code="service_unavailable", status_code=503, details=details)


class StripeError(AppError):
    """Stripe API error (400)."""

    def __init__(self, message: str, stripe_error: str | None = None) -> None:
        details = {"stripe_error": stripe_error} if stripe_error else {}
        super().__init__(message, code="stripe_error", status_code=400, details=details)
