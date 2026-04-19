"""
Just-We - Main Application Entry Point

微信公众号智能权重监控系统
"""

import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    article_exports_router,
    articles_router,
    auth_router,
    collector_accounts_router,
    feeds_router,
    fetch_jobs_router,
    image_router,
    logs_router,
    monitored_accounts_router,
    notifications_router,
    proxies_router,
    public_feeds_router,
    rate_limit_router,
    system_config_router,
    tasks_router,
    users_router,
    weight_router,
)
from app.core.config import get_settings
from app.core.database import close_db, get_db_context, init_db
from app.core.exceptions import AppException
from app.core.redis import close_redis
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.bootstrap_service import BootstrapService
from app.services.scheduler_service import SchedulerService, start_scheduler, stop_scheduler
from app.tasks.fetch_task import run_single_account
from app.tasks.health_task import run_all_collector_health_checks

# Suppress known deprecation warnings from third-party libraries
# passlib warnings about bcrypt
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
# python-multipart warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="python_multipart")


settings = get_settings()

SPA_EXCLUDED_PREFIXES = (
    "api",
    "docs",
    "redoc",
    "openapi.json",
    settings.media_url_prefix.strip("/"),
)


def _json_safe(value):
    """Convert validation payloads to JSON-safe primitives."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _build_validation_message(errors: list[dict]) -> str:
    """Build a concise validation summary for the frontend."""
    if not errors:
        return "请求参数不合法"
    first_error = errors[0]
    location = ".".join(str(part) for part in first_error.get("loc", []) if part not in {"body", "query", "path"})
    message = first_error.get("msg", "请求参数不合法")
    if location:
        return f"{location}: {message}"
    return message


def _frontend_dist() -> Path:
    """Return the configured frontend build directory."""
    return Path(settings.frontend_dist_path)


def _should_serve_spa(full_path: str) -> bool:
    """Return whether a request path should fall back to the Vue app."""
    first_segment = full_path.strip("/").split("/", 1)[0]
    return first_segment not in SPA_EXCLUDED_PREFIXES


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await init_db()
    Path(settings.media_root).mkdir(parents=True, exist_ok=True)
    start_scheduler()
    async with get_db_context() as db:
        await BootstrapService(db).ensure_default_admin()
        accounts = await MonitoredAccountRepository(db).get_active_accounts()
        scheduler_service = SchedulerService(db)
        await scheduler_service.load_account_schedules(accounts, run_single_account)
        scheduler_service.schedule_daily_job(
            job_id="collector_health_checks",
            hour=settings.collector_health_check_hour,
            minute=settings.collector_health_check_minute,
            func=run_all_collector_health_checks,
            name="Collector Health Checks (daily night)",
        )

    yield

    # Shutdown
    stop_scheduler()
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Just-We",
        description="微信公众号智能权重监控系统",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application-specific exceptions."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        errors = _json_safe(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": _build_validation_message(errors),
                "details": errors,
            },
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    app.mount(settings.media_url_prefix, StaticFiles(directory=settings.media_root, check_dir=False), name="media")

    # Register API routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(articles_router, prefix="/api")
    app.include_router(article_exports_router, prefix="/api")
    app.include_router(proxies_router, prefix="/api")
    app.include_router(weight_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(collector_accounts_router, prefix="/api")
    app.include_router(monitored_accounts_router, prefix="/api")
    app.include_router(fetch_jobs_router, prefix="/api")
    app.include_router(system_config_router, prefix="/api")
    app.include_router(feeds_router, prefix="/api")
    app.include_router(image_router, prefix="/api")
    app.include_router(rate_limit_router, prefix="/api")
    app.include_router(public_feeds_router)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve built frontend assets and SPA deep-link fallbacks."""
        if not _should_serve_spa(full_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

        dist_dir = _frontend_dist()
        index_file = dist_dir / "index.html"
        requested_file = (dist_dir / full_path).resolve()

        try:
            requested_file.relative_to(dist_dir.resolve())
        except ValueError:
            requested_file = index_file

        if requested_file.is_file():
            return FileResponse(requested_file)
        if index_file.is_file():
            return FileResponse(index_file)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Frontend build not found"},
        )

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
