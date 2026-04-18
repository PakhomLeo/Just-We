"""Article model for WeChat public account articles."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.monitored_account import MonitoredAccount


class Article(Base, TimestampMixin):
    """Article model for WeChat public account articles."""

    __tablename__ = "articles"

    monitored_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitored_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联监测公众号 ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="文章标题",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="清洗后全文",
    )
    content_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="清洗后的富文本 HTML",
    )
    content_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="内容类型",
    )
    raw_content: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="原始 HTML",
    )
    images: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="本地化图片路径列表",
    )
    original_images: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="原始微信图片 URL 列表",
    )
    cover_image: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="封面图",
    )
    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="文章链接",
    )
    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="作者",
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="发布时间",
    )
    ai_relevance_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="AI 判定相关度 0-1",
    )
    ai_judgment: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI 判定结果 {ratio, reason, keywords: []}",
    )
    ai_text_analysis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI 文字全文解析 JSON",
    )
    ai_image_analysis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI 图片内容解析 JSON",
    )
    ai_type_judgment: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI 类型判断 JSON",
    )
    ai_combined_analysis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI 文字和图片拼接后的结构化结果",
    )
    ai_target_match: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
        comment="目标类型判断：是/不是",
    )
    ai_analysis_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="AI 分析状态：pending/success/failed/skipped",
    )
    ai_analysis_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI 分析错误信息",
    )
    fetch_mode: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="抓取通道",
    )
    content_fingerprint: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="内容指纹",
    )
    source_payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="原始抓取元数据",
    )

    monitored_account: Mapped["MonitoredAccount"] = relationship(
        "MonitoredAccount",
        back_populates="articles",
    )

    def __repr__(self) -> str:
        return f"<Article {self.title[:50]}...>"
