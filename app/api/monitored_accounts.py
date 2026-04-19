"""Monitored account API routes."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.monitored_account import (
    MonitoredAccountCreate,
    MonitoredAccountListResponse,
    MonitoredAccountResponse,
    MonitoredAccountUpdate,
)
from app.services.monitoring_source_service import MonitoringSourceService
from app.services.fetch_job_service import FetchJobService
from app.models.fetch_job import FetchJobType
from app.tasks.fetch_task import run_single_account, run_history_backfill


router = APIRouter(prefix="/monitored-accounts", tags=["Monitored Accounts"])


@router.get("/", response_model=MonitoredAccountListResponse)
async def list_monitored_accounts(db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    items = await service.list_visible(current_user, include_all=True)
    return MonitoredAccountListResponse(total=len(items), items=[MonitoredAccountResponse.model_validate(item) for item in items])


@router.post("/", response_model=MonitoredAccountResponse)
async def create_monitored_account(request: MonitoredAccountCreate, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    monitored, _ = await service.create_from_url(
        owner_user_id=current_user.id,
        source_url=request.source_url,
        name=request.name,
        fakeid=request.fakeid,
    )
    return MonitoredAccountResponse.model_validate(monitored)


@router.get("/{monitored_account_id}", response_model=MonitoredAccountResponse)
async def get_monitored_account(monitored_account_id: int, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    return MonitoredAccountResponse.model_validate(account)


@router.put("/{monitored_account_id}", response_model=MonitoredAccountResponse)
async def update_monitored_account(monitored_account_id: int, request: MonitoredAccountUpdate, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    payload = {k: v for k, v in request.model_dump().items() if v is not None}
    updated = await service.update(account, **payload)
    return MonitoredAccountResponse.model_validate(updated)


@router.delete("/{monitored_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitored_account(monitored_account_id: int, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    await service.delete(account)


@router.post("/{monitored_account_id}/fetch")
async def trigger_monitored_fetch(monitored_account_id: int, background_tasks: BackgroundTasks, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    background_tasks.add_task(run_single_account, monitored_account_id)
    return {"status": "scheduled", "monitored_account_id": monitored_account_id}


@router.post("/{monitored_account_id}/history-backfill")
async def trigger_history_backfill(monitored_account_id: int, background_tasks: BackgroundTasks, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    job_service = FetchJobService(db)
    existing = await job_service.get_running_history_backfill(monitored_account_id)
    if existing is not None:
        return {"status": "already_running", "job_id": existing.id, "monitored_account_id": monitored_account_id}
    job = await job_service.create_job(monitored_account_id, FetchJobType.HISTORY_BACKFILL)
    background_tasks.add_task(run_history_backfill, monitored_account_id, job.id)
    return {"status": "scheduled", "job_id": job.id, "monitored_account_id": monitored_account_id}


@router.get("/{monitored_account_id}/history-backfill/status")
async def get_history_backfill_status(monitored_account_id: int, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    job = await FetchJobService(db).get_latest_history_backfill(monitored_account_id)
    if job is None:
        return {"status": "idle", "monitored_account_id": monitored_account_id}
    return {
        "status": job.status.value,
        "job_id": job.id,
        "monitored_account_id": monitored_account_id,
        "error": job.error,
        "payload": job.payload or {},
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.post("/{monitored_account_id}/history-backfill/stop")
async def stop_history_backfill(monitored_account_id: int, db: DbSession, current_user: CurrentUser):
    service = MonitoringSourceService(db)
    account = await service.get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitored account not found")
    job = await FetchJobService(db).request_stop_history_backfill(monitored_account_id)
    if job is None:
        return {"status": "idle", "monitored_account_id": monitored_account_id}
    return {"status": "stopped", "job_id": job.id, "monitored_account_id": monitored_account_id, "payload": job.payload or {}}
