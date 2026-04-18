"""Repository for singleton weight config."""

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weight_config import WeightConfig


class WeightConfigRepository:
    """Repository for persisted weight configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_first(self) -> WeightConfig | None:
        result = await self.db.execute(Select(WeightConfig).limit(1))
        return result.scalar_one_or_none()
