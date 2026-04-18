"""Scheduler service for managing APScheduler jobs."""

from datetime import datetime, time, timedelta, timezone
import random
from typing import Any, Callable
from zoneinfo import ZoneInfo

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

    Uses APScheduler to schedule dynamic fetch intervals based on monitored account tier.
    """

    def __init__(self, db: AsyncSession):
        """Initialize scheduler service."""
        self.db = db
        self.scheduler = get_scheduler()

    def get_next_run_at(self, interval_hours: int) -> datetime:
        """Compute the next run time in UTC."""
        return datetime.now(timezone.utc) + timedelta(hours=interval_hours)

    def _parse_time(self, value: str, fallback: time) -> time:
        try:
            hour, minute = [int(part) for part in value.split(":", 1)]
            return time(hour=hour, minute=minute)
        except Exception:
            return fallback

    def _is_quiet_time(self, local_dt: datetime, policy: dict[str, Any]) -> bool:
        start = self._parse_time(str(policy.get("quiet_start", "23:00")), time(hour=23))
        end = self._parse_time(str(policy.get("quiet_end", "06:00")), time(hour=6))
        current = local_dt.time()
        if start <= end:
            return start <= current < end
        return current >= start or current < end

    def _avoid_quiet_window(self, run_date: datetime, policy: dict[str, Any]) -> datetime:
        """Move automatic jobs out of the configured quiet window."""
        local_zone = ZoneInfo("Asia/Shanghai")
        local_date = run_date.astimezone(local_zone)
        if not self._is_quiet_time(local_date, policy):
            return run_date
        quiet_end = self._parse_time(str(policy.get("quiet_end", "06:00")), time(hour=6))
        next_date = local_date.date()
        if local_date.time() >= self._parse_time(str(policy.get("quiet_start", "23:00")), time(hour=23)):
            next_date = next_date + timedelta(days=1)
        adjusted_local = datetime.combine(next_date, quiet_end, tzinfo=local_zone) + timedelta(
            seconds=random.randint(30, 300)
        )
        return adjusted_local.astimezone(timezone.utc)

    def _planned_run_at(
        self,
        index: int,
        total_accounts: int,
        policy: dict[str, Any],
        fallback_interval_hours: int,
    ) -> datetime:
        daily_runs = max(1, int(policy.get("daily_runs", 2)))
        active_seconds_per_day = 17 * 60 * 60
        total_slots = max(1, total_accounts * daily_runs)
        base_spacing = max(10, active_seconds_per_day / total_slots)
        jitter_min = random.randint(10, 30)
        jitter_max = random.randint(300, 3000)
        jitter = min(jitter_max, max(jitter_min, int(base_spacing * 0.18)))
        delay_seconds = int(base_spacing * index) + random.randint(-jitter, jitter)
        if delay_seconds < 0:
            delay_seconds = max(10, int(fallback_interval_hours * 3600))
        return self._avoid_quiet_window(datetime.now(timezone.utc) + timedelta(seconds=delay_seconds), policy)

    def schedule_next_fetch(
        self,
        monitored_account_id: int,
        interval_hours: int,
        fetch_func: Callable,
        run_date: datetime | None = None,
    ) -> str:
        """
        Schedule the next fetch for a monitored account.

        Args:
            monitored_account_id: Monitored account ID
            interval_hours: Hours until next fetch
            fetch_func: Async function to call for fetching

        Returns:
            Job ID
        """
        job_id = f"fetch_{monitored_account_id}"
        run_date = run_date or self.get_next_run_at(interval_hours)

        # Remove existing job if any
        self.cancel_job(monitored_account_id)

        # Add new job
        self.scheduler.add_job(
            fetch_func,
            trigger=DateTrigger(run_date=run_date),
            args=[monitored_account_id],
            id=job_id,
            name=f"Fetch monitored account {monitored_account_id}",
            replace_existing=True,
        )

        return job_id

    def cancel_job(self, monitored_account_id: int) -> bool:
        """
        Cancel scheduled fetch for a monitored account.

        Args:
            monitored_account_id: Monitored account ID

        Returns:
            True if job was removed, False if no job existed
        """
        job_id = f"fetch_{monitored_account_id}"
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

    def get_job(self, monitored_account_id: int) -> dict[str, Any] | None:
        """
        Get scheduled job info for a monitored account.

        Args:
            monitored_account_id: Monitored account ID

        Returns:
            Dict with job info or None if not scheduled
        """
        job_id = f"fetch_{monitored_account_id}"
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
        monitored_accounts: list[MonitoredAccount],
        fetch_func: Callable,
    ) -> int:
        """
        Load and schedule all active monitored accounts.

        Args:
            monitored_accounts: List of monitored account models
            fetch_func: Async function to call for fetching

        Returns:
            Number of jobs scheduled
        """
        from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
        from app.services.system_config_service import SystemConfigService
        from app.services.weight_config_service import WeightConfigService

        config = await WeightConfigService(self.db).get_or_create()
        policy = await SystemConfigService(self.db).get_or_create_fetch_policy()
        daily_policy = policy.daily_account_fetch_policy
        adjuster = DynamicWeightAdjuster(**WeightConfigService.to_adjuster_kwargs(config))
        count = 0
        active_accounts = [
            item for item in monitored_accounts if item.status.value == "monitoring"
        ]

        for index, monitored_account in enumerate(active_accounts):
            interval = adjuster.get_next_check_interval(monitored_account)
            run_at = self._planned_run_at(index, len(active_accounts), daily_policy, interval)
            self.schedule_next_fetch(monitored_account.id, interval, fetch_func, run_date=run_at)
            monitored_account.next_scheduled_at = run_at
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
