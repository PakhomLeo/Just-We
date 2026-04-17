"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User


settings = get_settings()
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    from app.services.auth_service import AuthService

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_token(credentials.credentials)

    if user is None:
        raise UnauthorizedException("Invalid or expired token")

    if not user.is_active:
        raise UnauthorizedException("User account is disabled")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """Dependency factory for role-based access control."""

    async def _role_check(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized for this action",
            )
        return current_user

    return _role_check


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]

# Role-based dependencies
AdminUser = Annotated[User, Depends(require_role(["admin"]))]
OperatorUser = Annotated[User, Depends(require_role(["admin", "operator"]))]
AnyUser = Annotated[User, Depends(get_current_active_user)]
