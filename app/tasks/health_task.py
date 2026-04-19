"""Periodic collector-account health-check task."""

from app.core.database import get_db_context
from app.repositories.collector_account_repo import CollectorAccountRepository
from app.services.collector_account_service import CollectorAccountService
from app.services.health_service import health_check_service
from app.services.notification_service import NotificationService


async def run_all_collector_health_checks() -> dict:
    """Run health checks for all collector accounts."""
    async with get_db_context() as db:
        repo = CollectorAccountRepository(db)
        collector_service = CollectorAccountService(db)
        notification_service = NotificationService(db)

        accounts = await repo.get_visible_accounts(None)
        results = []
        for account in accounts:
            health_status, reason, expires_at = await health_check_service.check_collector_account_health(account, db)
            updated = await collector_service.mark_health(account, health_status, reason)
            if expires_at and reason == "凭证即将过期":
                await notification_service.notify_collector_expiring_soon(updated, expires_at)
            elif health_status.value != "normal":
                await notification_service.notify_collector_health_issue(updated, health_status, reason)
            results.append(
                {
                    "collector_account_id": account.id,
                    "health_status": health_status.value,
                    "reason": reason,
                }
            )

        success_count = sum(1 for item in results if item["health_status"] == "normal")
        return {
            "total": len(results),
            "healthy": success_count,
            "unhealthy": len(results) - success_count,
            "results": results,
        }
