"""Service for monitored source creation and management."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collector_account import CollectorAccountType
from app.models.monitored_account import MonitoredAccount
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.system_config_service import SystemConfigService


class MonitoringSourceService:
    """Manage monitored public accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MonitoredAccountRepository(db)
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

    async def create_from_url(self, owner_user_id, source_url: str, name: str | None = None, fakeid: str | None = None):
        parsed = self.parse_source_url(source_url)
        existing = await self.repo.get_by_owner_and_biz(owner_user_id, parsed["biz"])
        if existing:
            return existing, False

        policy = await self.system_config_service.get_or_create_fetch_policy()
        default_tier = 3
        primary_mode = CollectorAccountType(policy.primary_modes.get(str(default_tier), "mp_admin"))
        fallback_mode = (
            CollectorAccountType.WEREAD if primary_mode == CollectorAccountType.MP_ADMIN else CollectorAccountType.MP_ADMIN
        )

        monitored = await self.repo.create(
            owner_user_id=owner_user_id,
            biz=parsed["biz"],
            fakeid=fakeid or f"fakeid_{parsed['biz'][-8:]}",
            name=name or f"公众号 {parsed['biz'][-6:]}",
            source_url=source_url,
            current_tier=default_tier,
            composite_score=50.0,
            primary_fetch_mode=primary_mode,
            fallback_fetch_mode=fallback_mode,
            last_polled_at=None,
            last_published_at=None,
            next_scheduled_at=datetime.now(timezone.utc) + timedelta(hours=int(policy.check_intervals.get("3", 72))),
            strategy_config={"source_query": parsed},
        )
        return monitored, True

    async def update(self, monitored: MonitoredAccount, **kwargs) -> MonitoredAccount:
        if "target_tier" in kwargs and kwargs["target_tier"] is not None:
            kwargs["current_tier"] = kwargs.pop("target_tier")
        return await self.repo.update(monitored, **kwargs)
