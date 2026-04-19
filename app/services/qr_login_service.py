"""QR Login service for collector account authentication."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import QRCodeExpiredException, QRCodeNotFoundException
from app.core.redis import RedisKeys, get_redis_client
from app.models.collector_account import CollectorAccount, CollectorAccountType
from app.models.proxy import ProxyServiceKey
from app.schemas.qr import QRData, QRGenerateRequest, QRGenerateResponse, QRStatusResponse
from app.services.collector_account_service import CollectorAccountService
from app.services.proxy_service import ProxyService
from app.services.qr_providers import get_qr_provider


settings = get_settings()


class QRLoginService:
    """Manage QR login state and collector account creation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.collector_account_service = CollectorAccountService(db)
        self.redis = get_redis_client()
        self.expire_seconds = settings.qr_code_expire_seconds

    async def generate(self, request: QRGenerateRequest, current_user) -> QRGenerateResponse:
        login_proxy_id = request.proxy_id if isinstance(request.proxy_id, int) else None
        proxy_url = None
        if login_proxy_id is not None:
            proxy_service = ProxyService(self.db)
            from app.repositories.proxy_repo import ProxyRepository

            proxy = await ProxyRepository(self.db).get_by_id(login_proxy_id)
            if proxy is None:
                raise ValueError("所选账号代理不存在")
            service_key = (
                ProxyServiceKey.WEREAD_LOGIN
                if request.type == CollectorAccountType.WEREAD
                else ProxyServiceKey.MP_ADMIN_LOGIN
            )
            if service_key not in proxy_service.compatible_service_keys(proxy):
                raise ValueError("所选代理类型不能用于该账号登录/列表")
            proxy_url = proxy.proxy_url
        provider = self._get_provider(request.type, proxy_url)
        provider_result = await provider.generate()
        ticket = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        payload = QRData(
            ticket=ticket,
            type=request.type,
            created_at=now,
            expire_at=provider_result.expire_at,
            status="waiting",
        ).model_dump()
        payload.update(
            {
                "owner_user_id": str(current_user.id),
                "provider": provider.provider_name,
                "provider_ticket": provider_result.provider_ticket,
                "provider_state": provider_result.state,
                "login_proxy_id": login_proxy_id,
                "proxy_url": proxy_url,
            }
        )

        ttl_seconds = max(1, int((provider_result.expire_at - now).total_seconds()))
        await self.redis.setex(RedisKeys.qr_status(ticket), ttl_seconds, "waiting")
        await self.redis.setex(RedisKeys.qr_data(ticket), ttl_seconds, self._serialize_payload(payload))

        return QRGenerateResponse(
            qr_url=provider_result.qr_url,
            ticket=ticket,
            expire_at=provider_result.expire_at,
            provider=provider.provider_name,
            proxy_id=login_proxy_id,
            login_proxy_id=login_proxy_id,
        )

    async def get_status(self, ticket: str, current_user=None) -> QRStatusResponse:
        payload = await self._load_payload(ticket)
        if current_user is not None and payload.get("owner_user_id") != str(current_user.id) and current_user.role.value != "admin":
            raise QRCodeNotFoundException(ticket)

        if payload.get("status") != "confirmed":
            if self._is_expired(payload):
                await self.update_payload(ticket, payload, status="expired")
                payload["status"] = "expired"
            else:
                payload = await self._refresh_provider_status(ticket, payload)

        return QRStatusResponse(
            status=payload["status"],
            collector_account_id=payload.get("collector_account_id"),
            account_name=payload.get("account_name"),
            message=self._get_status_message(payload["status"], payload.get("message")),
            provider=payload.get("provider"),
        )

    async def update_payload(self, ticket: str, payload: dict[str, Any], **changes) -> dict[str, Any]:
        payload.update(changes)
        expire_at = datetime.fromisoformat(str(payload["expire_at"]).replace("Z", "+00:00"))
        ttl_seconds = max(1, int((expire_at - datetime.now(timezone.utc)).total_seconds()))
        await self.redis.setex(RedisKeys.qr_status(ticket), ttl_seconds, payload["status"])
        await self.redis.setex(RedisKeys.qr_data(ticket), ttl_seconds, self._serialize_payload(payload))
        return payload

    async def cancel(self, ticket: str) -> bool:
        payload = await self._load_payload(ticket)
        provider = self._get_provider(CollectorAccountType(payload.get("type", "mp_admin")), payload.get("proxy_url"))
        await provider.cancel(payload.get("provider_state") or {})
        await self.redis.delete(RedisKeys.qr_status(ticket))
        await self.redis.delete(RedisKeys.qr_data(ticket))
        return True

    async def _refresh_provider_status(self, ticket: str, payload: dict[str, Any], force: bool = False) -> dict[str, Any]:
        provider = self._get_provider(CollectorAccountType(payload["type"]), payload.get("proxy_url"))
        poll_result = await provider.poll(payload.get("provider_state") or {})
        payload["provider_state"] = poll_result.state
        payload["provider"] = provider.provider_name
        payload["message"] = poll_result.message
        if poll_result.account_payload:
            payload["account_payload"] = poll_result.account_payload
        if poll_result.status == "confirmed" and payload.get("collector_account_id") is None:
            owner_user_id = payload["owner_user_id"]
            account = await self._persist_account(payload, owner_user_id, poll_result.account_payload, None)
            payload["collector_account_id"] = account.id
            payload["account_name"] = account.display_name
        if force or poll_result.status != payload.get("status"):
            payload["status"] = poll_result.status
        await self.update_payload(ticket, payload)
        return payload

    async def _persist_account(
        self,
        payload: dict[str, Any],
        owner_user_id,
        account_payload: dict[str, Any] | None,
        display_name: str | None,
    ) -> CollectorAccount:
        if account_payload is None:
            raise QRCodeExpiredException(payload["ticket"])
        if isinstance(owner_user_id, str):
            owner_user_id = uuid.UUID(owner_user_id)
        return await self.collector_account_service.upsert_bound_account(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType(payload["type"]),
            display_name=display_name or account_payload["display_name"],
            credentials=account_payload["credentials"],
            external_id=account_payload.get("external_id"),
            expires_at=account_payload.get("expires_at"),
            metadata_json=account_payload.get("metadata_json"),
            login_proxy_id=payload.get("login_proxy_id"),
            last_login_proxy_ip=payload.get("proxy_url"),
        )

    async def _load_payload(self, ticket: str) -> dict[str, Any]:
        data = await self.redis.get(RedisKeys.qr_data(ticket))
        if data is None:
            raise QRCodeNotFoundException(ticket)
        return json.loads(data)

    def _serialize_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(
            payload,
            default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value),
        )

    def _is_expired(self, payload: dict[str, Any]) -> bool:
        expire_at = datetime.fromisoformat(str(payload["expire_at"]).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= expire_at

    def _get_status_message(self, status: str, override: str | None = None) -> str:
        if override:
            return override
        return {
            "waiting": "等待扫码",
            "scanned": "已扫码，请在手机上确认登录",
            "confirmed": "登录成功",
            "expired": "二维码已过期，请重新生成",
        }.get(status, "未知状态")

    def _get_provider(self, account_type: CollectorAccountType, proxy_url: str | None):
        try:
            return get_qr_provider(account_type, proxy_url=proxy_url)
        except TypeError:
            # Some tests monkeypatch get_qr_provider with the legacy one-arg shape.
            return get_qr_provider(account_type)
