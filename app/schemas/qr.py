"""QR code login schemas."""

from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field

from app.models.collector_account import CollectorAccountType


class QRGenerateRequest(BaseModel):
    """Schema for QR code generation request."""

    type: CollectorAccountType = Field(
        default=CollectorAccountType.MP_ADMIN,
        validation_alias=AliasChoices("type", "account_type"),
        serialization_alias="type",
    )
    proxy_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("proxy_id", "login_proxy_id"),
        description="账号登录/列表共用代理 ID；为空时直连",
    )


class QRGenerateResponse(BaseModel):
    """Schema for QR code generation response."""

    qr_url: str
    ticket: str
    expire_at: datetime
    provider: str | None = None
    proxy_id: int | None = None
    login_proxy_id: int | None = None


class QRStatusResponse(BaseModel):
    """Schema for QR code status response."""

    status: str  # waiting, scanned, confirmed, expired
    collector_account_id: int | None = None
    account_name: str | None = None
    message: str | None = None
    provider: str | None = None


class QRData(BaseModel):
    """Internal schema for QR code data stored in Redis."""

    ticket: str
    type: CollectorAccountType
    created_at: datetime
    expire_at: datetime
    status: str = "waiting"
    collector_account_id: int | None = None
    account_name: str | None = None
    cookies: dict | None = None
