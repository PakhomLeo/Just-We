"""Generate full JSON exports for fetched articles."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.article import Article
from app.models.article_export import ArticleExportRecord, ArticleExportStatus
from app.models.monitored_account import MonitoredAccount
from app.schemas.article_export import ArticleExportCreate


class ArticleExportService:
    """Create and list article JSON export records."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def list_records(self, current_user, limit: int = 20) -> tuple[list[ArticleExportRecord], int]:
        conditions = [ArticleExportRecord.owner_user_id == current_user.id]
        count_result = await self.db.execute(
            Select(func.count()).select_from(ArticleExportRecord).where(and_(*conditions))
        )
        result = await self.db.execute(
            Select(ArticleExportRecord)
            .where(and_(*conditions))
            .order_by(desc(ArticleExportRecord.created_at))
            .limit(limit)
        )
        return list(result.scalars().all()), count_result.scalar_one()

    async def get_record(self, record_id: int, current_user) -> ArticleExportRecord | None:
        result = await self.db.execute(
            Select(ArticleExportRecord).where(
                ArticleExportRecord.id == record_id,
                ArticleExportRecord.owner_user_id == current_user.id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_record(self, record: ArticleExportRecord) -> None:
        """Delete an export history record and its generated file if present."""
        path = Path(self.settings.media_root) / record.file_path
        if path.exists() and path.is_file():
            path.unlink()
        await self.db.delete(record)
        await self.db.flush()

    async def create_export(self, payload: ArticleExportCreate, current_user) -> ArticleExportRecord:
        articles = await self._select_articles(payload, current_user)
        export_payload = self._build_payload(payload, articles)
        export_dir = Path(self.settings.media_root) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"just-we-articles-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
        file_path = export_dir / filename
        file_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2, default=self._json_default), encoding="utf-8")

        record = ArticleExportRecord(
            owner_user_id=current_user.id,
            scope=payload.scope,
            target_match=payload.target_match,
            include_exported=payload.include_exported,
            filters=self._filters_payload(payload),
            article_count=len(articles),
            exported_article_ids=[article.id for article in articles],
            file_name=filename,
            file_path=str(Path("exports") / filename),
            status=ArticleExportStatus.COMPLETED,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def _select_articles(self, payload: ArticleExportCreate, current_user) -> list[Article]:
        conditions = []
        if current_user.role.value != "admin":
            conditions.append(Article.monitored_account.has(owner_user_id=current_user.id))
        if payload.scope == "account":
            conditions.append(Article.monitored_account_id == payload.monitored_account_id)
        if payload.scope == "time":
            if payload.start_date:
                conditions.append(Article.published_at >= payload.start_date)
            if payload.end_date:
                conditions.append(Article.published_at <= payload.end_date)
        if payload.target_match == "matched":
            conditions.append(Article.ai_target_match == "是")
        elif payload.target_match == "unmatched":
            conditions.append(Article.ai_target_match == "不是")
        elif payload.target_match == "unknown":
            conditions.append(Article.ai_target_match.is_(None))

        if not payload.include_exported:
            exported_ids = await self._previous_exported_article_ids(current_user)
            if exported_ids:
                conditions.append(~Article.id.in_(exported_ids))

        query = Select(Article).options(selectinload(Article.monitored_account))
        if conditions:
            query = query.where(and_(*conditions))
        result = await self.db.execute(query.order_by(desc(Article.published_at), desc(Article.created_at)))
        return list(result.scalars().all())

    async def _previous_exported_article_ids(self, current_user) -> set[int]:
        result = await self.db.execute(
            Select(ArticleExportRecord.exported_article_ids).where(
                ArticleExportRecord.owner_user_id == current_user.id,
                ArticleExportRecord.status == ArticleExportStatus.COMPLETED,
            )
        )
        ids: set[int] = set()
        for item in result.scalars().all():
            ids.update(int(value) for value in (item or []) if value is not None)
        return ids

    def _build_payload(self, payload: ArticleExportCreate, articles: list[Article]) -> dict[str, Any]:
        return {
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": "just-we.article-export.v1",
                "filters": self._filters_payload(payload),
                "article_count": len(articles),
            },
            "articles": [self._article_payload(article) for article in articles],
        }

    def _article_payload(self, article: Article) -> dict[str, Any]:
        account: MonitoredAccount | None = article.monitored_account
        return {
            "id": article.id,
            "monitored_account_id": article.monitored_account_id,
            "account": None
            if account is None
            else {
                "id": account.id,
                "name": account.name,
                "biz": account.biz,
                "fakeid": account.fakeid,
                "source_url": account.source_url,
                "avatar_url": account.avatar_url,
                "intro": account.mp_intro,
                "tier": account.current_tier,
                "fetch_mode": getattr(account.primary_fetch_mode, "value", account.primary_fetch_mode),
                "status": getattr(account.status, "value", account.status),
            },
            "title": article.title,
            "url": article.url,
            "author": article.author,
            "published_at": article.published_at,
            "content": article.content,
            "content_html": article.content_html,
            "content_type": article.content_type,
            "raw_content": article.raw_content,
            "cover_image": article.cover_image,
            "images": article.images or [],
            "original_images": article.original_images or [],
            "ai": {
                "relevance_ratio": article.ai_relevance_ratio,
                "judgment": article.ai_judgment,
                "text_analysis": article.ai_text_analysis,
                "image_analysis": article.ai_image_analysis,
                "type_judgment": article.ai_type_judgment,
                "combined_analysis": article.ai_combined_analysis,
                "target_match": article.ai_target_match,
                "status": article.ai_analysis_status,
                "error": article.ai_analysis_error,
            },
            "fetch_mode": article.fetch_mode,
            "source_payload": article.source_payload,
            "content_fingerprint": article.content_fingerprint,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        }

    def _filters_payload(self, payload: ArticleExportCreate) -> dict[str, Any]:
        return {
            "scope": payload.scope,
            "monitored_account_id": payload.monitored_account_id,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "target_match": payload.target_match,
            "include_exported": payload.include_exported,
        }

    @staticmethod
    def _json_default(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
