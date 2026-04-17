"""Schemas for fetch jobs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.collector_account import CollectorAccountType
from app.models.fetch_job import FetchJobStatus, FetchJobType


class FetchJobResponse(BaseModel):
    id: int
    job_type: FetchJobType
    status: FetchJobStatus
    monitored_account_id: int
    collector_account_id: int | None
    proxy_id: int | None
    fetch_mode: CollectorAccountType | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
