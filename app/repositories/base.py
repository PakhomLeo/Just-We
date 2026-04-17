"""Base repository class for common database operations."""

from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Row

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: int) -> ModelType | None:
        """Get a single record by ID."""
        result = await self.db.execute(
            Select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Get all records with pagination."""
        result = await self.db.execute(
            Select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_count(self) -> int:
        """Get total count of records."""
        result = await self.db.execute(
            Select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """Update an existing record."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        await self.db.delete(instance)
        await self.db.flush()

    async def save(self, instance: ModelType) -> ModelType:
        """Save an instance (create or update)."""
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
