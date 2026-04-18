"""Proxy repository for database operations."""

from datetime import datetime, timezone

from sqlalchemy import Select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import Proxy, ProxyServiceBinding, ProxyServiceKey, ServiceType
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
            conditions.append(Proxy.is_active.is_(True))
            conditions.append((Proxy.fail_until.is_(None)) | (Proxy.fail_until <= datetime.now(timezone.utc)))

        result = await self.db.execute(
            Select(Proxy).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_active_proxies(self) -> list[Proxy]:
        """Get all active proxies."""
        result = await self.db.execute(
            Select(Proxy).where(Proxy.is_active.is_(True))
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
                    Proxy.is_active.is_(True),
                    (Proxy.fail_until.is_(None)) | (Proxy.fail_until <= datetime.now(timezone.utc)),
                )
            )
            .order_by(Proxy.success_rate.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_proxy_bindings(self, proxy_id: int) -> list[ProxyServiceBinding]:
        result = await self.db.execute(
            Select(ProxyServiceBinding)
            .where(ProxyServiceBinding.proxy_id == proxy_id)
            .order_by(ProxyServiceBinding.priority.asc(), ProxyServiceBinding.id.asc())
        )
        return list(result.scalars().all())

    async def get_proxies_for_service_key(
        self,
        service_key: ProxyServiceKey,
        active_only: bool = True,
    ) -> list[Proxy]:
        conditions = [
            ProxyServiceBinding.service_key == service_key,
            ProxyServiceBinding.is_enabled.is_(True),
        ]
        if active_only:
            conditions.extend(
                [
                    Proxy.is_active.is_(True),
                    (Proxy.fail_until.is_(None)) | (Proxy.fail_until <= datetime.now(timezone.utc)),
                ]
            )
        result = await self.db.execute(
            Select(Proxy)
            .join(ProxyServiceBinding, ProxyServiceBinding.proxy_id == Proxy.id)
            .where(and_(*conditions))
            .order_by(ProxyServiceBinding.priority.asc(), Proxy.id.asc())
        )
        return list(result.scalars().unique().all())

    async def replace_bindings(
        self,
        proxy: Proxy,
        service_keys: list[ProxyServiceKey],
    ) -> list[ProxyServiceBinding]:
        for binding in await self.get_proxy_bindings(proxy.id):
            await self.db.delete(binding)
        await self.db.flush()

        bindings: list[ProxyServiceBinding] = []
        for index, service_key in enumerate(dict.fromkeys(service_keys)):
            binding = ProxyServiceBinding(
                proxy_id=proxy.id,
                service_key=service_key,
                is_enabled=True,
                priority=(index + 1) * 100,
            )
            self.db.add(binding)
            bindings.append(binding)
        await self.db.flush()
        for binding in bindings:
            await self.db.refresh(binding)
        return bindings
