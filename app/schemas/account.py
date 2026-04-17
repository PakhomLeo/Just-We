"""Account schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from app.models.account import AccountType, AccountStatus, HealthStatus


class AccountCreate(BaseModel):
    """Schema for creating an account."""

    biz: str = Field(..., min_length=1, max_length=64, description="公众号唯一标识")
    fakeid: str = Field(..., min_length=1, max_length=64, description="公众号 fakeid")
    name: str = Field(..., min_length=1, max_length=255, description="公众号名称")
    account_type: AccountType = Field(default=AccountType.MP, description="账号来源")
    cookies: dict[str, Any] | None = Field(default=None, description="登录凭证")


class AccountUpdate(BaseModel):
    """Schema for updating an account."""

    name: str | None = Field(default=None, max_length=255)
    fakeid: str | None = Field(default=None, max_length=64)
    cookies: dict[str, Any] | None = None
    status: AccountStatus | None = None
    manual_override: dict[str, Any] | None = None


class AccountResponse(BaseModel):
    """Schema for account response."""

    id: int
    biz: str
    fakeid: str
    name: str
    account_type: AccountType
    current_tier: int
    composite_score: float
    last_checked: datetime | None
    last_updated: datetime | None
    update_history: dict[str, Any]
    ai_relevance_history: dict[str, Any]
    manual_override: dict[str, Any] | None
    cookies: dict[str, Any] | None
    cookies_expire_at: datetime | None
    status: AccountStatus
    # Health check fields
    health_status: HealthStatus
    last_health_check: datetime | None
    health_reason: str | None
    created_at: datetime
    updated_at: datetime

    # Computed fields for frontend compatibility
    @computed_field
    @property
    def tier(self) -> int:
        """Alias for current_tier."""
        return self.current_tier

    @computed_field
    @property
    def score(self) -> float:
        """Alias for composite_score."""
        return self.composite_score

    @computed_field
    @property
    def last_check(self) -> datetime | None:
        """Alias for last_checked."""
        return self.last_checked

    @computed_field
    @property
    def last_update(self) -> datetime | None:
        """Alias for last_updated."""
        return self.last_updated

    @computed_field
    @property
    def article_count(self) -> int:
        """Article count - requires separate query in production."""
        return 0

    @computed_field
    @property
    def next_check(self) -> str | None:
        """Next check time - calculated from tier."""
        return None

    @computed_field
    @property
    def health_status_text(self) -> str:
        """Health status display text."""
        status_map = {
            HealthStatus.NORMAL: "正常",
            HealthStatus.RESTRICTED: "小黑屋",
            HealthStatus.EXPIRED: "已过期",
            HealthStatus.INVALID: "无效",
        }
        return status_map.get(self.health_status, "未知")

    @computed_field
    @property
    def cookies_remaining_days(self) -> int | None:
        """Days until cookies expire."""
        if not self.cookies_expire_at:
            return None
        now = datetime.now(self.cookies_expire_at.tzinfo)
        remaining = (self.cookies_expire_at - now).days
        return max(0, remaining)

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """Schema for paginated account list response."""

    total: int
    items: list[AccountResponse]
    page: int
    page_size: int
    total_pages: int


class ManualOverrideRequest(BaseModel):
    """Schema for manual override request."""

    target_tier: int = Field(..., ge=1, le=5, description="目标权重等级 1-5")
    reason: str = Field(..., min_length=1, max_length=500, description="原因")
    expire_at: datetime | None = Field(
        default=None,
        description="过期时间，不提供则默认24小时后",
    )


class AccountHistoryResponse(BaseModel):
    """Schema for account history response."""

    update_history: dict[str, Any]
    ai_relevance_history: dict[str, Any]
    tier_changes: list[dict[str, Any]]
    manual_overrides: list[dict[str, Any]]
