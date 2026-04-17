"""Startup bootstrap tasks."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import UserRole
from app.services.auth_service import AuthService


settings = get_settings()


class BootstrapService:
    """Provision development defaults on startup."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.auth_service = AuthService(db)

    async def ensure_default_admin(self):
        """Create or repair the default admin account."""
        if not settings.ensure_default_admin:
            return None

        existing = await self.auth_service.user_repo.get_by_email(settings.default_admin_email)
        hashed_password = self.auth_service.hash_password(settings.default_admin_password)
        if existing is None:
            return await self.auth_service.user_repo.create(
                email=settings.default_admin_email,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
            )

        return await self.auth_service.user_repo.update(
            existing,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
        )
