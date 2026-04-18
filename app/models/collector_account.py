"""Collector account model for WeRead and MP admin credentials."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enum_utils import value_enum

if TYPE_CHECKING:
    from app.models.proxy import Proxy
    from app.models.user import User


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
    cool_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="账号冷却截止时间",
    )
    last_error_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="最近一次抓取失败分类",
    )
    login_proxy_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("proxies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="登录会话锁定代理",
    )
    login_proxy_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="登录成功后是否锁定代理",
    )
    last_login_proxy_ip: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="最近登录出口 IP",
    )
    login_proxy_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="登录代理最近变更时间",
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    owner: Mapped["User"] = relationship("User")
    login_proxy: Mapped["Proxy | None"] = relationship("Proxy")
