"""Account repository for database operations."""

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Row

from app.models.account import Account, AccountStatus, AccountType
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository):
    """Repository for Account model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Account, db)

    async def get_by_biz(self, biz: str) -> Account | None:
        """Get account by biz identifier."""
        result = await self.db.execute(
            Select(Account).where(Account.biz == biz)
        )
        return result.scalar_one_or_none()

    async def get_active_accounts(self) -> list[Account]:
        """Get all active accounts."""
        result = await self.db.execute(
            Select(Account).where(Account.status == AccountStatus.ACTIVE)
        )
        return list(result.scalars().all())

    async def get_accounts_by_tier(self, tier: int) -> list[Account]:
        """Get all accounts with specific tier."""
        result = await self.db.execute(
            Select(Account).where(
                and_(
                    Account.current_tier == tier,
                    Account.status == AccountStatus.ACTIVE,
                )
            )
        )
        return list(result.scalars().all())

    async def get_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        status: AccountStatus | None = None,
        tier: int | None = None,
    ) -> Sequence[Account]:
        """Get paginated accounts with optional filters applied in SQL."""
        query = Select(Account)

        if status is not None:
            query = query.where(Account.status == status)
        if tier is not None:
            query = query.where(Account.current_tier == tier)

        result = await self.db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_filtered_count(
        self,
        status: AccountStatus | None = None,
        tier: int | None = None,
    ) -> int:
        """Get account count with optional filters applied in SQL."""
        query = Select(func.count()).select_from(Account)

        if status is not None:
            query = query.where(Account.status == status)
        if tier is not None:
            query = query.where(Account.current_tier == tier)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_score_and_tier(
        self,
        account: Account,
        new_score: float,
        new_tier: int,
    ) -> Account:
        """Update account score and tier."""
        return await self.update(
            account,
            composite_score=new_score,
            current_tier=new_tier,
        )

    async def update_last_checked(self, account: Account) -> Account:
        """Update last_checked timestamp."""
        return await self.update(account, last_checked=datetime.now(timezone.utc))

    async def update_last_updated(self, account: Account) -> Account:
        """Update last_updated timestamp."""
        return await self.update(account, last_updated=datetime.now(timezone.utc))

    async def update_history(
        self,
        account: Account,
        update_history: dict,
        ai_relevance_history: dict,
    ) -> Account:
        """Update account history records."""
        return await self.update(
            account,
            update_history=update_history,
            ai_relevance_history=ai_relevance_history,
        )

    async def set_manual_override(
        self,
        account: Account,
        manual_override: dict | None,
    ) -> Account:
        """Set or clear manual override."""
        return await self.update(account, manual_override=manual_override)

    async def get_all(self) -> list[Account]:
        """Get all accounts."""
        result = await self.db.execute(Select(Account))
        return list(result.scalars().all())

    async def get_by_type(self, account_type: AccountType) -> list[Account]:
        """Get accounts by type."""
        result = await self.db.execute(
            Select(Account).where(Account.account_type == account_type)
        )
        return list(result.scalars().all())
