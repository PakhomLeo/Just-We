"""Service for fetch job lifecycle."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fetch_job import FetchJob, FetchJobStatus, FetchJobType
from app.repositories.fetch_job_repo import FetchJobRepository


class FetchJobService:
    """Manage fetch job records."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FetchJobRepository(db)

    async def create_job(self, monitored_account_id: int, job_type: FetchJobType) -> FetchJob:
        return await self.repo.create(
            monitored_account_id=monitored_account_id,
            job_type=job_type,
            status=FetchJobStatus.PENDING,
            payload={},
        )

    async def mark_running(self, job: FetchJob, **kwargs) -> FetchJob:
        return await self.repo.update(job, status=FetchJobStatus.RUNNING, started_at=datetime.now(timezone.utc), **kwargs)

    async def mark_success(self, job: FetchJob, **kwargs) -> FetchJob:
        return await self.repo.update(job, status=FetchJobStatus.SUCCESS, finished_at=datetime.now(timezone.utc), **kwargs)

    async def mark_failed(self, job: FetchJob, error: str, **kwargs) -> FetchJob:
        payload = kwargs.pop("payload", None)
        merged_payload = dict(job.payload or {})
        if payload:
            merged_payload.update(payload)
        return await self.repo.update(
            job,
            status=FetchJobStatus.FAILED,
            error=error,
            finished_at=datetime.now(timezone.utc),
            payload=merged_payload,
            **kwargs,
        )

    async def list_recent(self, limit: int = 50) -> list[FetchJob]:
        return await self.repo.get_recent(limit=limit)
