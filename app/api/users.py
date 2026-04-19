"""User management API routes (admin only)."""

from fastapi import APIRouter, HTTPException, status, Query

from app.core.config import get_settings
from app.core.dependencies import DbSession, AdminUser
from app.schemas.auth import UserResponse, RegisterRequest, UserUpdate
from app.services.auth_service import AuthService
from app.models.user import UserRole


router = APIRouter(prefix="/users", tags=["Users"])
settings = get_settings()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: DbSession,
    current_user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get all users (admin only)."""
    from app.repositories.user_repo import UserRepository
    user_repo = UserRepository(db)
    users = await user_repo.get_all(skip=(page - 1) * page_size, limit=page_size)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: RegisterRequest,
    db: DbSession,
    current_user: AdminUser,
):
    """Create a new user (admin only)."""
    auth_service = AuthService(db)

    # Check if user exists
    existing = await auth_service.user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if request.username:
        if request.username == settings.default_admin_alias:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is reserved",
            )
        existing_username = await auth_service.user_repo.get_by_username(request.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

    # Create user
    user = await auth_service.create_user(
        email=request.email,
        password=request.password,
        role=request.role.value,
        username=request.username,
    )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    db: DbSession,
    current_user: AdminUser,
):
    """Update a user (admin only)."""
    from uuid import UUID
    from app.repositories.user_repo import UserRepository

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_uuid(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update user fields if provided
    if request.email is not None:
        user.email = request.email
    if request.username is not None:
        if request.username:
            if request.username == settings.default_admin_alias and user.username != settings.default_admin_alias:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is reserved")
            existing_username = await user_repo.get_by_username(request.username)
            if existing_username and existing_username.id != user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
            user.username = request.username
        else:
            user.username = None
    if request.password:
        user.hashed_password = AuthService(db).hash_password(request.password)
    if request.role is not None:
        user.role = UserRole(request.role.value)
    if request.is_active is not None:
        user.is_active = request.is_active

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: DbSession,
    current_user: AdminUser,
):
    """Get user by ID (admin only)."""
    from uuid import UUID
    from app.repositories.user_repo import UserRepository
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_uuid(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: DbSession,
    current_user: AdminUser,
):
    """Delete user (admin only)."""
    from uuid import UUID
    from app.repositories.user_repo import UserRepository
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_uuid(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user_repo.delete(user)
