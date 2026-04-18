"""Repository for monitored public accounts."""

import uuid

from sqlalchemy import Select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.repositories.base import BaseRepository


class MonitoredAccountRepository(BaseRepository):
    """CRUD helpers for monitored accounts."""

    def __init__(self, db: AsyncSession):
        super().__init__(MonitoredAccount, db)

    async def get_by_biz(self, biz: str) -> MonitoredAccount | None:
        result = await self.db.execute(Select(MonitoredAccount).where(MonitoredAccount.biz == biz))
        return result.scalar_one_or_none()

    async def get_by_feed_token(self, feed_token: str) -> MonitoredAccount | None:
        result = await self.db.execute(Select(MonitoredAccount).where(MonitoredAccount.feed_token == feed_token))
        return result.scalar_one_or_none()

    async def get_by_owner_and_biz(
        self,
        owner_user_id: uuid.UUID,
        biz: str,
    ) -> MonitoredAccount | None:
        result = await self.db.execute(
            Select(MonitoredAccount).where(
                and_(
                    MonitoredAccount.owner_user_id == owner_user_id,
                    MonitoredAccount.biz == biz,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_visible_accounts(self, owner_user_id: uuid.UUID | None = None) -> list[MonitoredAccount]:
        query = Select(MonitoredAccount).order_by(MonitoredAccount.created_at.desc())
        if owner_user_id is not None:
            query = query.where(MonitoredAccount.owner_user_id == owner_user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_accounts(self) -> list[MonitoredAccount]:
        result = await self.db.execute(
            Select(MonitoredAccount).where(MonitoredAccount.status == MonitoredAccountStatus.MONITORING)
        )
        return list(result.scalars().all())

    async def get_count_for_user(self, owner_user_id: uuid.UUID | None = None) -> int:
        query = Select(func.count()).select_from(MonitoredAccount)
        if owner_user_id is not None:
            query = query.where(MonitoredAccount.owner_user_id == owner_user_id)
        result = await self.db.execute(query)
        return result.scalar_one()
