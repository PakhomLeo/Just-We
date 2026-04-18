"""Service for monitored source creation and management."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.collector_account import CollectorAccountStatus, CollectorAccountType, CollectorHealthStatus
from app.models.monitored_account import MonitoredAccount
from app.repositories.collector_account_repo import CollectorAccountRepository
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.system_config_service import SystemConfigService


class MonitoringSourceService:
    """Manage monitored public accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MonitoredAccountRepository(db)
        self.collector_repo = CollectorAccountRepository(db)
        self.system_config_service = SystemConfigService(db)

    async def list_visible(self, current_user, include_all: bool = False) -> list[MonitoredAccount]:
        owner_user_id = None if include_all and current_user.role.value == "admin" else current_user.id
        return await self.repo.get_visible_accounts(owner_user_id)

    async def get(self, monitored_account_id: int) -> MonitoredAccount | None:
        return await self.repo.get_by_id(monitored_account_id)

    async def get_visible(self, monitored_account_id: int, current_user) -> MonitoredAccount | None:
        account = await self.get(monitored_account_id)
        if account is None:
            return None
        if current_user.role.value == "admin" or account.owner_user_id == current_user.id:
            return account
        return None

    async def fetch_mode_for_tier(self, tier: int) -> CollectorAccountType:
        policy = await self.system_config_service.get_or_create_fetch_policy()
        return CollectorAccountType(policy.primary_modes.get(str(tier), "mp_admin"))

    def parse_source_url(self, source_url: str) -> dict:
        parsed = urlparse(source_url)
        query = parse_qs(parsed.query)
        biz = (query.get("__biz") or query.get("biz") or [None])[0]
        if not biz:
            tail = parsed.path.rstrip("/").split("/")[-1]
            biz = f"derived_{tail}" if tail else None
        if not biz:
            raise ValueError("Unable to parse biz from source URL")
        return {
            "biz": biz.replace("u__", ""),
            "mid": (query.get("mid") or [None])[0],
            "idx": (query.get("idx") or [None])[0],
            "sn": (query.get("sn") or [None])[0],
        }

    async def resolve_with_weread_platform(self, source_url: str) -> dict:
        """Resolve MP metadata via the WeRead-compatible platform when configured."""
        settings = get_settings()
        base_url = (settings.weread_platform_url or "").rstrip("/")
        if not base_url:
            return {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{base_url}/api/v2/platform/wxs2mp", json={"url": source_url})
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return {}
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        if not isinstance(payload, dict):
            return {}
        return {
            "biz": payload.get("biz") or payload.get("__biz") or payload.get("mpBiz"),
            "fakeid": payload.get("fakeid") or payload.get("fakeId"),
            "name": payload.get("nickname") or payload.get("name") or payload.get("title"),
            "avatar_url": payload.get("avatar") or payload.get("avatar_url") or payload.get("headImg"),
            "mp_intro": payload.get("intro") or payload.get("description") or payload.get("signature"),
            "raw": payload,
            "resolve_source": "weread_platform",
        }

    async def resolve_with_mp_admin_searchbiz(self, owner_user_id, query: str | None) -> dict:
        """Fallback resolver that uses a healthy MP admin account and searchbiz."""
        if not query:
            return {}
        accounts = await self.collector_repo.get_by_owner_and_type(owner_user_id, CollectorAccountType.MP_ADMIN)
        healthy = [
            account for account in accounts
            if account.status == CollectorAccountStatus.ACTIVE
            and account.health_status == CollectorHealthStatus.NORMAL
            and not (account.metadata_json or {}).get("fakeid_missing_blocked")
        ]
        for account in healthy:
            credentials = account.credentials or {}
            token = credentials.get("token")
            cookies = credentials.get("cookies") or {}
            if not token or not cookies:
                continue
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(
                        "https://mp.weixin.qq.com/cgi-bin/searchbiz",
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
                        cookies=cookies,
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception:
                continue
            entries = payload.get("list") or payload.get("data", {}).get("list") or []
            if isinstance(entries, dict):
                entries = entries.get("list", [])
            if not entries:
                continue
            first = entries[0]
            return {
                "fakeid": first.get("fakeid") or first.get("fakeId"),
                "name": first.get("nickname") or first.get("nick_name") or first.get("name"),
                "avatar_url": first.get("round_head_img") or first.get("head_img") or first.get("avatar"),
                "mp_intro": first.get("signature") or first.get("intro"),
                "raw": first,
                "resolve_source": "mp_admin_searchbiz",
            }
        return {}

    async def create_from_url(self, owner_user_id, source_url: str, name: str | None = None, fakeid: str | None = None):
        parsed = self.parse_source_url(source_url)
        resolved = await self.resolve_with_weread_platform(source_url)
        if not resolved.get("fakeid"):
            fallback = await self.resolve_with_mp_admin_searchbiz(owner_user_id, name or resolved.get("name"))
            if fallback:
                merged_raw = {
                    "weread_platform": resolved.get("raw"),
                    "mp_admin_searchbiz": fallback.get("raw"),
                }
                resolved = {**resolved, **{k: v for k, v in fallback.items() if v}, "raw": merged_raw}
        if resolved.get("biz"):
            parsed["biz"] = str(resolved["biz"]).replace("u__", "")
        existing = await self.repo.get_by_owner_and_biz(owner_user_id, parsed["biz"])
        if existing:
            return existing, False

        policy = await self.system_config_service.get_or_create_fetch_policy()
        default_tier = 3
        fetch_mode = CollectorAccountType(policy.primary_modes.get(str(default_tier), "mp_admin"))

        resolved_fakeid = fakeid or resolved.get("fakeid")
        capabilities = {
            "list_fetch": bool(resolved_fakeid),
            "detail_fetch": True,
            "detail_only": not bool(resolved_fakeid),
        }
        metadata = {
            "raw": resolved.get("raw") if resolved else None,
            "resolve_source": resolved.get("resolve_source") if resolved else None,
            "resolve_error": None if resolved_fakeid else "fakeid_unavailable",
            "capabilities": capabilities,
        }
        monitored = await self.repo.create(
            owner_user_id=owner_user_id,
            biz=parsed["biz"],
            fakeid=resolved_fakeid,
            name=name or resolved.get("name") or f"公众号 {parsed['biz'][-6:]}",
            source_url=source_url,
            avatar_url=resolved.get("avatar_url"),
            mp_intro=resolved.get("mp_intro"),
            metadata_json=metadata,
            current_tier=default_tier,
            composite_score=50.0,
            primary_fetch_mode=fetch_mode,
            fallback_fetch_mode=None,
            last_polled_at=None,
            last_published_at=None,
            next_scheduled_at=datetime.now(timezone.utc) + timedelta(hours=int(policy.check_intervals.get("3", 72))),
            strategy_config={
                "source_query": parsed,
                "capabilities": capabilities,
            },
        )
        return monitored, True

    async def update(self, monitored: MonitoredAccount, **kwargs) -> MonitoredAccount:
        if "target_tier" in kwargs and kwargs["target_tier"] is not None:
            next_tier = kwargs.pop("target_tier")
            kwargs["current_tier"] = next_tier
            kwargs["primary_fetch_mode"] = await self.fetch_mode_for_tier(next_tier)
            kwargs["fallback_fetch_mode"] = None
        return await self.repo.update(monitored, **kwargs)
