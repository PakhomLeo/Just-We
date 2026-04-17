"""QR code login schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.models.collector_account import CollectorAccountType


class QRGenerateRequest(BaseModel):
    """Schema for QR code generation request."""

    type: CollectorAccountType = CollectorAccountType.MP_ADMIN


class QRGenerateResponse(BaseModel):
    """Schema for QR code generation response."""

    qr_url: str
    ticket: str
    expire_at: datetime
    provider: str | None = None


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
