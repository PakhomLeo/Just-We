"""Article service for article management."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.repositories.article_repo import ArticleRepository


class ArticleService:
    """Service for article management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.article_repo = ArticleRepository(db)

    async def get_article(self, article_id: int) -> Article | None:
        """Get article by ID."""
        return await self.article_repo.get_by_id(article_id)

    async def get_visible_article(self, article_id: int, current_user) -> Article | None:
        owner_user_id = None if current_user.role.value == "admin" else current_user.id
        return await self.article_repo.get_visible_by_id(article_id, owner_user_id=owner_user_id)

    async def get_articles_by_account(
        self,
        account_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Article]:
        """Get articles by account ID."""
        return await self.article_repo.get_by_account(account_id, skip, limit)

    async def get_recent_articles(
        self,
        account_id: int,
        hours: int = 24,
    ) -> list[Article]:
        """Get recent articles for an account."""
        return await self.article_repo.get_recent_articles(account_id, hours)

    async def get_article_by_url(self, url: str) -> Article | None:
        """Get article by URL."""
        return await self.article_repo.get_by_url(url)

    async def save_article(
        self,
        account_id: int | None,
        title: str,
        content: str,
        url: str,
        raw_content: str | None = None,
        images: list[str] | None = None,
        monitored_account_id: int | None = None,
        cover_image: str | None = None,
        author: str | None = None,
        published_at: datetime | None = None,
        ai_relevance_ratio: float | None = None,
        ai_judgment: dict[str, Any] | None = None,
        fetch_mode: str | None = None,
        content_fingerprint: str | None = None,
        source_payload: dict[str, Any] | None = None,
    ) -> Article:
        """Save a new article."""
        # Check if article already exists
        existing = await self.article_repo.get_by_url(url)
        if existing:
            # Update existing article
            return await self.article_repo.update(
                existing,
                account_id=account_id,
                monitored_account_id=monitored_account_id,
                title=title,
                content=content,
                raw_content=raw_content,
                images=images or [],
                cover_image=cover_image,
                author=author,
                published_at=published_at,
                ai_relevance_ratio=ai_relevance_ratio,
                ai_judgment=ai_judgment,
                fetch_mode=fetch_mode,
                content_fingerprint=content_fingerprint,
                source_payload=source_payload,
            )

        # Create new article
        return await self.article_repo.create(
            account_id=account_id,
            monitored_account_id=monitored_account_id,
            title=title,
            content=content,
            raw_content=raw_content,
            images=images or [],
            cover_image=cover_image,
            url=url,
            author=author,
            published_at=published_at,
            ai_relevance_ratio=ai_relevance_ratio,
            ai_judgment=ai_judgment,
            fetch_mode=fetch_mode,
            content_fingerprint=content_fingerprint,
            source_payload=source_payload,
        )

    async def get_articles_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        account_id: int | None = None,
        monitored_account_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        current_user=None,
    ) -> tuple[list[Article], int]:
        """Get paginated articles with filters."""
        skip = (page - 1) * page_size
        owner_user_id = None if current_user is None or current_user.role.value == "admin" else current_user.id
        return await self.article_repo.get_articles_paginated(
            skip=skip,
            limit=page_size,
            account_id=account_id,
            monitored_account_id=monitored_account_id,
            start_date=start_date,
            end_date=end_date,
            owner_user_id=owner_user_id,
        )

    async def update_ai_analysis(
        self,
        article_id: int,
        ai_relevance_ratio: float,
        ai_judgment: dict[str, Any],
    ) -> Article | None:
        """Update article with AI analysis results."""
        article = await self.article_repo.get_by_id(article_id)
        if article is None:
            return None
        return await self.article_repo.update(
            article,
            ai_relevance_ratio=ai_relevance_ratio,
            ai_judgment=ai_judgment,
        )

    async def get_article_count(self, account_id: int) -> int:
        """Get total article count for an account."""
        return await self.article_repo.get_count_by_account(account_id)
