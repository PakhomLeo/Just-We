"""API routes package."""

from app.api.auth import router as auth_router
from app.api.accounts import router as accounts_router
from app.api.qr import router as qr_router
from app.api.articles import router as articles_router
from app.api.proxies import router as proxies_router
from app.api.weight import router as weight_router
from app.api.tasks import router as tasks_router
from app.api.logs import router as logs_router
from app.api.notifications import router as notifications_router
from app.api.users import router as users_router

__all__ = [
    "auth_router",
    "accounts_router",
    "qr_router",
    "articles_router",
    "proxies_router",
    "weight_router",
    "tasks_router",
    "logs_router",
    "notifications_router",
    "users_router",
]
