"""Article repository for database operations."""

from datetime import datetime, timedelta, timezone

import uuid

from sqlalchemy import Select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository):
    """Repository for Article model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)

    async def get_by_monitored_account(
        self,
        monitored_account_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Article]:
        """Get articles by monitored account ID."""
        result = await self.db.execute(
            Select(Article)
            .options(selectinload(Article.monitored_account))
            .where(Article.monitored_account_id == monitored_account_id)
            .order_by(desc(Article.published_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_for_feed(
        self,
        monitored_account_ids: list[int],
        skip: int = 0,
        limit: int = 50,
        title_include: str | None = None,
        title_exclude: str | None = None,
    ) -> list[Article]:
        """Get articles for feed generation."""
        if not monitored_account_ids:
            return []
        query = (
            Select(Article)
            .options(selectinload(Article.monitored_account))
            .where(Article.monitored_account_id.in_(monitored_account_ids))
        )
        if title_include:
            query = query.where(Article.title.ilike(f"%{title_include}%"))
        if title_exclude:
            query = query.where(~Article.title.ilike(f"%{title_exclude}%"))
        result = await self.db.execute(query.order_by(desc(Article.published_at)).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_recent_articles(
        self,
        monitored_account_id: int,
        hours: int = 24,
    ) -> list[Article]:
        """Get recent articles for a monitored account within specified hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            Select(Article)
            .options(selectinload(Article.monitored_account))
            .where(
                and_(
                    Article.monitored_account_id == monitored_account_id,
                    Article.published_at >= cutoff,
                )
            )
            .order_by(desc(Article.published_at))
        )
        return list(result.scalars().all())

    async def get_by_url(self, url: str) -> Article | None:
        """Get article by URL."""
        result = await self.db.execute(
            Select(Article).where(Article.url == url)
        )
        return result.scalar_one_or_none()

    async def get_visible_by_id(
        self,
        article_id: int,
        owner_user_id: uuid.UUID | None = None,
    ) -> Article | None:
        query = Select(Article).options(selectinload(Article.monitored_account))
        query = query.where(Article.id == article_id)
        if owner_user_id is not None:
            query = query.where(Article.monitored_account.has(owner_user_id=owner_user_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_count_by_monitored_account(self, monitored_account_id: int) -> int:
        """Get total article count for a monitored account."""
        result = await self.db.execute(
            Select(func.count())
            .select_from(Article)
            .where(Article.monitored_account_id == monitored_account_id)
        )
        return result.scalar_one()

    async def get_articles_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        monitored_account_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        owner_user_id: uuid.UUID | None = None,
    ) -> tuple[list[Article], int]:
        """Get paginated articles with filters."""
        query = Select(Article)

        conditions = []
        if monitored_account_id:
            conditions.append(Article.monitored_account_id == monitored_account_id)
        if start_date:
            conditions.append(Article.published_at >= start_date)
        if end_date:
            conditions.append(Article.published_at <= end_date)
        if owner_user_id is not None:
            conditions.append(Article.monitored_account.has(owner_user_id=owner_user_id))

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = Select(func.count()).select_from(Article)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            query.options(selectinload(Article.monitored_account))
            .order_by(desc(Article.published_at))
            .offset(skip)
            .limit(limit)
        )
        articles = list(result.scalars().all())

        return articles, total
