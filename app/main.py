"""
DynamicWePubMonitor - Main Application Entry Point

微信公众号智能权重监控系统
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.redis import close_redis
from app.api import (
    auth_router,
    accounts_router,
    qr_router,
    articles_router,
    proxies_router,
    weight_router,
    tasks_router,
    logs_router,
    notifications_router,
    users_router,
)
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.core.exceptions import AppException


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await init_db()
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DynamicWePubMonitor",
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
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "details": exc.errors(),
            },
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    # Register API routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(accounts_router, prefix="/api")
    app.include_router(qr_router, prefix="/api")
    app.include_router(articles_router, prefix="/api")
    app.include_router(proxies_router, prefix="/api")
    app.include_router(weight_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(users_router, prefix="/api")

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
