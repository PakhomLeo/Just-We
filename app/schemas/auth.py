"""Authentication schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Login request schema."""

    email: str
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Registration request schema."""

    email: EmailStr
    username: str | None = Field(default=None, min_length=2, max_length=80)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str
    exp: datetime
    iat: datetime | None = None


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    email: str
    username: str | None = None
    role: UserRole
    aggregate_feed_token: str
    is_active: bool
    is_superuser: bool
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update schema."""

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=2, max_length=80)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None
