import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import OperationLog
from app.repositories.base import BaseRepository


class LogRepository(BaseRepository):
    """Repository for OperationLog model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(OperationLog, db)

    async def get_by_target(
        self,
        target_type: str,
        target_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OperationLog]:
        """Get logs by target type and ID."""
        result = await self.db.execute(
            Select(OperationLog)
            .where(
                and_(
                    OperationLog.target_type == target_type,
                    OperationLog.target_id == target_id,
                )
            )
            .order_by(desc(OperationLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OperationLog]:
        """Get logs by user ID."""
        result = await self.db.execute(
            Select(OperationLog)
            .where(OperationLog.user_id == user_id)
            .order_by(desc(OperationLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OperationLog]:
        """Get logs by action type."""
        result = await self.db.execute(
            Select(OperationLog)
            .where(OperationLog.action == action)
            .order_by(desc(OperationLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        target_type: str,
        target_id: int,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        detail: str | None = None,
    ) -> OperationLog:
        """Create a new operation log entry."""
        return await self.create(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_state=before_state,
            after_state=after_state,
            detail=detail,
        )

    async def get_recent_logs(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OperationLog]:
        """Get recent logs within specified hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            Select(OperationLog)
            .where(OperationLog.created_at >= cutoff)
            .order_by(desc(OperationLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        action: str | None = None,
        target_type: str | None = None,
    ) -> list[OperationLog]:
        """Get paginated logs with SQL-level filters."""
        query = Select(OperationLog)

        if action is not None:
            query = query.where(OperationLog.action == action)
        if target_type is not None:
            query = query.where(OperationLog.target_type == target_type)

        result = await self.db.execute(
            query.order_by(desc(OperationLog.created_at)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_filtered_count(
        self,
        action: str | None = None,
        target_type: str | None = None,
    ) -> int:
        """Get log count with SQL-level filters."""
        query = Select(func.count()).select_from(OperationLog)

        if action is not None:
            query = query.where(OperationLog.action == action)
        if target_type is not None:
            query = query.where(OperationLog.target_type == target_type)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_count_by_target(
        self,
        target_type: str,
        target_id: int,
    ) -> int:
        """Get total log count for a specific target."""
        result = await self.db.execute(
            Select(func.count())
            .select_from(OperationLog)
            .where(
                and_(
                    OperationLog.target_type == target_type,
                    OperationLog.target_id == target_id,
                )
            )
        )
        return result.scalar_one()
