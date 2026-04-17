"""Proxy repository for database operations."""

from sqlalchemy import Select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import Proxy, ServiceType
from app.repositories.base import BaseRepository


class ProxyRepository(BaseRepository):
    """Repository for Proxy model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Proxy, db)

    async def get_by_service_type(
        self,
        service_type: ServiceType,
        active_only: bool = True,
    ) -> list[Proxy]:
        """Get proxies by service type."""
        conditions = [Proxy.service_type == service_type]
        if active_only:
            conditions.append(Proxy.is_active == True)

        result = await self.db.execute(
            Select(Proxy).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_active_proxies(self) -> list[Proxy]:
        """Get all active proxies."""
        result = await self.db.execute(
            Select(Proxy).where(Proxy.is_active == True)
        )
        return list(result.scalars().all())

    async def update_success_rate(self, proxy: Proxy, success_rate: float) -> Proxy:
        """Update proxy success rate."""
        return await self.update(proxy, success_rate=success_rate)

    async def deactivate(self, proxy: Proxy) -> Proxy:
        """Deactivate a proxy."""
        return await self.update(proxy, is_active=False)

    async def get_best_proxy_for_service(
        self,
        service_type: ServiceType,
    ) -> Proxy | None:
        """Get the best proxy for a service type based on success rate."""
        result = await self.db.execute(
            Select(Proxy)
            .where(
                and_(
                    Proxy.service_type == service_type,
                    Proxy.is_active == True,
                )
            )
            .order_by(Proxy.success_rate.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
