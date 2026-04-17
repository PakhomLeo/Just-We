"""Health check service for legacy and collector accounts."""

from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import httpx

from app.models.account import Account, AccountType, HealthStatus
from app.models.collector_account import CollectorAccount, CollectorAccountType, CollectorHealthStatus


class HealthCheckService:
    """Service for checking account health status."""

    # Default cookie validity period (4 days)
    DEFAULT_COOKIE_VALIDITY_DAYS = 4
    EXPIRING_SOON_HOURS = 24

    def __init__(self, db=None):
        self.db = db

    async def check_account_health(
        self,
        account: Account,
    ) -> Tuple[HealthStatus, str]:
        """
        Check the health status of an account.

        Returns:
            Tuple of (health_status, reason)
        """
        # Check if cookies are set
        if not account.cookies:
            return HealthStatus.INVALID, "未设置 Cookie"

        # Check if cookies are expired based on cookies_expire_at
        if account.cookies_expire_at:
            if datetime.now(timezone.utc) > account.cookies_expire_at:
                return HealthStatus.EXPIRED, "Cookie 已过期"

        # Perform live health check based on account type
        try:
            if account.account_type == AccountType.WEREAD:
                return await self._check_weread_health(account)
            elif account.account_type == AccountType.MP:
                return await self._check_mp_health(account)
            else:
                return HealthStatus.INVALID, f"未知账号类型: {account.account_type}"
        except Exception as e:
            return HealthStatus.INVALID, f"健康检查异常: {str(e)}"

    async def _check_weread_health(self, account: Account) -> Tuple[HealthStatus, str]:
        """Check WeRead account health."""
        # WeRead health check endpoint
        url = "https://weread.qq.com/webapp/json/bookStoreHomePage"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://weread.qq.com/",
        }

        # Add cookies
        if account.cookies:
            cookie_str = self._format_cookies(account.cookies)
            headers["Cookie"] = cookie_str

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    # Check if response contains expected data
                    data = response.json()
                    if data.get("bookStoreHomePage"):
                        return HealthStatus.NORMAL, "正常"
                    else:
                        return HealthStatus.RESTRICTED, "数据异常"
                elif response.status_code == 403:
                    return HealthStatus.RESTRICTED, "访问被拒绝 (403)"
                elif response.status_code == 401:
                    return HealthStatus.EXPIRED, "未授权 (401)"
                else:
                    return HealthStatus.INVALID, f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            return HealthStatus.RESTRICTED, "请求超时"
        except httpx.RequestError as e:
            return HealthStatus.INVALID, f"请求失败: {str(e)}"

    async def _check_mp_health(self, account: Account) -> Tuple[HealthStatus, str]:
        """Check WeChat MP account health."""
        # MP health check endpoint - use profile or list endpoint
        url = "https://mp.weixin.qq.com/cgi-bin/home"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
        }

        # Add cookies
        if account.cookies:
            cookie_str = self._format_cookies(account.cookies)
            headers["Cookie"] = cookie_str

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    # Check if redirected to login
                    if "login" in response.headers.get("Location", ""):
                        return HealthStatus.EXPIRED, "需要重新登录"
                    # Check response content
                    text = response.text
                    if "accountupgrade" in text or "appmsg" in text:
                        return HealthStatus.NORMAL, "正常"
                    else:
                        return HealthStatus.RESTRICTED, "数据异常"
                elif response.status_code == 403:
                    return HealthStatus.RESTRICTED, "访问被拒绝 (403)"
                elif response.status_code == 302:
                    # Redirect usually means need to login
                    location = response.headers.get("Location", "")
                    if "login" in location.lower():
                        return HealthStatus.EXPIRED, "重定向到登录页"
                    return HealthStatus.RESTRICTED, f"重定向: {location[:50]}"
                elif response.status_code == 401:
                    return HealthStatus.EXPIRED, "未授权 (401)"
                else:
                    return HealthStatus.INVALID, f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            return HealthStatus.RESTRICTED, "请求超时"
        except httpx.RequestError as e:
            return HealthStatus.INVALID, f"请求失败: {str(e)}"

    async def check_collector_account_health(
        self,
        account: CollectorAccount,
    ) -> tuple[CollectorHealthStatus, str, datetime | None]:
        """Check health for new collector accounts."""
        now = datetime.now(timezone.utc)
        expires_at = account.expires_at

        if account.account_type == CollectorAccountType.MP_ADMIN:
            if not (account.credentials.get("cookies") or account.credentials):
                return CollectorHealthStatus.INVALID, "未设置 MP Admin Cookie", expires_at
        elif account.account_type == CollectorAccountType.WEREAD:
            if not (account.credentials.get("token") or account.credentials.get("cookies")):
                return CollectorHealthStatus.INVALID, "未设置 WeRead 凭证", expires_at

        if expires_at and now > expires_at:
            return CollectorHealthStatus.EXPIRED, "凭证已过期", expires_at

        try:
            if account.account_type == CollectorAccountType.MP_ADMIN:
                status, reason = await self._check_mp_admin_collector(account)
            elif account.account_type == CollectorAccountType.WEREAD:
                status, reason = await self._check_weread_collector(account)
            else:
                return CollectorHealthStatus.INVALID, f"未知抓取账号类型: {account.account_type}", expires_at
        except Exception as exc:
            return CollectorHealthStatus.INVALID, f"健康检查异常: {exc}", expires_at

        if status == CollectorHealthStatus.NORMAL and expires_at:
            remaining = expires_at - now
            if remaining <= timedelta(hours=self.EXPIRING_SOON_HOURS):
                return status, "凭证即将过期", expires_at

        return status, reason, expires_at

    def _build_collector_headers(self, referer: str) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": referer,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def _check_mp_admin_collector(
        self,
        account: CollectorAccount,
    ) -> tuple[CollectorHealthStatus, str]:
        cookies = account.credentials.get("cookies") or account.credentials
        token = account.credentials.get("token")
        params = {"token": token} if token else None
        headers = self._build_collector_headers("https://mp.weixin.qq.com/")

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                response = await client.get(
                    "https://mp.weixin.qq.com/cgi-bin/home",
                    params=params,
                    cookies=cookies,
                    headers=headers,
                )
        except httpx.TimeoutException:
            return CollectorHealthStatus.RESTRICTED, "健康检查请求超时"
        except httpx.RequestError as exc:
            return CollectorHealthStatus.INVALID, f"健康检查请求失败: {exc}"

        location = (response.headers.get("Location") or "").lower()
        body = response.text.lower()
        if response.status_code in {301, 302} and "login" in location:
            return CollectorHealthStatus.EXPIRED, "已跳转到登录页"
        if response.status_code == 401:
            return CollectorHealthStatus.EXPIRED, "未授权"
        if response.status_code == 403:
            return CollectorHealthStatus.RESTRICTED, "访问被拒绝"
        if response.status_code >= 500:
            return CollectorHealthStatus.RESTRICTED, f"上游异常 HTTP {response.status_code}"
        if response.status_code >= 400:
            return CollectorHealthStatus.INVALID, f"HTTP {response.status_code}"
        if "请使用微信扫描二维码登录" in response.text or "login_container" in body:
            return CollectorHealthStatus.EXPIRED, "需要重新登录"
        if any(marker in body for marker in ["cgi-bin/home", "masssendpage", "weui-desktop-layout", "appmsg"]):
            return CollectorHealthStatus.NORMAL, "正常"
        return CollectorHealthStatus.RESTRICTED, "返回内容不符合预期"

    async def _check_weread_collector(
        self,
        account: CollectorAccount,
    ) -> tuple[CollectorHealthStatus, str]:
        headers = self._build_collector_headers("https://weread.qq.com/")
        cookies = account.credentials.get("cookies") or {}
        token = account.credentials.get("token")

        # Prefer the platform token probe when available.
        if token and account.metadata_json.get("provider") == "weread_platform":
            platform_url = (account.metadata_json.get("platform_url") or "").rstrip("/")
            if platform_url:
                probe_candidates = [
                    "/api/v2/feeds",
                    "/api/v2/feeds/all",
                    "/api/v2/users/me",
                ]
                auth_headers = {**headers, "Authorization": f"Bearer {token}"}
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        for path in probe_candidates:
                            response = await client.get(f"{platform_url}{path}", headers=auth_headers)
                            if response.status_code == 200:
                                return CollectorHealthStatus.NORMAL, "正常"
                            if response.status_code in {401, 403}:
                                return CollectorHealthStatus.EXPIRED, "平台令牌失效"
                except httpx.TimeoutException:
                    return CollectorHealthStatus.RESTRICTED, "平台健康检查超时"
                except httpx.RequestError as exc:
                    return CollectorHealthStatus.INVALID, f"平台健康检查失败: {exc}"

        # Fall back to an authenticated-ish WeRead probe when cookies are present.
        if cookies:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        "https://weread.qq.com/webapp/json/bookStoreHomePage",
                        headers=headers,
                        cookies=cookies,
                    )
            except httpx.TimeoutException:
                return CollectorHealthStatus.RESTRICTED, "健康检查请求超时"
            except httpx.RequestError as exc:
                return CollectorHealthStatus.INVALID, f"健康检查请求失败: {exc}"

            if response.status_code == 200:
                return CollectorHealthStatus.NORMAL, "正常"
            if response.status_code in {401, 403}:
                return CollectorHealthStatus.EXPIRED, "WeRead 凭证失效"
            if response.status_code == 429:
                return CollectorHealthStatus.RESTRICTED, "请求过于频繁"
            if response.status_code >= 500:
                return CollectorHealthStatus.RESTRICTED, f"上游异常 HTTP {response.status_code}"
            return CollectorHealthStatus.INVALID, f"HTTP {response.status_code}"

        if token:
            return CollectorHealthStatus.NORMAL, "令牌存在，等待平台校验"
        return CollectorHealthStatus.INVALID, "缺少可用凭证"

    def _format_cookies(self, cookies: dict) -> str:
        """Format cookies dict to string."""
        if isinstance(cookies, str):
            return cookies
        return "; ".join(f"{k}={v}" for k, v in cookies.items())

    def calculate_expire_at(
        self,
        base_time: datetime | None = None,
        days: int | None = None,
    ) -> datetime:
        """Calculate cookies expire time based on settings.

        Args:
            base_time: Base time to calculate from (default: now)
            days: Number of days until expiration (default: from settings or 4)

        Returns:
            Expiration datetime with timezone
        """
        if base_time is None:
            base_time = datetime.now(timezone.utc)

        if days is None:
            days = self.DEFAULT_COOKIE_VALIDITY_DAYS

        return base_time + timedelta(days=days)


# Global instance
health_check_service = HealthCheckService()
