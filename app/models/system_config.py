"""System-wide singleton configuration models."""

from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AIAnalysisConfig(Base, TimestampMixin):
    __tablename__ = "ai_analysis_configs"

    api_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    text_api_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    text_api_key: Mapped[str] = mapped_column(Text, default="", nullable=False)
    text_model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    text_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_api_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_api_key: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    text_analysis_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_analysis_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    type_judgment_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_article_type: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)


class FetchPolicy(Base, TimestampMixin):
    __tablename__ = "fetch_policies"

    tier_thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    check_intervals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    primary_modes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    retry_limit: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    random_delay_min_ms: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    random_delay_max_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    rate_limit_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    proxy_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    history_backfill_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notification_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    @property
    def article_content_interval_policy(self) -> dict:
        """Article detail pacing policy stored inside rate_limit_policy JSON."""
        return (self.rate_limit_policy or {}).get(
            "article_content_interval_policy",
            {"dynamic_enabled": True, "min_seconds": 20, "max_seconds": 180},
        )

    @article_content_interval_policy.setter
    def article_content_interval_policy(self, value: dict) -> None:
        policy = dict(self.rate_limit_policy or {})
        policy["article_content_interval_policy"] = value or {}
        self.rate_limit_policy = policy

    @property
    def daily_account_fetch_policy(self) -> dict:
        """Automatic account polling policy stored inside history_backfill_policy JSON."""
        return (self.history_backfill_policy or {}).get(
            "daily_account_fetch_policy",
            {
                "daily_runs": 2,
                "quiet_start": "23:00",
                "quiet_end": "06:00",
                "allow_manual_in_quiet_window": True,
                "allow_backlog_in_quiet_window": True,
            },
        )

    @daily_account_fetch_policy.setter
    def daily_account_fetch_policy(self, value: dict) -> None:
        policy = dict(self.history_backfill_policy or {})
        policy["daily_account_fetch_policy"] = value or {}
        self.history_backfill_policy = policy


class NotificationEmailConfig(Base, TimestampMixin):
    __tablename__ = "notification_email_configs"

    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    smtp_host: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    smtp_username: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    smtp_password: Mapped[str] = mapped_column(Text, default="", nullable=False)
    from_email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    to_emails: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
