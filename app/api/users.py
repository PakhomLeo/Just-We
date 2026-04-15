"""User management API routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.dependencies import DbSession, CurrentUser, AdminUser
from app.schemas.auth import UserResponse


router = APIRouter(prefix="/users", tags=["Users"])


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
