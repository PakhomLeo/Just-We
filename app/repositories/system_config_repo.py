"""Repositories for singleton system configs."""

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import AIAnalysisConfig, FetchPolicy, NotificationEmailConfig


class AIAnalysisConfigRepository:
    """Repository for singleton AI config."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_first(self) -> AIAnalysisConfig | None:
        result = await self.db.execute(Select(AIAnalysisConfig).limit(1))
        return result.scalar_one_or_none()


class FetchPolicyRepository:
    """Repository for singleton fetch policy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_first(self) -> FetchPolicy | None:
        result = await self.db.execute(Select(FetchPolicy).limit(1))
        return result.scalar_one_or_none()


class NotificationEmailConfigRepository:
    """Repository for singleton notification email config."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_first(self) -> NotificationEmailConfig | None:
        result = await self.db.execute(Select(NotificationEmailConfig).limit(1))
        return result.scalar_one_or_none()
