"""Repository for fetch jobs."""

from sqlalchemy import Select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fetch_job import FetchJob, FetchJobStatus, FetchJobType
from app.repositories.base import BaseRepository


class FetchJobRepository(BaseRepository):
    """CRUD helpers for fetch jobs."""

    def __init__(self, db: AsyncSession):
        super().__init__(FetchJob, db)

    async def get_recent(self, limit: int = 50) -> list[FetchJob]:
        result = await self.db.execute(Select(FetchJob).order_by(FetchJob.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def get_running_for_monitored_account(
        self,
        monitored_account_id: int,
        job_type: FetchJobType,
    ) -> FetchJob | None:
        result = await self.db.execute(
            Select(FetchJob)
            .where(
                and_(
                    FetchJob.monitored_account_id == monitored_account_id,
                    FetchJob.job_type == job_type,
                    FetchJob.status.in_([FetchJobStatus.PENDING, FetchJobStatus.RUNNING]),
                )
            )
            .order_by(FetchJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_monitored_account(
        self,
        monitored_account_id: int,
        job_type: FetchJobType,
    ) -> FetchJob | None:
        result = await self.db.execute(
            Select(FetchJob)
            .where(
                and_(
                    FetchJob.monitored_account_id == monitored_account_id,
                    FetchJob.job_type == job_type,
                )
            )
            .order_by(FetchJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
