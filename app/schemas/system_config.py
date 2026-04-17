"""Schemas for system configurations."""

from pydantic import BaseModel


class AIConfigPayload(BaseModel):
    api_url: str
    api_key: str
    model: str
    prompt_template: str
    enabled: bool = True


class FetchPolicyPayload(BaseModel):
    tier_thresholds: dict[str, float]
    check_intervals: dict[str, int]
    primary_modes: dict[str, str]
    retry_limit: int
    retry_backoff_seconds: int
    random_delay_min_ms: int
    random_delay_max_ms: int


class NotificationEmailConfigPayload(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    to_emails: list[str] = []
    use_tls: bool = True
