"""Redis configuration and client management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings


settings = get_settings()

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency for getting Redis client."""
    client = get_redis_client()
    try:
        yield client
    finally:
        # Don't close the client as it's shared
        pass


@asynccontextmanager
async def get_redis_context() -> AsyncGenerator[Redis, None]:
    """Context manager for Redis client (for use outside of FastAPI)."""
    client = get_redis_client()
    try:
        yield client
    finally:
        pass  # Don't close the shared client


async def close_redis() -> None:
    """Close Redis connections."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class RedisKeys:
    """Redis key patterns for the application."""

    # QR Code login
    QR_PREFIX = "qr_login:"
    QR_STATUS = "qr_login:status:{ticket}"
    QR_DATA = "qr_login:data:{ticket}"

    # Proxy health cache
    PROXY_HEALTH = "proxy:health:{proxy_id}"

    # Rate limiting
    RATE_LIMIT = "rate_limit:{key}"

    @staticmethod
    def qr_status(ticket: str) -> str:
        """Get QR status key."""
        return f"qr_login:status:{ticket}"

    @staticmethod
    def qr_data(ticket: str) -> str:
        """Get QR data key."""
        return f"qr_login:data:{ticket}"
