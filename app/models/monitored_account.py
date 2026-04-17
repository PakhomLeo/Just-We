"""Monitored public account model."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.collector_account import CollectorAccountType
from app.models.enum_utils import value_enum


class MonitoredAccountStatus(str, enum.Enum):
    MONITORING = "monitoring"
    PAUSED = "paused"
    RISK_OBSERVED = "risk_observed"
    INVALID = "invalid"


class MonitoredAccount(Base, TimestampMixin):
    __tablename__ = "monitored_accounts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "biz", name="uq_monitored_accounts_owner_biz"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    biz: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fakeid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_tier: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    primary_fetch_mode: Mapped[CollectorAccountType] = mapped_column(
        value_enum(CollectorAccountType),
        default=CollectorAccountType.MP_ADMIN,
        nullable=False,
    )
    fallback_fetch_mode: Mapped[CollectorAccountType | None] = mapped_column(
        value_enum(CollectorAccountType),
        nullable=True,
    )
    status: Mapped[MonitoredAccountStatus] = mapped_column(
        value_enum(MonitoredAccountStatus),
        default=MonitoredAccountStatus.MONITORING,
        nullable=False,
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    update_history: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ai_relevance_history: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    manual_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategy_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    owner: Mapped["User"] = relationship("User")
    articles: Mapped[list["Article"]] = relationship("Article", back_populates="monitored_account")
