"""Collector account model for WeRead and MP admin credentials."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enum_utils import value_enum


class CollectorAccountType(str, enum.Enum):
    WEREAD = "weread"
    MP_ADMIN = "mp_admin"


class CollectorAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"
    ERROR = "error"


class CollectorHealthStatus(str, enum.Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    EXPIRED = "expired"
    INVALID = "invalid"


class RiskStatus(str, enum.Enum):
    NORMAL = "normal"
    COOLING = "cooling"
    BLOCKED = "blocked"


class CollectorAccount(Base, TimestampMixin):
    __tablename__ = "collector_accounts"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_type: Mapped[CollectorAccountType] = mapped_column(
        value_enum(CollectorAccountType),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    credentials: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[CollectorAccountStatus] = mapped_column(
        value_enum(CollectorAccountStatus),
        default=CollectorAccountStatus.ACTIVE,
        nullable=False,
    )
    health_status: Mapped[CollectorHealthStatus] = mapped_column(
        value_enum(CollectorHealthStatus),
        default=CollectorHealthStatus.NORMAL,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    risk_status: Mapped[RiskStatus] = mapped_column(
        value_enum(RiskStatus),
        default=RiskStatus.NORMAL,
        nullable=False,
    )
    risk_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    owner: Mapped["User"] = relationship("User")
