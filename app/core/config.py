"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/dynamicwepubmonitor",
        description="Database connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT token generation",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="JWT token expiration time in minutes",
    )

    # LLM API
    llm_api_url: str = Field(
        default="https://api.example.com/v1/chat/completions",
        description="LLM API endpoint URL",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="LLM model name",
    )

    # Application
    app_env: Literal["development", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(
        default=True,
        description="Debug mode",
    )

    # DynamicWeightAdjuster Configuration
    weight_frequency_ratio: float = Field(default=0.35)
    weight_recency_ratio: float = Field(default=0.25)
    weight_relevance_ratio: float = Field(default=0.25)
    weight_stability_ratio: float = Field(default=0.15)

    tier_threshold_tier1: float = Field(default=80.0)
    tier_threshold_tier2: float = Field(default=65.0)
    tier_threshold_tier3: float = Field(default=50.0)
    tier_threshold_tier4: float = Field(default=35.0)

    check_interval_tier1: int = Field(default=24)
    check_interval_tier2: int = Field(default=48)
    check_interval_tier3: int = Field(default=72)
    check_interval_tier4: int = Field(default=144)
    check_interval_tier5: int = Field(default=336)

    # Alert Thresholds
    high_relevance_threshold: float = Field(default=0.8)
    ai_consecutive_low_threshold: int = Field(default=3)

    # QR Code
    qr_code_expire_seconds: int = Field(default=180)
    weread_platform_url: str | None = Field(
        default=None,
        description="External WeRead login platform URL compatible with wewe-rss platform API",
    )
    weread_platform_timeout_seconds: int = Field(
        default=30,
        description="Timeout for WeRead platform login API calls",
    )
    media_root: str = Field(
        default="media",
        description="Local media root directory",
    )
    media_url_prefix: str = Field(
        default="/media",
        description="Public URL prefix for serving localized media files",
    )
    collector_health_check_interval_hours: int = Field(
        default=6,
        description="Interval in hours for periodic collector account health checks",
    )
    alert_webhook_url: str | None = Field(
        default=None,
        description="Optional webhook URL for delivering alert notifications",
    )
    default_admin_alias: str = Field(
        default="admin",
        description="Development alias accepted by login API for the default admin account",
    )
    default_admin_email: str = Field(
        default="admin@admin.com",
        description="Default admin account email for development bootstrap",
    )
    default_admin_password: str = Field(
        default="admin123",
        description="Default admin account password for development bootstrap",
    )
    ensure_default_admin: bool = Field(
        default=True,
        description="Ensure the default admin account exists on application startup",
    )

    @property
    def tier_thresholds(self) -> list[float]:
        """Return tier thresholds as a list."""
        return [
            self.tier_threshold_tier1,
            self.tier_threshold_tier2,
            self.tier_threshold_tier3,
            self.tier_threshold_tier4,
        ]

    @property
    def check_intervals(self) -> dict[int, int]:
        """Return check intervals per tier."""
        return {
            1: self.check_interval_tier1,
            2: self.check_interval_tier2,
            3: self.check_interval_tier3,
            4: self.check_interval_tier4,
            5: self.check_interval_tier5,
        }

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
