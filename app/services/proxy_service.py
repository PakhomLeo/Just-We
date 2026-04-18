"""Proxy service for proxy pool management."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import (
    LEGACY_SERVICE_TO_PROXY_SERVICE,
    Proxy,
    ProxyKind,
    ProxyRotationMode,
    ProxyServiceKey,
    ServiceType,
)
from app.repositories.proxy_repo import ProxyRepository
from app.core.exceptions import ProxyNotAvailableException


STATIC_OR_STICKY_KINDS = {
    ProxyKind.ISP_STATIC,
    ProxyKind.RESIDENTIAL_STATIC,
    ProxyKind.MOBILE_STATIC,
}

LOGIN_SERVICE_KEYS = {
    ProxyServiceKey.MP_ADMIN_LOGIN,
    ProxyServiceKey.WEREAD_LOGIN,
}

WECHAT_SERVICE_KEYS = {
    ProxyServiceKey.MP_ADMIN_LOGIN,
    ProxyServiceKey.MP_LIST,
    ProxyServiceKey.MP_DETAIL,
    ProxyServiceKey.WEREAD_LOGIN,
    ProxyServiceKey.WEREAD_LIST,
    ProxyServiceKey.WEREAD_DETAIL,
    ProxyServiceKey.IMAGE_PROXY,
}


class ProxyService:
    """Service for proxy pool management."""

    _rr_index: dict[str, int] = {}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proxy_repo = ProxyRepository(db)

    async def get_proxy_for_service(
        self,
        service_type: ServiceType,
    ) -> Proxy:
        """Get a proxy for a specific service type."""
        return await self.select_proxy(LEGACY_SERVICE_TO_PROXY_SERVICE[service_type])

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

    async def get_proxies_by_service_key(
        self,
        service_key: ProxyServiceKey,
        active_only: bool = True,
    ) -> list[Proxy]:
        """Get proxies bound to a reusable service key."""
        return await self.proxy_repo.get_proxies_for_service_key(
            service_key, active_only=active_only
        )

    async def get_proxy_pool_for_service(self, service_type: ServiceType) -> list[Proxy]:
        """Return active proxies ordered for retry/rotation."""
        return await self.get_proxy_pool_for_service_key(LEGACY_SERVICE_TO_PROXY_SERVICE[service_type])

    def compatible_service_keys(self, proxy: Proxy) -> list[ProxyServiceKey]:
        """Return services that can use this proxy based on type and sticky settings."""
        if proxy.proxy_kind == ProxyKind.DATACENTER:
            return [ProxyServiceKey.AI]

        if proxy.proxy_kind in {ProxyKind.ISP_STATIC, ProxyKind.RESIDENTIAL_STATIC}:
            return [
                ProxyServiceKey.MP_ADMIN_LOGIN,
                ProxyServiceKey.WEREAD_LOGIN,
                ProxyServiceKey.MP_LIST,
                ProxyServiceKey.WEREAD_LIST,
                ProxyServiceKey.MP_DETAIL,
                ProxyServiceKey.WEREAD_DETAIL,
            ]

        if proxy.proxy_kind == ProxyKind.MOBILE_STATIC:
            return [
                ProxyServiceKey.MP_ADMIN_LOGIN,
                ProxyServiceKey.WEREAD_LOGIN,
                ProxyServiceKey.MP_LIST,
                ProxyServiceKey.WEREAD_LIST,
                ProxyServiceKey.MP_DETAIL,
                ProxyServiceKey.WEREAD_DETAIL,
            ]

        if proxy.proxy_kind in {ProxyKind.RESIDENTIAL_ROTATING, ProxyKind.MOBILE_ROTATING, ProxyKind.CUSTOM_GATEWAY}:
            services = [
                ProxyServiceKey.MP_DETAIL,
                ProxyServiceKey.WEREAD_DETAIL,
                ProxyServiceKey.IMAGE_PROXY,
            ]
            if (proxy.sticky_ttl_seconds or 0) >= 300:
                services.extend([ProxyServiceKey.MP_LIST, ProxyServiceKey.WEREAD_LIST])
            return services

        return []

    def validate_service_bindings(self, proxy: Proxy, service_keys: list[ProxyServiceKey]) -> None:
        compatible = set(self.compatible_service_keys(proxy))
        invalid = [key.value for key in service_keys if key not in compatible]
        if invalid:
            raise ValueError(f"Proxy type {proxy.proxy_kind.value} cannot be used for: {', '.join(invalid)}")

    def incompatible_reasons(self, proxy: Proxy) -> dict[str, str]:
        compatible = set(self.compatible_service_keys(proxy))
        reasons: dict[str, str] = {}
        for service_key in ProxyServiceKey:
            if service_key in compatible:
                continue
            if proxy.proxy_kind == ProxyKind.DATACENTER:
                reasons[service_key.value] = "数据中心代理仅允许用于 AI，禁止用于微信链路"
            elif service_key in LOGIN_SERVICE_KEYS:
                reasons[service_key.value] = "登录会话需要静态 ISP、静态住宅或静态移动代理"
            elif service_key in {ProxyServiceKey.MP_LIST, ProxyServiceKey.WEREAD_LIST}:
                reasons[service_key.value] = "列表抓取需要静态代理，或 sticky_ttl_seconds >= 300 的粘性轮换代理"
            else:
                reasons[service_key.value] = "当前代理类型不推荐用于该服务"
        return reasons

    async def replace_service_bindings(
        self,
        proxy: Proxy,
        service_keys: list[ProxyServiceKey],
    ) -> list[ProxyServiceKey]:
        self.validate_service_bindings(proxy, service_keys)
        bindings = await self.proxy_repo.replace_bindings(proxy, service_keys)
        await self.db.refresh(proxy, attribute_names=["service_bindings"])
        return [binding.service_key for binding in bindings]

    def _min_success_rate(self) -> float:
        return 50.0

    def _candidate_key(self, service_key: ProxyServiceKey) -> str:
        return service_key.value

    async def get_proxy_pool_for_service_key(self, service_key: ProxyServiceKey) -> list[Proxy]:
        proxies = await self.proxy_repo.get_proxies_for_service_key(service_key, active_only=True)
        if not proxies:
            legacy_types = [
                service_type
                for service_type, mapped_key in LEGACY_SERVICE_TO_PROXY_SERVICE.items()
                if mapped_key == service_key
            ]
            legacy: list[Proxy] = []
            for service_type in legacy_types:
                legacy.extend(await self.proxy_repo.get_by_service_type(service_type, active_only=True))
            proxies = legacy
        min_success_rate = self._min_success_rate()
        filtered = [proxy for proxy in proxies if (proxy.success_rate or 0) >= min_success_rate]
        # Priority/order comes from binding; success rate is only used as a light tiebreaker.
        return sorted(filtered, key=lambda proxy: (-(proxy.success_rate or 0) if proxy.rotation_mode == ProxyRotationMode.FIXED else 0, proxy.id))

    async def select_proxy(
        self,
        service_key: ProxyServiceKey,
        account_id: int | None = None,
        purpose: str | None = None,
    ) -> Proxy:
        """Select a proxy for a business service, using fixed login or round-robin rules."""
        if service_key == ProxyServiceKey.AI:
            proxies = await self.get_proxy_pool_for_service_key(service_key)
            if not proxies:
                raise ProxyNotAvailableException(service_key.value)
        else:
            proxies = await self.get_proxy_pool_for_service_key(service_key)
            if not proxies:
                raise ProxyNotAvailableException(service_key.value)

        fixed = [proxy for proxy in proxies if proxy.rotation_mode == ProxyRotationMode.FIXED]
        if service_key in LOGIN_SERVICE_KEYS and fixed:
            return fixed[0]

        key = self._candidate_key(service_key)
        index = self._rr_index.get(key, 0)
        proxy = proxies[index % len(proxies)]
        self._rr_index[key] = index + 1
        return proxy

    async def mark_proxy_success(self, proxy: Proxy) -> Proxy:
        """Reward a proxy after a successful upstream request."""
        new_rate = min(100.0, proxy.success_rate + 2.0)
        return await self.proxy_repo.update(
            proxy,
            success_rate=new_rate,
            fail_until=None,
            last_error=None,
            last_checked_at=datetime.now(timezone.utc),
        )

    async def mark_proxy_failure(self, proxy: Proxy, error: str | None = None, cooldown_seconds: int = 120) -> Proxy:
        """Penalize a proxy after request failure or invalid upstream content."""
        new_rate = max(0.0, proxy.success_rate - 15.0)
        return await self.proxy_repo.update(
            proxy,
            success_rate=new_rate,
            fail_until=datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds),
            last_error=error,
            last_checked_at=datetime.now(timezone.utc),
        )

    async def create_proxy(
        self,
        host: str,
        port: int,
        service_type: ServiceType,
        username: str | None = None,
        password: str | None = None,
        proxy_kind: ProxyKind = ProxyKind.RESIDENTIAL_ROTATING,
        rotation_mode: ProxyRotationMode = ProxyRotationMode.ROUND_ROBIN,
        sticky_ttl_seconds: int | None = None,
        provider_name: str | None = None,
        notes: str | None = None,
        service_keys: list[ProxyServiceKey] | None = None,
    ) -> Proxy:
        """Create a new proxy."""
        if service_keys is None and proxy_kind == ProxyKind.RESIDENTIAL_ROTATING:
            if service_type in {ServiceType.MP_LIST, ServiceType.WEREAD_LIST}:
                proxy_kind = ProxyKind.ISP_STATIC
                rotation_mode = ProxyRotationMode.STICKY
                sticky_ttl_seconds = sticky_ttl_seconds or 1800
            elif service_type == ServiceType.AI:
                proxy_kind = ProxyKind.DATACENTER
                rotation_mode = ProxyRotationMode.ROUND_ROBIN
        proxy = await self.proxy_repo.create(
            host=host,
            port=port,
            service_type=service_type,
            username=username,
            password=password,
            proxy_kind=proxy_kind,
            rotation_mode=rotation_mode,
            sticky_ttl_seconds=sticky_ttl_seconds,
            provider_name=provider_name,
            notes=notes,
            is_active=True,
            success_rate=100.0,
        )
        keys = service_keys if service_keys is not None else [LEGACY_SERVICE_TO_PROXY_SERVICE[service_type]]
        await self.replace_service_bindings(proxy, keys)
        return proxy

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[Proxy]:
        created: list[Proxy] = []
        for item in items:
            proxy = await self.create_proxy(**item)
            created.append(proxy)
        return created

    async def update_proxy(
        self,
        proxy_id: int,
        **kwargs: Any,
    ) -> Proxy:
        """Update a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        updated = await self.proxy_repo.update(proxy, **kwargs)
        self.validate_service_bindings(updated, updated.service_keys)
        return updated

    async def delete_proxy(self, proxy_id: int) -> None:
        """Delete a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        from sqlalchemy import Select

        from app.models.collector_account import (
            CollectorAccount,
            CollectorAccountStatus,
            CollectorHealthStatus,
        )

        result = await self.db.execute(Select(CollectorAccount).where(CollectorAccount.login_proxy_id == proxy_id))
        accounts = list(result.scalars().all())
        for account in accounts:
            metadata = dict(account.metadata_json or {})
            metadata["login_proxy_missing"] = True
            metadata["login_proxy_missing_reason"] = "绑定登录代理已被删除，需要重新绑定并重新登录"
            account.login_proxy_id = None
            account.status = CollectorAccountStatus.ERROR
            account.health_status = CollectorHealthStatus.INVALID
            account.risk_reason = "绑定登录代理已被删除，需要重新绑定并重新登录"
            account.last_error_category = "login_proxy_missing"
            account.credentials = {}
            account.metadata_json = metadata
        await self.db.flush()
        await self.proxy_repo.delete(proxy)

    async def test_proxy(self, proxy: Proxy) -> dict[str, Any]:
        """Test if a proxy is working."""
        test_url = "https://httpbin.org/ip"
        start_time = asyncio.get_event_loop().time()

        try:
            transport = httpx.AsyncHTTPTransport(proxy=proxy.proxy_url)
            async with httpx.AsyncClient(
                transport=transport,
                timeout=10.0,
            ) as client:
                response = await client.get(test_url)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000

                if response.status_code == 200:
                    await self.mark_proxy_success(proxy)
                    return {
                        "proxy_id": proxy.id,
                        "success": True,
                        "latency_ms": latency,
                        "error": None,
                    }
                else:
                    await self.mark_proxy_failure(proxy, f"HTTP {response.status_code}", cooldown_seconds=60)
                    return {
                        "proxy_id": proxy.id,
                        "success": False,
                        "latency_ms": latency,
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            await self.mark_proxy_failure(proxy, str(e), cooldown_seconds=120)
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
        return await self.select_proxy(LEGACY_SERVICE_TO_PROXY_SERVICE[service_type])

    async def deactivate_proxy(self, proxy_id: int) -> Proxy:
        """Deactivate a proxy."""
        proxy = await self.proxy_repo.get_by_id(proxy_id)
        if proxy is None:
            raise ProxyNotAvailableException(f"proxy_id={proxy_id}")
        return await self.proxy_repo.deactivate(proxy)

    async def get_proxy_count(self) -> int:
        """Get total proxy count."""
        return await self.proxy_repo.get_count()

    def _is_cooling(self, proxy: Proxy, now: datetime) -> bool:
        if proxy.fail_until is None:
            return False
        fail_until = proxy.fail_until
        if fail_until.tzinfo is None:
            fail_until = fail_until.replace(tzinfo=timezone.utc)
        return fail_until > now

    async def get_proxy_stats(self) -> dict[str, Any]:
        """Return real proxy health statistics."""
        proxies = await self.proxy_repo.get_all(skip=0, limit=10000)
        now = datetime.now(timezone.utc)
        total = len(proxies)
        active = len([proxy for proxy in proxies if proxy.is_active])
        cooling = len([proxy for proxy in proxies if self._is_cooling(proxy, now)])
        average_success_rate = (
            round(sum(proxy.success_rate or 0 for proxy in proxies) / total, 2)
            if total
            else 0.0
        )
        by_service: dict[str, dict[str, Any]] = {}
        for proxy in proxies:
            keys = proxy.service_keys or [LEGACY_SERVICE_TO_PROXY_SERVICE.get(proxy.service_type, ProxyServiceKey.MP_DETAIL)]
            for service_key in keys:
                key = service_key.value
                item = by_service.setdefault(
                    key,
                    {"total": 0, "active": 0, "cooling": 0, "average_success_rate": 0.0},
                )
                item["total"] += 1
                if proxy.is_active:
                    item["active"] += 1
                if self._is_cooling(proxy, now):
                    item["cooling"] += 1
                item["average_success_rate"] += proxy.success_rate or 0
        for item in by_service.values():
            item["average_success_rate"] = round(item["average_success_rate"] / item["total"], 2) if item["total"] else 0.0
        by_kind: dict[str, int] = {}
        by_rotation_mode: dict[str, int] = {}
        for proxy in proxies:
            by_kind[proxy.proxy_kind.value] = by_kind.get(proxy.proxy_kind.value, 0) + 1
            by_rotation_mode[proxy.rotation_mode.value] = by_rotation_mode.get(proxy.rotation_mode.value, 0) + 1
        return {
            "total": total,
            "active": active,
            "cooling": cooling,
            "average_success_rate": average_success_rate,
            "by_service": by_service,
            "by_kind": by_kind,
            "by_rotation_mode": by_rotation_mode,
        }
