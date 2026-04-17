"""Proxy model for proxy pool management."""

import enum

from sqlalchemy import String, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enum_utils import value_enum


class ServiceType(str, enum.Enum):
    """Service type enumeration for proxy routing."""
    POLLING = "polling"
    FETCH = "fetch"
    PARSE = "parse"
    AI = "ai"
    WEREAD_LIST = "weread_list"
    WEREAD_DETAIL = "weread_detail"
    MP_LIST = "mp_list"
    MP_DETAIL = "mp_detail"


class Proxy(Base, TimestampMixin):
    """Proxy model for managing proxy pool."""

    __tablename__ = "proxies"

    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="代理主机",
    )
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="代理端口",
    )
    username: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="用户名",
    )
    password: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="密码",
    )
    service_type: Mapped[ServiceType] = mapped_column(
        value_enum(ServiceType),
        default=ServiceType.FETCH,
        nullable=False,
        comment="服务类型",
    )
    success_rate: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
        comment="成功率 0-100",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用",
    )

    @property
    def proxy_url(self) -> str:
        """Get proxy URL for HTTP requests."""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port} ({self.service_type.value})>"
