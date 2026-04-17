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


class FetchPolicy(Base, TimestampMixin):
    __tablename__ = "fetch_policies"

    tier_thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    check_intervals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    primary_modes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    retry_limit: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    random_delay_min_ms: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    random_delay_max_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)


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
