"""Repository for collector accounts."""

import uuid

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collector_account import CollectorAccount, CollectorAccountType
from app.repositories.base import BaseRepository


class CollectorAccountRepository(BaseRepository):
    """CRUD helpers for collector accounts."""

    def __init__(self, db: AsyncSession):
        super().__init__(CollectorAccount, db)

    async def get_visible_accounts(self, owner_user_id: uuid.UUID | None = None) -> list[CollectorAccount]:
        query = Select(CollectorAccount).order_by(CollectorAccount.created_at.desc())
        if owner_user_id is not None:
            query = query.where(CollectorAccount.owner_user_id == owner_user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_owner_and_type(
        self,
        owner_user_id: uuid.UUID,
        account_type: CollectorAccountType,
    ) -> list[CollectorAccount]:
        result = await self.db.execute(
            Select(CollectorAccount)
            .where(
                CollectorAccount.owner_user_id == owner_user_id,
                CollectorAccount.account_type == account_type,
            )
            .order_by(CollectorAccount.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_owner_type_and_external_id(
        self,
        owner_user_id: uuid.UUID,
        account_type: CollectorAccountType,
        external_id: str,
    ) -> CollectorAccount | None:
        result = await self.db.execute(
            Select(CollectorAccount).where(
                CollectorAccount.owner_user_id == owner_user_id,
                CollectorAccount.account_type == account_type,
                CollectorAccount.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()
