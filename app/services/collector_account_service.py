"""Service for collector account management."""

from datetime import datetime, timezone

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
    ) -> CollectorAccount:
        return await self.repo.create(
            owner_user_id=owner_user_id,
            account_type=account_type,
            display_name=display_name,
            external_id=external_id,
            credentials=credentials,
            expires_at=expires_at,
            metadata_json=metadata_json or {},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
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
                    status=CollectorAccountStatus.ACTIVE,
                    health_status=CollectorHealthStatus.NORMAL,
                    risk_status=RiskStatus.NORMAL,
                    risk_reason=None,
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
        )

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
            update["last_success_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.RESTRICTED:
            update["status"] = CollectorAccountStatus.ERROR
            update["risk_status"] = RiskStatus.BLOCKED
            update["last_failure_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.EXPIRED:
            update["status"] = CollectorAccountStatus.EXPIRED
            update["risk_status"] = RiskStatus.NORMAL
            update["last_failure_at"] = datetime.now(timezone.utc)
        elif health_status == CollectorHealthStatus.INVALID:
            update["status"] = CollectorAccountStatus.ERROR
            update["risk_status"] = RiskStatus.NORMAL
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
        )

    async def mark_fetch_failure(
        self,
        account: CollectorAccount,
        category: str,
        reason: str,
    ) -> CollectorAccount:
        update = {
            "last_failure_at": datetime.now(timezone.utc),
            "risk_reason": reason,
        }
        if category == "credentials_invalid":
            update["status"] = CollectorAccountStatus.EXPIRED
            update["health_status"] = CollectorHealthStatus.EXPIRED
            update["risk_status"] = RiskStatus.NORMAL
        elif category == "configuration_error":
            update["status"] = CollectorAccountStatus.ERROR
            update["health_status"] = CollectorHealthStatus.INVALID
            update["risk_status"] = RiskStatus.NORMAL
        elif category == "risk_control":
            update["status"] = CollectorAccountStatus.ERROR
            update["health_status"] = CollectorHealthStatus.RESTRICTED
            update["risk_status"] = RiskStatus.BLOCKED
        else:
            update["risk_status"] = RiskStatus.COOLING
        return await self.repo.update(account, **update)

    async def mark_success(self, account: CollectorAccount) -> CollectorAccount:
        return await self.repo.update(
            account,
            last_success_at=datetime.now(timezone.utc),
            risk_status=RiskStatus.NORMAL,
            risk_reason=None,
            status=CollectorAccountStatus.ACTIVE,
        )
