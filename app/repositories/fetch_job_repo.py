"""Repository for fetch jobs."""

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fetch_job import FetchJob
from app.repositories.base import BaseRepository


class FetchJobRepository(BaseRepository):
    """CRUD helpers for fetch jobs."""

    def __init__(self, db: AsyncSession):
        super().__init__(FetchJob, db)

    async def get_recent(self, limit: int = 50) -> list[FetchJob]:
        result = await self.db.execute(Select(FetchJob).order_by(FetchJob.created_at.desc()).limit(limit))
        return list(result.scalars().all())
