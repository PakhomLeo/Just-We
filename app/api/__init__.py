"""API routes package."""

from app.api.auth import router as auth_router
from app.api.articles import router as articles_router
from app.api.article_exports import router as article_exports_router
from app.api.proxies import router as proxies_router
from app.api.weight import router as weight_router
from app.api.tasks import router as tasks_router
from app.api.logs import router as logs_router
from app.api.notifications import router as notifications_router
from app.api.users import router as users_router
from app.api.collector_accounts import router as collector_accounts_router
from app.api.monitored_accounts import router as monitored_accounts_router
from app.api.fetch_jobs import router as fetch_jobs_router
from app.api.system_config import router as system_config_router
from app.api.feeds import router as feeds_router
from app.api.image import router as image_router
from app.api.rate_limit import router as rate_limit_router
from app.api.public_feeds import router as public_feeds_router

__all__ = [
    "auth_router",
    "articles_router",
    "article_exports_router",
    "proxies_router",
    "weight_router",
    "tasks_router",
    "logs_router",
    "notifications_router",
    "users_router",
    "collector_accounts_router",
    "monitored_accounts_router",
    "fetch_jobs_router",
    "system_config_router",
    "feeds_router",
    "image_router",
    "rate_limit_router",
    "public_feeds_router",
]
