"""Health check service for collector accounts."""

from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collector_account import CollectorAccount, CollectorAccountType, CollectorHealthStatus


class HealthCheckService:
    """Service for checking account health status."""

    # Default cookie validity period (4 days)
    DEFAULT_COOKIE_VALIDITY_DAYS = 4
    EXPIRING_SOON_HOURS = 24

    def __init__(self, db=None):
        self.db = db

    async def check_collector_account_health(
        self,
        account: CollectorAccount,
        db: AsyncSession | None = None,
    ) -> tuple[CollectorHealthStatus, str, datetime | None]:
        """Check health for new collector accounts."""
        now = datetime.now(timezone.utc)
        expires_at = account.expires_at

        if account.account_type == CollectorAccountType.MP_ADMIN:
            if not (account.credentials.get("cookies") or account.credentials.get("cookie")):
                return CollectorHealthStatus.INVALID, "未设置 MP Admin Cookie", expires_at
            if not account.credentials.get("token"):
                return CollectorHealthStatus.INVALID, "缺少 MP Admin token，请重新扫码登录公众号后台账号", expires_at
        elif account.account_type == CollectorAccountType.WEREAD:
            if not (account.credentials.get("token") or account.credentials.get("cookies")):
                return CollectorHealthStatus.INVALID, "未设置 WeRead 凭证", expires_at

        if expires_at and now > expires_at:
            return CollectorHealthStatus.EXPIRED, "凭证已过期", expires_at

        try:
            if account.account_type == CollectorAccountType.MP_ADMIN:
                status, reason = await self._check_mp_admin_collector(account)
            elif account.account_type == CollectorAccountType.WEREAD:
                status, reason = await self._check_weread_collector(account, db)
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
        db: AsyncSession | None = None,
    ) -> tuple[CollectorHealthStatus, str]:
        headers = self._build_collector_headers("https://weread.qq.com/")
        cookies = account.credentials.get("cookies") or {}
        token = account.credentials.get("token")

        # WeRead-compatible platform tokens are validated by the platform itself
        # during real list fetches. Extra article-list probes consume account/IP
        # quota and can push the account into platform risk control.
        if token and account.metadata_json.get("provider") == "weread_platform":
            platform_url = (account.metadata_json.get("platform_url") or "").rstrip("/")
            if platform_url:
                return CollectorHealthStatus.NORMAL, "平台令牌存在，等待抓取校验"

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
