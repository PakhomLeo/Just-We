"""Fetch job model for collection pipeline execution."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.collector_account import CollectorAccountType
from app.models.enum_utils import value_enum

if TYPE_CHECKING:
    from app.models.collector_account import CollectorAccount
    from app.models.monitored_account import MonitoredAccount


class FetchJobType(str, enum.Enum):
    UPDATE_LIST = "update_list"
    ARTICLE_DETAIL = "article_detail"
    FULL_SYNC = "full_sync"
    HISTORY_BACKFILL = "history_backfill"


class FetchJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class FetchJob(Base, TimestampMixin):
    __tablename__ = "fetch_jobs"

    job_type: Mapped[FetchJobType] = mapped_column(value_enum(FetchJobType), nullable=False)
    status: Mapped[FetchJobStatus] = mapped_column(
        value_enum(FetchJobStatus),
        default=FetchJobStatus.PENDING,
        nullable=False,
    )
    monitored_account_id: Mapped[int] = mapped_column(
        ForeignKey("monitored_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collector_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("collector_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True)
    fetch_mode: Mapped[CollectorAccountType | None] = mapped_column(value_enum(CollectorAccountType), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    monitored_account: Mapped["MonitoredAccount"] = relationship("MonitoredAccount")
    collector_account: Mapped["CollectorAccount"] = relationship("CollectorAccount")
