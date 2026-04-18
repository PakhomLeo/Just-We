"""Schemas for system configurations."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArticleContentIntervalPolicyPayload(BaseModel):
    dynamic_enabled: bool = True
    min_seconds: int = Field(default=20, ge=10, le=30)
    max_seconds: int = Field(default=180, ge=60, le=300)

    @field_validator("max_seconds")
    @classmethod
    def max_must_exceed_min(cls, value: int, info):
        min_seconds = info.data.get("min_seconds")
        if min_seconds is not None and value <= min_seconds:
            raise ValueError("max_seconds must be greater than min_seconds")
        return value


class DailyAccountFetchPolicyPayload(BaseModel):
    daily_runs: int = Field(default=2, ge=1)
    quiet_start: str = "23:00"
    quiet_end: str = "06:00"
    allow_manual_in_quiet_window: bool = True
    allow_backlog_in_quiet_window: bool = True


class AIConfigPayload(BaseModel):
    api_url: str
    api_key: str
    model: str
    prompt_template: str
    enabled: bool = True
    text_api_url: str = ""
    text_api_key: str = ""
    text_model: str = ""
    text_enabled: bool = True
    image_api_url: str = ""
    image_api_key: str = ""
    image_model: str = ""
    image_enabled: bool = True
    text_analysis_prompt: str = ""
    image_analysis_prompt: str = ""
    type_judgment_prompt: str = ""
    target_article_type: str = ""
    timeout_seconds: int = 60


class FetchPolicyPayload(BaseModel):
    tier_thresholds: dict[str, float]
    check_intervals: dict[str, int]
    primary_modes: dict[str, str]
    retry_limit: int
    retry_backoff_seconds: int
    random_delay_min_ms: int
    random_delay_max_ms: int
    rate_limit_policy: dict[str, Any] = {}
    history_backfill_policy: dict[str, Any] = {}
    notification_policy: dict[str, Any] = {}
    article_content_interval_policy: ArticleContentIntervalPolicyPayload = Field(
        default_factory=ArticleContentIntervalPolicyPayload
    )
    daily_account_fetch_policy: DailyAccountFetchPolicyPayload = Field(
        default_factory=DailyAccountFetchPolicyPayload
    )


class NotificationEmailConfigPayload(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    to_emails: list[str] = []
    use_tls: bool = True
    webhook_enabled: bool = False
    webhook_url: str = ""


class RateLimitPolicyPayload(BaseModel):
    global_limit_per_minute: int = 60
    account_limit_per_minute: int = 20
    proxy_limit_per_minute: int = 30
    monitored_limit_per_minute: int = 20
    detail_min_interval_seconds: float = 1.0
    proxy_failure_cooldown_seconds: int = 120


class NotificationPolicyPayload(BaseModel):
    credential_check_interval_hours: int = 6
    expiring_notice_hours: list[int] = [24, 6]
    webhook_enabled: bool = False
    webhook_url: str = ""


class ProxyPolicyPayload(BaseModel):
    disable_direct_wechat_fetch: bool = True
    min_success_rate: float = 50.0
    proxy_failure_cooldown_seconds: int = 120
    detail_rotation_strategy: str = "round_robin"
    list_sticky_ttl_seconds: int = 1800
