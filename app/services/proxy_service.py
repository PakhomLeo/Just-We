"""Proxy service for proxy pool management."""

import asyncio
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import Proxy, ServiceType
from app.repositories.proxy_repo import ProxyRepository
from app.core.exceptions import ProxyNotAvailableException


class ProxyService:
    """Service for proxy pool management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proxy_repo = ProxyRepository(db)

    async def get_proxy_for_service(
        self,
        service_type: ServiceType,
    ) -> Proxy:
        """Get a proxy for a specific service type."""
        proxy = await self.proxy_repo.get_best_proxy_for_service(service_type)
        if proxy is None:
            raise ProxyNotAvailableException(service_type.value)
        return proxy

    async def get_all_proxies(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Proxy]:
        """Get all proxies."""
        return await self.proxy_repo.get_all(skip=skip, limit=limit)

    async def get_proxies_by_service_type(
        self,
        service_type: ServiceType,
        active_only: bool = True,
    ) -> list[Proxy]:
        """Get proxies by service type."""
        return await self.proxy_repo.get_by_service_type(
            service_type, active_only=active_only
        )

    async def create_proxy(
        self,
        host: str,
        port: int,
        service_type: ServiceType,
        username: str | None = None,
        password: str | None = None,
    ) -> Proxy:
        """Create a new proxy."""
        return await self.proxy_repo.create(
            host=host,
            port=port,
            service_type=service_type,
            username=username,
            password=password,
            is_active=True,
            success_rate=100.0,
        )

    async def update_proxy(
        self,
        proxy_id: int,
        **kwargs: Any,
    ) -> Proxy:
        """Update a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        return await self.proxy_repo.update(proxy, **kwargs)

    async def delete_proxy(self, proxy_id: int) -> None:
        """Delete a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        await self.proxy_repo.delete(proxy)

    async def test_proxy(self, proxy: Proxy) -> dict[str, Any]:
        """Test if a proxy is working."""
        test_url = "https://httpbin.org/ip"
        start_time = asyncio.get_event_loop().time()

        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy.proxy_url, "https://": proxy.proxy_url},
                timeout=10.0,
            ) as client:
                response = await client.get(test_url)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000

                if response.status_code == 200:
                    # Update success rate
                    new_rate = min(100.0, proxy.success_rate + 1.0)
                    await self.proxy_repo.update_success_rate(proxy, new_rate)
                    return {
                        "proxy_id": proxy.id,
                        "success": True,
                        "latency_ms": latency,
                        "error": None,
                    }
                else:
                    # Decrease success rate
                    new_rate = max(0.0, proxy.success_rate - 5.0)
                    await self.proxy_repo.update_success_rate(proxy, new_rate)
                    return {
                        "proxy_id": proxy.id,
                        "success": False,
                        "latency_ms": latency,
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            # Decrease success rate on error
            new_rate = max(0.0, proxy.success_rate - 10.0)
            await self.proxy_repo.update_success_rate(proxy, new_rate)
            return {
                "proxy_id": proxy.id,
                "success": False,
                "latency_ms": None,
                "error": str(e),
            }

    async def rotate(
        self,
        service_type: ServiceType,
    ) -> Proxy:
        """Get next available proxy for a service type (rotation)."""
        proxies = await self.proxy_repo.get_by_service_type(service_type)
        if not proxies:
            raise ProxyNotAvailableException(service_type.value)

        # Simple round-robin: return first active with high success rate
        for proxy in sorted(proxies, key=lambda p: p.success_rate, reverse=True):
            if proxy.is_active and proxy.success_rate >= 50.0:
                return proxy

        # If all have low success rate, return the best one anyway
        return max(proxies, key=lambda p: p.success_rate)

    async def deactivate_proxy(self, proxy_id: int) -> Proxy:
        """Deactivate a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        return await self.proxy_repo.deactivate(proxy)

    async def get_proxy_count(self) -> int:
        """Get total proxy count."""
        return await self.proxy_repo.get_count()
