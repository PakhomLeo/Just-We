"""Article JSON export records."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enum_utils import value_enum

if TYPE_CHECKING:
    from app.models.user import User


class ArticleExportStatus(str, enum.Enum):
    """Article export lifecycle state."""

    COMPLETED = "completed"
    FAILED = "failed"


class ArticleExportRecord(Base, TimestampMixin):
    """A generated article JSON export file and its selection criteria."""

    __tablename__ = "article_export_records"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    target_match: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    include_exported: Mapped[bool] = mapped_column(default=False, nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exported_article_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ArticleExportStatus] = mapped_column(
        value_enum(ArticleExportStatus),
        default=ArticleExportStatus.COMPLETED,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship("User")
