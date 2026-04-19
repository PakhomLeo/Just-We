"""Schemas for collector accounts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.collector_account import (
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)


class CollectorAccountResponse(BaseModel):
    id: int
    owner_user_id: UUID
    account_type: CollectorAccountType
    display_name: str
    external_id: str | None
    status: CollectorAccountStatus
    health_status: CollectorHealthStatus
    expires_at: datetime | None
    last_health_check: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    risk_status: RiskStatus
    risk_reason: str | None
    cool_until: datetime | None = None
    last_error_category: str | None = None
    bound_proxy_id: int | None = None
    login_proxy_id: int | None = None
    login_proxy_locked: bool = True
    last_login_proxy_ip: str | None = None
    login_proxy_changed_at: datetime | None = None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectorAccountListResponse(BaseModel):
    total: int
    items: list[CollectorAccountResponse]


class CollectorLoginProxyUpdate(BaseModel):
    login_proxy_id: int | None


class CollectorProxyUpdate(BaseModel):
    proxy_id: int | None
