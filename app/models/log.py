"""Operation log model for audit trail."""

import uuid

from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OperationLog(Base, TimestampMixin):
    """Operation log model for audit trail."""

    __tablename__ = "operation_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="操作用户 ID",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="操作类型",
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="目标类型：account, article, proxy",
    )
    target_id: Mapped[int] = mapped_column(
        nullable=False,
        comment="目标 ID",
    )
    before_state: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="变更前状态",
    )
    after_state: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="变更后状态",
    )
    detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="额外描述",
    )

    def __repr__(self) -> str:
        return f"<OperationLog {self.action} on {self.target_type}:{self.target_id}>"
