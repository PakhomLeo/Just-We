"""Account model for WeChat public accounts."""

import enum
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enum_utils import value_enum


class AccountType(str, enum.Enum):
    """Account type enumeration."""
    WEREAD = "weread"
    MP = "mp"


class AccountStatus(str, enum.Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class HealthStatus(str, enum.Enum):
    """Health status enumeration."""
    NORMAL = "normal"      # 绿色 - 正常可用
    RESTRICTED = "restricted"  # 红色 - 小黑屋/被限制
    EXPIRED = "expired"    # 橘红色 - Cookie 过期/登录失效
    INVALID = "invalid"    # 灰色 - 完全不可用


class Account(Base, TimestampMixin):
    """WeChat public account model."""

    __tablename__ = "accounts"

    biz: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="公众号唯一标识",
    )
    fakeid: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="公众号 fakeid",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="公众号名称",
    )
    account_type: Mapped[AccountType] = mapped_column(
        value_enum(AccountType),
        default=AccountType.MP,
        nullable=False,
        comment="账号来源：weread 或 mp",
    )
    current_tier: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="当前权重等级 1-5",
    )
    composite_score: Mapped[float] = mapped_column(
        Float,
        default=50.0,
        nullable=False,
        comment="综合得分 0-100",
    )
    last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="上次检查时间",
    )
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="上次更新时间（文章）",
    )
    update_history: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="近90天更新记录 {timestamp: update_count}",
    )
    ai_relevance_history: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="AI 分析历史 {timestamp: {ratio, reason}}",
    )
    manual_override: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="手动覆盖 {target_tier, expire_at, reason}",
    )
    cookies: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="登录凭证",
    )
    cookies_expire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Cookie 过期时间",
    )
    status: Mapped[AccountStatus] = mapped_column(
        value_enum(AccountStatus),
        default=AccountStatus.ACTIVE,
        nullable=False,
        comment="账号状态",
    )
    # Health check fields
    health_status: Mapped[HealthStatus] = mapped_column(
        value_enum(HealthStatus),
        default=HealthStatus.NORMAL,
        nullable=False,
        comment="健康状态: normal/restricted/expired/invalid",
    )
    last_health_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后健康检查时间",
    )
    health_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="健康检查失败原因",
    )

    # Relationships
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Account {self.name} ({self.biz})>"
