"""Scheduler service for managing APScheduler jobs."""

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitored_account import MonitoredAccount


# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None


class SchedulerService:
    """
    Service for managing scheduled fetch jobs.

    Uses APScheduler to schedule dynamic fetch intervals based on account tier.
    """

    def __init__(self, db: AsyncSession):
        """Initialize scheduler service."""
        self.db = db
        self.scheduler = get_scheduler()

    def get_next_run_at(self, interval_hours: int) -> datetime:
        """Compute the next run time in UTC."""
        return datetime.now(timezone.utc) + timedelta(hours=interval_hours)

    def schedule_next_fetch(
        self,
        account_id: int,
        interval_hours: int,
        fetch_func: Callable,
    ) -> str:
        """
        Schedule the next fetch for an account.

        Args:
            account_id: Account ID
            interval_hours: Hours until next fetch
            fetch_func: Async function to call for fetching

        Returns:
            Job ID
        """
        job_id = f"fetch_{account_id}"
        run_date = self.get_next_run_at(interval_hours)

        # Remove existing job if any
        self.cancel_job(account_id)

        # Add new job
        self.scheduler.add_job(
            fetch_func,
            trigger=DateTrigger(run_date=run_date),
            args=[account_id],
            id=job_id,
            name=f"Fetch account {account_id}",
            replace_existing=True,
        )

        return job_id

    def cancel_job(self, account_id: int) -> bool:
        """
        Cancel scheduled fetch for an account.

        Args:
            account_id: Account ID

        Returns:
            True if job was removed, False if no job existed
        """
        job_id = f"fetch_{account_id}"
        try:
            self.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    def schedule_interval_job(
        self,
        job_id: str,
        interval_hours: int,
        func: Callable,
        args: list[Any] | None = None,
        name: str | None = None,
    ) -> str:
        """Schedule or replace a recurring interval job."""
        self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(hours=interval_hours, timezone="UTC"),
            args=args or [],
            id=job_id,
            name=name or job_id,
            replace_existing=True,
        )
        return job_id

    def get_job(self, account_id: int) -> dict[str, Any] | None:
        """
        Get scheduled job info for an account.

        Args:
            account_id: Account ID

        Returns:
            Dict with job info or None if not scheduled
        """
        job_id = f"fetch_{account_id}"
        job = self.scheduler.get_job(job_id)

        if job is None:
            return None

        next_run_time = getattr(job, "next_run_time", None)
        pending = getattr(job, "pending", False)

        return {
            "job_id": job.id,
            "name": job.name,
            "next_run": next_run_time.isoformat() if next_run_time else None,
            "pending": pending,
        }

    def get_all_jobs(self) -> list[dict[str, Any]]:
        """
        Get all scheduled jobs.

        Returns:
            List of job info dicts
        """
        jobs = self.scheduler.get_jobs()
        items = []
        for job in jobs:
            next_run_time = getattr(job, "next_run_time", None)
            items.append(
                {
                    "job_id": job.id,
                    "name": job.name,
                    "next_run": next_run_time.isoformat() if next_run_time else None,
                    "pending": getattr(job, "pending", False),
                }
            )
        return items

    async def load_account_schedules(
        self,
        accounts: list[MonitoredAccount],
        fetch_func: Callable,
    ) -> int:
        """
        Load and schedule all active accounts.

        Args:
            accounts: List of Account models
            fetch_func: Async function to call for fetching

        Returns:
            Number of jobs scheduled
        """
        from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster

        adjuster = DynamicWeightAdjuster()
        count = 0

        for account in accounts:
            if account.status.value == "monitoring":
                interval = adjuster.get_next_check_interval(account)
                self.schedule_next_fetch(account.id, interval, fetch_func)
                account.next_scheduled_at = self.get_next_run_at(interval)
                count += 1

        await self.db.flush()
        return count

    def pause_all(self) -> int:
        """
        Pause all jobs.

        Returns:
            Number of jobs paused
        """
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            job.pause()
        return len(jobs)

    def resume_all(self) -> int:
        """
        Resume all paused jobs.

        Returns:
            Number of jobs resumed
        """
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            job.resume()
        return len(jobs)
