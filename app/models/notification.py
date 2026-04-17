"""Notification model for alerts and updates."""

import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """Notification model for alerts and updates."""

    __tablename__ = "notifications"

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="通知所属平台用户",
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联账号 ID",
    )
    collector_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("collector_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联抓取账号 ID",
    )
    monitored_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitored_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联监测对象 ID",
    )
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联文章 ID",
    )
    notification_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="通知类型",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="通知标题",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="通知内容",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已读",
    )
    payload: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="扩展通知载荷",
    )

    owner: Mapped["User | None"] = relationship("User")
    collector_account: Mapped["CollectorAccount | None"] = relationship("CollectorAccount")
    monitored_account: Mapped["MonitoredAccount | None"] = relationship("MonitoredAccount")
    article: Mapped["Article | None"] = relationship("Article")

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type}: {self.title}>"
