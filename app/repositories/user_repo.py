"""User repository for database operations."""

from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            Select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id_uuid(self, id: UUID) -> User | None:
        """Get user by UUID."""
        result = await self.db.execute(
            Select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def update_last_login(self, user: User) -> User:
        """Update user's last login timestamp."""
        from datetime import datetime, timezone

        return await self.update(user, last_login=datetime.now(timezone.utc))
