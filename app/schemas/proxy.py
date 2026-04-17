"""Proxy schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.proxy import ServiceType


class ProxyCreate(BaseModel):
    """Schema for creating a proxy."""

    host: str = Field(..., min_length=1, max_length=255, description="代理主机")
    port: int = Field(..., ge=1, le=65535, description="代理端口")
    username: str | None = Field(default=None, max_length=128, description="用户名")
    password: str | None = Field(default=None, max_length=128, description="密码")
    service_type: ServiceType = Field(default=ServiceType.FETCH, description="服务类型")


class ProxyUpdate(BaseModel):
    """Schema for updating a proxy."""

    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, max_length=128)
    service_type: ServiceType | None = None
    is_active: bool | None = None


class ProxyResponse(BaseModel):
    """Schema for proxy response."""

    id: int
    host: str
    port: int
    username: str | None
    service_type: ServiceType
    success_rate: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProxyTestResult(BaseModel):
    """Schema for proxy test result."""

    proxy_id: int
    success: bool
    latency_ms: float | None = None
    error: str | None = None


class ProxyListResponse(BaseModel):
    """Schema for paginated proxy list response."""

    total: int
    items: list[ProxyResponse]
    page: int
    page_size: int
    total_pages: int
