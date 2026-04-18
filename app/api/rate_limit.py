"""Rate-limit observability endpoints."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.services.rate_limit_service import rate_limit_service
from app.services.system_config_service import SystemConfigService


router = APIRouter(prefix="/rate-limit", tags=["Rate Limit"])


@router.get("/stats")
async def get_rate_limit_stats(db: DbSession, current_user: CurrentUser):
    policy = await SystemConfigService(db).get_rate_limit_policy()
    rate_limit_service.configure(policy)
    return rate_limit_service.stats()
