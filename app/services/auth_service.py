"""Authentication service for JWT token management."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.repositories.user_repo import UserRepository


settings = get_settings()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    """Service for authentication and JWT token management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def create_access_token(
        self,
        user_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )

        to_encode: dict[str, Any] = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError:
            return None

    async def get_user_by_token(self, token: str) -> User | None:
        """Get user from JWT token."""
        payload = self.decode_token(token)
        if payload is None:
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        from uuid import UUID

        try:
            user_uuid = UUID(user_id)
            return await self.user_repo.get_by_id_uuid(user_uuid)
        except (ValueError, AttributeError):
            return None

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate a user by email and password."""
        lookup_email = email
        if email == settings.default_admin_alias:
            lookup_email = settings.default_admin_email
        user = await self.user_repo.get_by_email(lookup_email)
        if user is None:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(
        self,
        email: str,
        password: str,
        role: str = "viewer",
    ) -> User:
        """Create a new user."""
        from app.models.user import UserRole

        hashed_password = self.hash_password(password)
        role_enum = UserRole(role) if isinstance(role, str) else role

        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed_password,
            role=role_enum,
            is_active=True,
        )
        return user

    async def update_last_login(self, user: User) -> User:
        """Update user's last login timestamp."""
        return await self.user_repo.update_last_login(user)
