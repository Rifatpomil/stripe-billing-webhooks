"""Application configuration."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "billing-webhooks-service"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/billing"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""  # whsec_...
    stripe_api_version: str = "2024-11-20.acacia"

    # Webhook processing
    webhook_retry_max_attempts: int = 5
    webhook_retry_delay_seconds: int = 60
    webhook_retry_worker_enabled: bool = True
    webhook_retry_worker_interval_seconds: int = 60


def get_settings() -> Settings:
    """Return settings. Cached in production; bypass cache when TESTING=1."""
    if os.getenv("TESTING", "").lower() in ("1", "true", "yes"):
        return Settings()
    return _get_settings_cached()


@lru_cache(maxsize=1)
def _get_settings_cached() -> Settings:
    """Cached settings for production."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear settings cache (for tests)."""
    _get_settings_cached.cache_clear()
