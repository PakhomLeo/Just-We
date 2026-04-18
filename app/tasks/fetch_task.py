"""Fetch task for the monitored account pipeline."""

from app.core.database import get_db_context
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.fetch_pipeline_service import FetchPipelineService


async def run_single_account(monitored_account_id: int) -> dict:
    """Run full pipeline for a monitored account."""
    async with get_db_context() as db:
        return await FetchPipelineService(db).run_monitored_account(monitored_account_id)


async def run_history_backfill(monitored_account_id: int, job_id: int | None = None) -> dict:
    """Run history backfill for a monitored account."""
    async with get_db_context() as db:
        return await FetchPipelineService(db).run_history_backfill(monitored_account_id, job_id)


async def run_all_accounts() -> dict:
    """Run fetch pipeline for all active monitored accounts."""
    async with get_db_context() as db:
        monitored_accounts = await MonitoredAccountRepository(db).get_active_accounts()
        results = []
        for monitored_account in monitored_accounts:
            results.append(await run_single_account(monitored_account.id))

        successful = sum(1 for item in results if item.get("success"))
        return {
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }
