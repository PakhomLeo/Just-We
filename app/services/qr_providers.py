"""QR login providers for collector accounts."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import get_settings
from app.core.exceptions import QRProviderException, QRProviderNotConfiguredException
from app.models.collector_account import CollectorAccountType


settings = get_settings()


@dataclass
class ProviderGenerateResult:
    qr_url: str
    provider_ticket: str
    expire_at: datetime
    state: dict[str, Any]


@dataclass
class ProviderPollResult:
    status: str
    state: dict[str, Any]
    account_payload: dict[str, Any] | None = None
    message: str | None = None


class BaseQRProvider:
    provider_name = "base"

    async def generate(self) -> ProviderGenerateResult:
        raise NotImplementedError

    async def poll(self, state: dict[str, Any]) -> ProviderPollResult:
        raise NotImplementedError

    async def cancel(self, state: dict[str, Any]) -> None:
        return None


class WereadPlatformQRProvider(BaseQRProvider):
    """Use an external platform compatible with wewe-rss login APIs."""

    provider_name = "weread_platform"

    def __init__(self) -> None:
        self.base_url = settings.weread_platform_url
        self.timeout = settings.weread_platform_timeout_seconds
        if not self.base_url:
            raise QRProviderNotConfiguredException("weread_platform")

    async def generate(self) -> ProviderGenerateResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(urljoin(self.base_url, "/api/v2/login/platform"))
                response.raise_for_status()
            except Exception as exc:
                raise QRProviderException(self.provider_name, str(exc)) from exc

        payload = response.json()
        provider_ticket = str(payload["uuid"])
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=settings.qr_code_expire_seconds)
        return ProviderGenerateResult(
            qr_url=payload["scanUrl"],
            provider_ticket=provider_ticket,
            expire_at=expire_at,
            state={"provider_ticket": provider_ticket},
        )

    async def poll(self, state: dict[str, Any]) -> ProviderPollResult:
        provider_ticket = state["provider_ticket"]
        async with httpx.AsyncClient(timeout=max(self.timeout, 120)) as client:
            try:
                response = await client.get(urljoin(self.base_url, f"/api/v2/login/platform/{provider_ticket}"))
                response.raise_for_status()
            except Exception as exc:
                raise QRProviderException(self.provider_name, str(exc)) from exc

        payload = response.json()
        token = payload.get("token")
        if token:
            account_payload = {
                "external_id": payload.get("username") or str(payload.get("vid") or provider_ticket),
                "display_name": payload.get("username") or "微信读书账号",
                "credentials": {
                    "token": token,
                    "vid": payload.get("vid"),
                    "username": payload.get("username"),
                },
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                "metadata_json": {
                    "provider": self.provider_name,
                    "provider_ticket": provider_ticket,
                    "platform_url": self.base_url.rstrip("/"),
                },
            }
            return ProviderPollResult(
                status="confirmed",
                state=state,
                account_payload=account_payload,
                message=payload.get("message") or "登录成功",
            )

        message = (payload.get("message") or "").lower()
        status = "waiting"
        if "scan" in message or "扫码" in message:
            status = "scanned"
        if "expired" in message or "过期" in message:
            status = "expired"
        return ProviderPollResult(status=status, state=state, message=payload.get("message"))


class MpAdminQRProvider(BaseQRProvider):
    """Direct mp.weixin.qq.com QR login provider."""

    provider_name = "mp_admin"
    base_url = "https://mp.weixin.qq.com"

    def _build_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": f"{self.base_url}/",
        }

    def _extract_qr_info(self, html: str) -> tuple[str | None, str | None]:
        qr_match = re.search(
            r"(https?:\/\/mp\.weixin\.qq\.com\/cgi-bin\/loginqrcode\?action=getqrcode&param=\d+)",
            html,
        )
        uuid_match = re.search(r'(?:"|\')uuid(?:"|\')\s*:\s*(?:"|\')([^"\']+)(?:"|\')', html)
        qr_url = qr_match.group(1) if qr_match else None
        uuid_value = uuid_match.group(1) if uuid_match else None
        return qr_url, uuid_value

    def _client_from_state(self, state: dict[str, Any]) -> httpx.AsyncClient:
        client = httpx.AsyncClient(timeout=30, headers=self._build_headers(), follow_redirects=True)
        for name, value in (state.get("cookies") or {}).items():
            client.cookies.set(name, value, domain=".mp.weixin.qq.com")
        return client

    async def generate(self) -> ProviderGenerateResult:
        async with httpx.AsyncClient(timeout=30, headers=self._build_headers(), follow_redirects=True) as client:
            try:
                response = await client.get(f"{self.base_url}/")
                response.raise_for_status()
            except Exception as exc:
                raise QRProviderException(self.provider_name, str(exc)) from exc

            qr_url, uuid_value = self._extract_qr_info(response.text)
            if not uuid_value:
                fingerprint = secrets.token_hex(16)
                start_response = await client.post(
                    f"{self.base_url}/cgi-bin/bizlogin",
                    params={"action": "startlogin"},
                    data={
                        "fingerprint": fingerprint,
                        "token": "",
                        "lang": "zh_CN",
                        "f": "json",
                        "ajax": "1",
                        "redirect_url": "/cgi-bin/home",
                        "login_type": "3",
                    },
                )
                start_response.raise_for_status()
                uuid_value = start_response.cookies.get("uuid") or client.cookies.get("uuid")
            else:
                fingerprint = client.cookies.get("fingerprint") or secrets.token_hex(16)

            if not uuid_value:
                raise QRProviderException(self.provider_name, "Unable to obtain mp_admin login UUID")

            qr_url = qr_url or (
                f"{self.base_url}/cgi-bin/scanloginqrcode?action=getqrcode&uuid={uuid_value}"
            )

            state = {
                "provider_ticket": uuid_value,
                "uuid": uuid_value,
                "fingerprint": fingerprint,
                "cookies": dict(client.cookies.items()),
            }
            expire_at = datetime.now(timezone.utc) + timedelta(seconds=settings.qr_code_expire_seconds)
            return ProviderGenerateResult(
                qr_url=qr_url,
                provider_ticket=uuid_value,
                expire_at=expire_at,
                state=state,
            )

    async def poll(self, state: dict[str, Any]) -> ProviderPollResult:
        async with self._client_from_state(state) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/cgi-bin/scanloginqrcode",
                    params={
                        "action": "ask",
                        "fingerprint": state["fingerprint"],
                        "lang": "zh_CN",
                        "f": "json",
                        "ajax": "1",
                    },
                )
                response.raise_for_status()
            except Exception as exc:
                raise QRProviderException(self.provider_name, str(exc)) from exc

            updated_state = {**state, "cookies": dict(client.cookies.items())}
            payload = response.json()
            status_code = payload.get("status")
            if status_code in {2, 4}:
                return ProviderPollResult(status="scanned", state=updated_state, message="已扫码，请确认登录")
            if status_code in {1, 3}:
                account_payload = await self._finalize_login(updated_state)
                return ProviderPollResult(
                    status="confirmed",
                    state=updated_state,
                    account_payload=account_payload,
                    message="登录成功",
                )
            if status_code in {5, -1}:
                return ProviderPollResult(status="expired", state=updated_state, message="二维码已过期")
            return ProviderPollResult(status="waiting", state=updated_state, message="等待扫码")

    async def _finalize_login(self, state: dict[str, Any]) -> dict[str, Any]:
        async with self._client_from_state(state) as client:
            response = await client.post(
                f"{self.base_url}/cgi-bin/bizlogin",
                params={"action": "login"},
                data={
                    "userlang": "zh_CN",
                    "redirect_url": "",
                    "cookie_forbidden": "0",
                    "cookie_cleaned": "0",
                    "plugin_used": "0",
                    "login_type": "3",
                    "fingerprint": state["fingerprint"],
                    "token": "",
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": "1",
                },
            )
            response.raise_for_status()
            cookies = dict(client.cookies.items())
            token = cookies.get("token")
            if not token:
                token_match = re.search(r"token=([^&\\s\"']+)", response.text)
                if token_match:
                    token = token_match.group(1)
            external_id = cookies.get("wxuin") or token or state["provider_ticket"]
            display_name = f"公众号管理员账号 {str(external_id)[-6:]}"
            return {
                "external_id": str(external_id),
                "display_name": display_name,
                "credentials": {
                    "token": token,
                    "cookies": cookies,
                },
                "expires_at": datetime.now(timezone.utc) + timedelta(days=4),
                "metadata_json": {
                    "provider": self.provider_name,
                    "provider_ticket": state["provider_ticket"],
                    "fingerprint": state["fingerprint"],
                },
            }


def get_qr_provider(account_type: CollectorAccountType) -> BaseQRProvider:
    if account_type == CollectorAccountType.WEREAD:
        return WereadPlatformQRProvider()
    if account_type == CollectorAccountType.MP_ADMIN:
        return MpAdminQRProvider()
    raise QRProviderException("unknown", f"Unsupported collector account type: {account_type.value}")
