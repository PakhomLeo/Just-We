"""Account service for business logic."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountStatus, AccountType
from app.repositories.account_repo import AccountRepository
from app.core.exceptions import AccountNotFoundException


class AccountService:
    """Service for account management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = AccountRepository(db)

    async def get_account(self, account_id: int) -> Account:
        """Get account by ID."""
        account = await self.account_repo.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundException(account_id)
        return account

    async def get_account_by_biz(self, biz: str) -> Account | None:
        """Get account by biz identifier."""
        return await self.account_repo.get_by_biz(biz)

    async def get_active_accounts(self) -> list[Account]:
        """Get all active accounts."""
        return await self.account_repo.get_active_accounts()

    async def get_accounts_by_tier(self, tier: int) -> list[Account]:
        """Get accounts by tier."""
        return await self.account_repo.get_accounts_by_tier(tier)

    async def create_account(
        self,
        biz: str,
        fakeid: str,
        name: str,
        account_type: str = "mp",
        cookies: dict | None = None,
    ) -> Account:
        """Create a new account."""
        return await self.account_repo.create(
            biz=biz,
            fakeid=fakeid,
            name=name,
            account_type=account_type,
            cookies=cookies,
            status=AccountStatus.ACTIVE,
            current_tier=3,  # Default tier
            composite_score=50.0,  # Default score
            update_history={},
            ai_relevance_history={},
        )

    async def update_account(
        self,
        account_id: int,
        **kwargs: Any,
    ) -> Account:
        """Update an account."""
        account = await self.get_account(account_id)
        return await self.account_repo.update(account, **kwargs)

    async def delete_account(self, account_id: int) -> None:
        """Delete an account."""
        account = await self.get_account(account_id)
        await self.account_repo.delete(account)

    async def apply_manual_override(
        self,
        account_id: int,
        target_tier: int,
        reason: str,
        expire_at: datetime | None = None,
    ) -> Account:
        """Apply manual tier override to an account."""
        account = await self.get_account(account_id)

        if expire_at is None:
            expire_at = datetime.now(timezone.utc) + timedelta(hours=24)

        manual_override = {
            "target_tier": target_tier,
            "reason": reason,
            "expire_at": expire_at.isoformat(),
        }

        return await self.account_repo.set_manual_override(account, manual_override)

    async def clear_manual_override(self, account_id: int) -> Account:
        """Clear manual override from an account."""
        account = await self.get_account(account_id)
        return await self.account_repo.set_manual_override(account, None)

    async def update_score_and_tier(
        self,
        account: Account,
        new_score: float,
        new_tier: int,
    ) -> Account:
        """Update account score and tier."""
        return await self.account_repo.update_score_and_tier(
            account, new_score, new_tier
        )

    async def update_last_checked(self, account: Account) -> Account:
        """Update last checked timestamp."""
        return await self.account_repo.update_last_checked(account)

    async def update_last_updated(self, account: Account) -> Account:
        """Update last updated timestamp."""
        return await self.account_repo.update_last_updated(account)

    async def update_histories(
        self,
        account: Account,
        update_history: dict,
        ai_relevance_history: dict,
    ) -> Account:
        """Update account histories."""
        return await self.account_repo.update_history(
            account, update_history, ai_relevance_history
        )

    async def get_account_history(self, account_id: int) -> dict[str, Any]:
        """Get account history for display."""
        account = await self.get_account(account_id)

        # Extract tier changes from logs
        tier_changes = []
        # TODO: Implement tier change extraction from operation logs

        return {
            "update_history": account.update_history,
            "ai_relevance_history": account.ai_relevance_history,
            "tier_changes": tier_changes,
            "manual_overrides": [account.manual_override]
            if account.manual_override
            else [],
        }

    async def get_accounts_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: AccountStatus | None = None,
        tier: int | None = None,
    ) -> tuple[list[Account], int]:
        """Get paginated accounts with filters."""
        accounts = await self.account_repo.get_paginated(
            skip=(page - 1) * page_size,
            limit=page_size,
            status=status,
            tier=tier,
        )
        total = await self.account_repo.get_filtered_count(status=status, tier=tier)
        return list(accounts), total

    async def get_all_accounts(self) -> list[Account]:
        """Get all accounts."""
        return await self.account_repo.get_all()

    async def get_accounts_by_type(self, account_type: str) -> list[Account]:
        """Get accounts by type."""
        return await self.account_repo.get_by_type(AccountType(account_type))
