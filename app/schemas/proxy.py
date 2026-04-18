"""Proxy schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.proxy import ProxyKind, ProxyRotationMode, ProxyServiceKey, ServiceType


class ProxyCreate(BaseModel):
    """Schema for creating a proxy."""

    host: str = Field(..., min_length=1, max_length=255, description="代理主机")
    port: int = Field(..., ge=1, le=65535, description="代理端口")
    username: str | None = Field(default=None, max_length=128, description="用户名")
    password: str | None = Field(default=None, max_length=128, description="密码")
    service_type: ServiceType = Field(default=ServiceType.FETCH, description="服务类型")
    proxy_kind: ProxyKind = Field(default=ProxyKind.RESIDENTIAL_ROTATING, description="代理类型")
    rotation_mode: ProxyRotationMode = Field(default=ProxyRotationMode.ROUND_ROBIN, description="轮换模式")
    sticky_ttl_seconds: int | None = Field(default=None, ge=1, description="粘性会话时长")
    provider_name: str | None = Field(default=None, max_length=128, description="供应商")
    notes: str | None = Field(default=None, description="备注")
    service_keys: list[ProxyServiceKey] | None = Field(default=None, description="绑定服务")


class ProxyUpdate(BaseModel):
    """Schema for updating a proxy."""

    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, max_length=128)
    service_type: ServiceType | None = None
    proxy_kind: ProxyKind | None = None
    rotation_mode: ProxyRotationMode | None = None
    sticky_ttl_seconds: int | None = Field(default=None, ge=1)
    provider_name: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    is_active: bool | None = None


class ProxyResponse(BaseModel):
    """Schema for proxy response."""

    id: int
    host: str
    port: int
    username: str | None
    service_type: ServiceType
    proxy_kind: ProxyKind
    rotation_mode: ProxyRotationMode
    sticky_ttl_seconds: int | None = None
    provider_name: str | None = None
    notes: str | None = None
    service_keys: list[ProxyServiceKey] = []
    success_rate: float
    is_active: bool
    fail_until: datetime | None = None
    last_error: str | None = None
    last_checked_at: datetime | None = None
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


class ProxyBulkCreate(BaseModel):
    proxies: list[ProxyCreate] = Field(..., min_length=1, max_length=500)


class ProxyBulkCreateResponse(BaseModel):
    created: int
    items: list[ProxyResponse]


class ProxyServiceBindingResponse(BaseModel):
    service_key: ProxyServiceKey
    is_enabled: bool
    priority: int

    model_config = {"from_attributes": True}


class ProxyServicesUpdate(BaseModel):
    service_keys: list[ProxyServiceKey] = Field(default_factory=list)


class ProxyServicesResponse(BaseModel):
    proxy_id: int
    service_keys: list[ProxyServiceKey]
    compatible_service_keys: list[ProxyServiceKey]
    incompatible_reasons: dict[str, str]
