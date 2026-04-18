"""Proxy model for proxy pool management."""

import enum
from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class ProxyKind(str, enum.Enum):
    """Commercial/operational proxy kind."""

    DATACENTER = "datacenter"
    ISP_STATIC = "isp_static"
    RESIDENTIAL_STATIC = "residential_static"
    RESIDENTIAL_ROTATING = "residential_rotating"
    MOBILE_STATIC = "mobile_static"
    MOBILE_ROTATING = "mobile_rotating"
    CUSTOM_GATEWAY = "custom_gateway"


class ProxyRotationMode(str, enum.Enum):
    """How this proxy should be selected."""

    FIXED = "fixed"
    STICKY = "sticky"
    ROUND_ROBIN = "round_robin"
    PER_REQUEST = "per_request"
    PROVIDER_AUTO = "provider_auto"


class ProxyServiceKey(str, enum.Enum):
    """Business services that can consume a proxy."""

    MP_ADMIN_LOGIN = "mp_admin_login"
    MP_LIST = "mp_list"
    MP_DETAIL = "mp_detail"
    WEREAD_LOGIN = "weread_login"
    WEREAD_LIST = "weread_list"
    WEREAD_DETAIL = "weread_detail"
    IMAGE_PROXY = "image_proxy"
    AI = "ai"


LEGACY_SERVICE_TO_PROXY_SERVICE = {
    ServiceType.AI: ProxyServiceKey.AI,
    ServiceType.WEREAD_LIST: ProxyServiceKey.WEREAD_LIST,
    ServiceType.WEREAD_DETAIL: ProxyServiceKey.WEREAD_DETAIL,
    ServiceType.MP_LIST: ProxyServiceKey.MP_LIST,
    ServiceType.MP_DETAIL: ProxyServiceKey.MP_DETAIL,
    ServiceType.FETCH: ProxyServiceKey.MP_DETAIL,
    ServiceType.PARSE: ProxyServiceKey.IMAGE_PROXY,
    ServiceType.POLLING: ProxyServiceKey.WEREAD_LIST,
}


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
        comment="兼容旧接口的默认服务类型；新逻辑使用 proxy_service_bindings",
    )
    proxy_kind: Mapped[ProxyKind] = mapped_column(
        value_enum(ProxyKind),
        default=ProxyKind.RESIDENTIAL_ROTATING,
        nullable=False,
        comment="代理类型",
    )
    rotation_mode: Mapped[ProxyRotationMode] = mapped_column(
        value_enum(ProxyRotationMode),
        default=ProxyRotationMode.ROUND_ROBIN,
        nullable=False,
        comment="轮换模式",
    )
    sticky_ttl_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="粘性会话时长",
    )
    provider_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="代理供应商或来源",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
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
    fail_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="失败冷却截止时间",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="最近失败原因",
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近检测时间",
    )

    @property
    def proxy_url(self) -> str:
        """Get proxy URL for HTTP requests."""
        if "://" in self.host:
            if self.username and self.password and "@" not in self.host:
                scheme, _, rest = self.host.partition("://")
                return f"{scheme}://{self.username}:{self.password}@{rest}:{self.port}"
            return f"{self.host}:{self.port}"
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port} ({self.service_type.value})>"

    @property
    def service_keys(self) -> list[ProxyServiceKey]:
        return [
            binding.service_key
            for binding in (self.service_bindings or [])
            if binding.is_enabled
        ]

    service_bindings: Mapped[list["ProxyServiceBinding"]] = relationship(
        "ProxyServiceBinding",
        cascade="all, delete-orphan",
        back_populates="proxy",
        lazy="selectin",
    )


class ProxyServiceBinding(Base, TimestampMixin):
    """Map a proxy to one or more business services."""

    __tablename__ = "proxy_service_bindings"
    __table_args__ = (
        UniqueConstraint("proxy_id", "service_key", name="uq_proxy_service_binding_proxy_service"),
    )

    proxy_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proxies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_key: Mapped[ProxyServiceKey] = mapped_column(
        value_enum(ProxyServiceKey),
        nullable=False,
        index=True,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    proxy: Mapped[Proxy] = relationship("Proxy", back_populates="service_bindings")
