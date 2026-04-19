"""Schemas for monitored accounts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.models.collector_account import CollectorAccountType
from app.models.monitored_account import MonitoredAccountStatus


class MonitoredAccountCreate(BaseModel):
    source_url: str = Field(..., min_length=1)
    name: str | None = None
    fakeid: str | None = None


class MonitoredAccountUpdate(BaseModel):
    name: str | None = None
    fakeid: str | None = None
    status: MonitoredAccountStatus | None = None
    target_tier: int | None = Field(default=None, ge=1, le=5)


class MonitoredAccountResponse(BaseModel):
    id: int
    owner_user_id: UUID
    biz: str
    fakeid: str | None
    feed_token: str
    name: str
    source_url: str
    avatar_url: str | None
    mp_intro: str | None = None
    metadata_json: dict | None = None
    current_tier: int
    composite_score: float
    primary_fetch_mode: CollectorAccountType = Field(exclude=True)
    status: MonitoredAccountStatus
    last_polled_at: datetime | None
    last_published_at: datetime | None
    next_scheduled_at: datetime | None
    manual_override: dict | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def tier(self) -> int:
        return self.current_tier

    @computed_field
    @property
    def score(self) -> float:
        return self.composite_score

    @computed_field
    @property
    def fetch_mode(self) -> CollectorAccountType:
        return self.primary_fetch_mode

    model_config = {"from_attributes": True}


class MonitoredAccountListResponse(BaseModel):
    total: int
    items: list[MonitoredAccountResponse]
