"""Fetch job API routes."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.fetch_job import FetchJobResponse
from app.services.fetch_job_service import FetchJobService


router = APIRouter(prefix="/fetch-jobs", tags=["Fetch Jobs"])


@router.get("/", response_model=list[FetchJobResponse])
async def list_fetch_jobs(db: DbSession, current_user: CurrentUser):
    items = await FetchJobService(db).list_recent()
    return [FetchJobResponse.model_validate(item) for item in items]
