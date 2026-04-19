"""Service for collector account management."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collector_account import (
    CollectorAccount,
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)
from app.repositories.collector_account_repo import CollectorAccountRepository


class CollectorAccountService:
    """Manage bound collection credentials."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CollectorAccountRepository(db)

    async def list_visible(self, current_user, include_all: bool = False) -> list[CollectorAccount]:
        owner_user_id = None if include_all and current_user.role.value == "admin" else current_user.id
        return await self.repo.get_visible_accounts(owner_user_id)

    async def get(self, collector_account_id: int) -> CollectorAccount | None:
        return await self.repo.get_by_id(collector_account_id)

    async def get_visible(self, collector_account_id: int, current_user) -> CollectorAccount | None:
        account = await self.get(collector_account_id)
        if account is None:
            return None
        if current_user.role.value == "admin" or account.owner_user_id == current_user.id:
            return account
        return None

    async def create_bound_account(
        self,
        owner_user_id,
        account_type: CollectorAccountType,
        display_name: str,
        credentials: dict,
        external_id: str | None = None,
        expires_at=None,
        metadata_json: dict | None = None,
        login_proxy_id: int | None = None,
        last_login_proxy_ip: str | None = None,
    ) -> CollectorAccount:
        return await self.repo.create(
            owner_user_id=owner_user_id,
            account_type=account_type,
            display_name=display_name,
            external_id=external_id,
            credentials=credentials,
            expires_at=expires_at,
            metadata_json=metadata_json or {},
            login_proxy_id=login_proxy_id,
            login_proxy_locked=True,
            last_login_proxy_ip=last_login_proxy_ip,
            login_proxy_changed_at=datetime.now(timezone.utc) if login_proxy_id else None,
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            cool_until=None,
            last_error_category=None,
            last_success_at=datetime.now(timezone.utc),
        )

    async def upsert_bound_account(
        self,
        owner_user_id,
        account_type: CollectorAccountType,
        display_name: str,
        credentials: dict,
        external_id: str | None = None,
        expires_at=None,
        metadata_json: dict | None = None,
        login_proxy_id: int | None = None,
        last_login_proxy_ip: str | None = None,
    ) -> CollectorAccount:
        if external_id:
            existing = await self.repo.get_by_owner_type_and_external_id(owner_user_id, account_type, external_id)
            if existing is not None:
                return await self.repo.update(
                    existing,
                    display_name=display_name,
                    credentials=credentials,
                    expires_at=expires_at,
                    metadata_json=metadata_json or existing.metadata_json,
                    login_proxy_id=login_proxy_id if login_proxy_id is not None else existing.login_proxy_id,
                    login_proxy_locked=True,
                    last_login_proxy_ip=last_login_proxy_ip or existing.last_login_proxy_ip,
                    login_proxy_changed_at=datetime.now(timezone.utc) if login_proxy_id and login_proxy_id != existing.login_proxy_id else existing.login_proxy_changed_at,
                    status=CollectorAccountStatus.ACTIVE,
                    health_status=CollectorHealthStatus.NORMAL,
                    risk_status=RiskStatus.NORMAL,
                    risk_reason=None,
                    cool_until=None,
                    last_error_category=None,
                    last_success_at=datetime.now(timezone.utc),
                )
        return await self.create_bound_account(
            owner_user_id=owner_user_id,
            account_type=account_type,
            display_name=display_name,
            credentials=credentials,
            external_id=external_id,
            expires_at=expires_at,
            metadata_json=metadata_json,
            login_proxy_id=login_proxy_id,
            last_login_proxy_ip=last_login_proxy_ip,
        )

    async def update_account_proxy(self, account: CollectorAccount, proxy_id: int | None) -> CollectorAccount:
        metadata = dict(account.metadata_json or {})
        metadata["account_proxy_changed_at"] = datetime.now(timezone.utc).isoformat()
        metadata.pop("login_proxy_missing", None)
        metadata.pop("login_proxy_missing_reason", None)
        metadata.pop("login_proxy_changed_requires_relogin", None)
        return await self.repo.update(
            account,
            login_proxy_id=proxy_id,
            login_proxy_locked=True,
            last_login_proxy_ip=None,
            login_proxy_changed_at=datetime.now(timezone.utc),
            metadata_json=metadata,
        )

    async def update_login_proxy(self, account: CollectorAccount, login_proxy_id: int | None) -> CollectorAccount:
        return await self.update_account_proxy(account, login_proxy_id)

    async def mark_health(
        self,
        account: CollectorAccount,
        health_status: CollectorHealthStatus,
        message: str | None = None,
    ) -> CollectorAccount:
        update = {
            "health_status": health_status,
            "last_health_check": datetime.now(timezone.utc),
        }
        if health_status == CollectorHealthStatus.NORMAL:
            update["status"] = CollectorAccountStatus.ACTIVE
            update["risk_status"] = RiskStatus.NORMAL
            update["risk_reason"] = None
            update["cool_until"] = None
            update["last_error_category"] = None
            update["last_success_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.RESTRICTED:
            update["status"] = CollectorAccountStatus.ERROR
            update["risk_status"] = RiskStatus.BLOCKED
            update["last_error_category"] = "risk_control"
            update["last_failure_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.EXPIRED:
            update["status"] = CollectorAccountStatus.EXPIRED
            update["risk_status"] = RiskStatus.NORMAL
            update["last_error_category"] = "credentials_invalid"
            update["last_failure_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.INVALID:
            update["status"] = CollectorAccountStatus.ERROR
            update["risk_status"] = RiskStatus.NORMAL
            update["last_error_category"] = "configuration_error"
            update["last_failure_at"] = datetime.now(timezone.utc)
        if message:
            update["risk_reason"] = message
        return await self.repo.update(account, **update)

    async def mark_failure(self, account: CollectorAccount, reason: str) -> CollectorAccount:
        return await self.repo.update(
            account,
            last_failure_at=datetime.now(timezone.utc),
            risk_status=RiskStatus.COOLING,
            risk_reason=reason,
            cool_until=datetime.now(timezone.utc) + timedelta(minutes=30),
            last_error_category="temporary_failure",
        )

    async def mark_fetch_failure(
        self,
        account: CollectorAccount,
        category: str,
        reason: str,
    ) -> CollectorAccount:
        now = datetime.now(timezone.utc)
        cooldown_until = now + timedelta(minutes=30)
        if category == "risk_control":
            tomorrow = (now + timedelta(days=1)).date()
            cooldown_until = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
        update = {
            "last_failure_at": datetime.now(timezone.utc),
            "risk_reason": reason,
            "last_error_category": category,
        }
        if category == "credentials_invalid":
            update["status"] = CollectorAccountStatus.EXPIRED
            update["health_status"] = CollectorHealthStatus.EXPIRED
            update["risk_status"] = RiskStatus.NORMAL
            update["cool_until"] = None
        elif category == "configuration_error":
            update["status"] = CollectorAccountStatus.ERROR
            update["health_status"] = CollectorHealthStatus.INVALID
            update["risk_status"] = RiskStatus.NORMAL
            update["cool_until"] = None
        elif category == "risk_control":
            update["status"] = CollectorAccountStatus.ERROR
            update["health_status"] = CollectorHealthStatus.RESTRICTED
            update["risk_status"] = RiskStatus.BLOCKED
            update["cool_until"] = cooldown_until
        else:
            update["risk_status"] = RiskStatus.COOLING
            update["cool_until"] = cooldown_until
        return await self.repo.update(account, **update)

    async def mark_success(self, account: CollectorAccount) -> CollectorAccount:
        return await self.repo.update(
            account,
            last_success_at=datetime.now(timezone.utc),
            risk_status=RiskStatus.NORMAL,
            risk_reason=None,
            cool_until=None,
            last_error_category=None,
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
        )

    async def update_discovered_profile(
        self,
        account: CollectorAccount,
        profile: dict,
    ) -> CollectorAccount:
        credentials = dict(account.credentials or {})
        metadata = dict(account.metadata_json or {})
        if profile.get("cookies"):
            credentials["cookies"] = profile["cookies"]
            credentials["cookie"] = "; ".join(f"{key}={value}" for key, value in profile["cookies"].items())
        if profile.get("fakeid"):
            credentials["fakeid"] = profile["fakeid"]
            metadata["fakeid"] = profile["fakeid"]
            metadata["fakeid_missing"] = False
        else:
            metadata["fakeid_missing"] = True
        if profile.get("nickname"):
            credentials["nickname"] = profile["nickname"]
            metadata["nickname"] = profile["nickname"]
        metadata["profile"] = profile
        return await self.repo.update(
            account,
            display_name=profile.get("nickname") or account.display_name,
            credentials=credentials,
            metadata_json=metadata,
            last_error_category=None if profile.get("fakeid") else "fakeid_missing",
        )

    def is_available_for_fetch(self, account: CollectorAccount) -> bool:
        if account.status != CollectorAccountStatus.ACTIVE:
            return False
        if account.health_status != CollectorHealthStatus.NORMAL:
            return False
        credentials = account.credentials or {}
        if account.account_type == CollectorAccountType.MP_ADMIN:
            if not credentials.get("token") or not (credentials.get("cookies") or credentials.get("cookie")):
                return False
        elif account.account_type == CollectorAccountType.WEREAD:
            if not (credentials.get("token") or credentials.get("cookies")):
                return False
        cool_until = account.cool_until
        if cool_until is None:
            return True
        if cool_until.tzinfo is None:
            cool_until = cool_until.replace(tzinfo=timezone.utc)
        return cool_until <= datetime.now(timezone.utc)
