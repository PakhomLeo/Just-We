"""QR login providers for collector accounts."""

from __future__ import annotations

import json
import re
import secrets
import base64
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
import pyqrcode

from app.core.config import get_settings
from app.core.exceptions import QRProviderException, QRProviderNotConfiguredException
from app.models.collector_account import CollectorAccountType


settings = get_settings()


def build_qr_svg_data_url(value: str) -> str:
    """Encode a QR payload as an SVG data URL that can be rendered by <img>."""
    buffer = BytesIO()
    pyqrcode.create(value).svg(buffer, scale=5)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


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

    def __init__(self, proxy_url: str | None = None) -> None:
        self.proxy_url = proxy_url

    async def generate(self) -> ProviderGenerateResult:
        raise NotImplementedError

    async def poll(self, state: dict[str, Any]) -> ProviderPollResult:
        raise NotImplementedError

    async def cancel(self, state: dict[str, Any]) -> None:
        return None


class WereadPlatformQRProvider(BaseQRProvider):
    """Use an external platform compatible with wewe-rss login APIs."""

    provider_name = "weread_platform"

    def __init__(self, proxy_url: str | None = None) -> None:
        super().__init__(proxy_url=proxy_url)
        self.base_url = settings.weread_platform_url
        self.timeout = settings.weread_platform_timeout_seconds
        if not self.base_url:
            raise QRProviderNotConfiguredException("weread_platform")

    async def generate(self) -> ProviderGenerateResult:
        async with httpx.AsyncClient(timeout=self.timeout, proxy=self.proxy_url) as client:
            try:
                response = await client.get(urljoin(self.base_url, "/api/v2/login/platform"))
                response.raise_for_status()
            except Exception as exc:
                raise QRProviderException(self.provider_name, str(exc)) from exc

        payload = response.json()
        provider_ticket = str(payload["uuid"])
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=settings.qr_code_expire_seconds)
        return ProviderGenerateResult(
            qr_url=build_qr_svg_data_url(payload["scanUrl"]),
            provider_ticket=provider_ticket,
            expire_at=expire_at,
            state={"provider_ticket": provider_ticket, "scan_url": payload["scanUrl"]},
        )

    async def poll(self, state: dict[str, Any]) -> ProviderPollResult:
        provider_ticket = state["provider_ticket"]
        async with httpx.AsyncClient(timeout=max(self.timeout, 120), proxy=self.proxy_url) as client:
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
        client = httpx.AsyncClient(
            timeout=30,
            headers=self._build_headers(),
            follow_redirects=True,
            proxy=state.get("proxy_url") or self.proxy_url,
        )
        for name, value in (state.get("cookies") or {}).items():
            client.cookies.set(name, value, domain=".mp.weixin.qq.com")
        return client

    def _cookie_header(self, cookies: dict[str, Any]) -> str:
        return "; ".join(f"{key}={value}" for key, value in cookies.items() if value is not None)

    def _extract_token_from_login_response(self, response: httpx.Response, payload: dict[str, Any]) -> str | None:
        redirect_url = payload.get("redirect_url") or payload.get("redirectUrl") or payload.get("url") or ""
        for candidate in [redirect_url, response.headers.get("location") or "", response.text]:
            if not candidate:
                continue
            parsed = urlparse(candidate)
            token = (parse_qs(parsed.query).get("token") or [None])[0]
            if token:
                return token
            token_match = re.search(r"token=([^&\\s\"']+)", candidate)
            if token_match:
                return token_match.group(1)
        return None

    def _extract_home_profile(self, html: str) -> dict[str, str | None]:
        nickname = None
        fakeid = None
        for pattern in [
            r"nick_name\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"nickname\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"operator_nickname\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ]:
            match = re.search(pattern, html or "")
            if match:
                nickname = match.group(1).strip()
                break
        for pattern in [
            r"fakeid\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"fakeId\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ]:
            match = re.search(pattern, html or "")
            if match:
                fakeid = match.group(1).strip()
                break
        return {"nickname": nickname, "fakeid": fakeid}

    def _parse_searchbiz_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        entries = (
            payload.get("list")
            or payload.get("data", {}).get("list")
            or payload.get("search_list")
            or payload.get("items")
            or []
        )
        if isinstance(entries, str):
            try:
                entries = json.loads(entries)
            except Exception:
                entries = []
        if isinstance(entries, dict):
            entries = entries.get("list", [])
        if not isinstance(entries, list) or not entries:
            return {}
        first = entries[0] or {}
        return {
            "fakeid": first.get("fakeid") or first.get("fakeId"),
            "nickname": first.get("nickname") or first.get("nick_name") or first.get("name"),
            "alias": first.get("alias"),
            "avatar_url": first.get("round_head_img") or first.get("head_img") or first.get("avatar"),
            "raw": first,
        }

    async def discover_profile_from_credentials(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Discover MP admin nickname and fakeid from persisted token/cookies."""
        cookies = credentials.get("cookies") or {}
        token = credentials.get("token")
        if not cookies or not token:
            return {"fakeid": None, "nickname": None, "error": "missing_token_or_cookies"}
        headers = self._build_headers()
        async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True, cookies=cookies) as client:
            home_response = await client.get(
                f"{self.base_url}/cgi-bin/home",
                params={"token": token, "lang": "zh_CN"},
            )
            home_profile = self._extract_home_profile(home_response.text)
            query = home_profile.get("nickname") or credentials.get("nickname") or ""
            search_payload: dict[str, Any] = {}
            if query:
                response = await client.get(
                    f"{self.base_url}/cgi-bin/searchbiz",
                    params={
                        "action": "search_biz",
                        "token": token,
                        "lang": "zh_CN",
                        "f": "json",
                        "ajax": "1",
                        "random": "0.1",
                        "query": query,
                        "begin": "0",
                        "count": "5",
                    },
                )
                if response.status_code < 400:
                    try:
                        search_payload = self._parse_searchbiz_response(response.json())
                    except Exception:
                        search_payload = {}
            fakeid = home_profile.get("fakeid") or search_payload.get("fakeid")
            nickname = search_payload.get("nickname") or home_profile.get("nickname")
            return {
                "fakeid": fakeid,
                "nickname": nickname,
                "alias": search_payload.get("alias"),
                "avatar_url": search_payload.get("avatar_url"),
                "home_profile": home_profile,
                "searchbiz": search_payload.get("raw"),
                "cookies": dict(client.cookies.items()),
            }

    async def _fetch_qr_data_url(self, client: httpx.AsyncClient, qr_url: str) -> str:
        """Return a browser-safe data URL so mp.weixin hotlink restrictions do not break <img>."""
        response = await client.get(qr_url, headers={**self._build_headers(), "Referer": f"{self.base_url}/"})
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/png").split(";")[0].strip().lower()
        if not content_type.startswith("image/"):
            raise QRProviderException(self.provider_name, f"QR endpoint returned non-image content: {content_type}")
        encoded = base64.b64encode(response.content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    async def generate(self) -> ProviderGenerateResult:
        async with httpx.AsyncClient(timeout=30, headers=self._build_headers(), follow_redirects=True, proxy=self.proxy_url) as client:
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
            qr_display_url = await self._fetch_qr_data_url(client, qr_url)

            state = {
                "provider_ticket": uuid_value,
                "uuid": uuid_value,
                "fingerprint": fingerprint,
                "cookies": dict(client.cookies.items()),
                "proxy_url": self.proxy_url,
            }
            expire_at = datetime.now(timezone.utc) + timedelta(seconds=settings.qr_code_expire_seconds)
            return ProviderGenerateResult(
                qr_url=qr_display_url,
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
            try:
                status_code = int(payload.get("status"))
            except Exception:
                status_code = payload.get("status")
            if status_code in {2, 4, "scan"}:
                return ProviderPollResult(status="scanned", state=updated_state, message="已扫码，请确认登录")
            if status_code in {1, 3, "confirm", "confirmed"}:
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
            try:
                payload = response.json()
            except Exception:
                payload = {}
            token = cookies.get("token") or self._extract_token_from_login_response(response, payload)
            credentials = {
                "token": token,
                "cookies": cookies,
                "cookie": self._cookie_header(cookies),
            }
            profile: dict[str, Any] = {}
            if token:
                try:
                    profile = await self.discover_profile_from_credentials(credentials)
                    if profile.get("cookies"):
                        cookies = profile["cookies"]
                        credentials["cookies"] = cookies
                        credentials["cookie"] = self._cookie_header(cookies)
                except Exception as exc:
                    profile = {"error": str(exc)}
            fakeid = profile.get("fakeid")
            nickname = profile.get("nickname")
            external_id = cookies.get("wxuin") or token or state["provider_ticket"]
            display_name = nickname or f"公众号管理员账号 {str(external_id)[-6:]}"
            if fakeid:
                credentials["fakeid"] = fakeid
            if nickname:
                credentials["nickname"] = nickname
            return {
                "external_id": str(external_id),
                "display_name": display_name,
                "credentials": credentials,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=4),
                "metadata_json": {
                    "provider": self.provider_name,
                    "provider_ticket": state["provider_ticket"],
                    "fingerprint": state["fingerprint"],
                    "fakeid": fakeid,
                    "fakeid_missing": not bool(fakeid),
                    "nickname": nickname,
                    "login_response": payload,
                    "profile": profile,
                },
            }


async def discover_mp_admin_profile(credentials: dict[str, Any]) -> dict[str, Any]:
    """Public helper used by API/services to refresh MP admin fakeid metadata."""
    return await MpAdminQRProvider().discover_profile_from_credentials(credentials)


def get_qr_provider(account_type: CollectorAccountType, proxy_url: str | None = None) -> BaseQRProvider:
    if account_type == CollectorAccountType.WEREAD:
        return WereadPlatformQRProvider(proxy_url=proxy_url)
    if account_type == CollectorAccountType.MP_ADMIN:
        return MpAdminQRProvider(proxy_url=proxy_url)
    raise QRProviderException("unknown", f"Unsupported collector account type: {account_type.value}")
