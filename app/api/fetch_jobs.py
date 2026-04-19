"""Fetch job API routes."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.fetch_job import FetchJobResponse
from app.services.fetch_job_service import FetchJobService


router = APIRouter(prefix="/fetch-jobs", tags=["Fetch Jobs"])


@router.get("/", response_model=list[FetchJobResponse])
async def list_fetch_jobs(db: DbSession, current_user: CurrentUser):
    items = await FetchJobService(db).list_recent()
    return [FetchJobResponse.model_validate(item) for item in items]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fetch_job(job_id: int, db: DbSession, current_user: CurrentUser):
    service = FetchJobService(db)
    job = await service.get_visible(job_id, current_user)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fetch job not found")
    await service.delete_job(job)
