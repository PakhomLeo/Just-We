"""Task API routes for manual trigger operations."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.dependencies import DbSession, CurrentUser, OperatorUser
from app.services.monitoring_source_service import MonitoringSourceService
from app.tasks.fetch_task import run_single_account, run_all_accounts


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/fetch/all")
async def trigger_fetch_all(
    background_tasks: BackgroundTasks,
    current_user: OperatorUser,
):
    """
    Manually trigger fetch for all active monitored accounts.

    The fetch runs in the background.
    """
    # Schedule the task
    background_tasks.add_task(run_all_accounts)

    return {
        "message": "Fetch triggered for all active accounts",
        "status": "scheduled",
    }


@router.post("/fetch/{monitored_account_id}")
async def trigger_fetch(
    monitored_account_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: OperatorUser,
):
    """
    Manually trigger fetch for a single monitored account.

    The fetch runs in the background.
    """
    account = await MonitoringSourceService(db).get_visible(monitored_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Monitored account {monitored_account_id} not found")
    # Schedule the task
    background_tasks.add_task(run_single_account, monitored_account_id)

    return {
        "message": f"Fetch triggered for monitored account {monitored_account_id}",
        "status": "scheduled",
    }


@router.get("/fetch/{monitored_account_id}/status")
async def get_fetch_status(
    monitored_account_id: int,
    current_user: CurrentUser,
):
    """
    Get the scheduled fetch status for a monitored account.

    Note: This requires Redis to track job status properly.
    """
    from app.services.scheduler_service import SchedulerService
    from app.core.database import get_db_context

    async with get_db_context() as db:
        scheduler = SchedulerService(db)
        job_info = scheduler.get_job(monitored_account_id)

        if job_info is None:
            return {
                "monitored_account_id": monitored_account_id,
                "scheduled": False,
            }

        return {
            "monitored_account_id": monitored_account_id,
            "scheduled": True,
            "next_run": job_info.get("next_run"),
            "pending": job_info.get("pending"),
        }
