"""User model for authentication with fastapi-users."""

import enum
import uuid
from datetime import datetime

from fastapi_users import UUIDIDMixin
from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enum_utils import value_enum


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(UUIDIDMixin, Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(length=320),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        value_enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
