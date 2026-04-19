"""Authentication API routes."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, CurrentUser
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, Token, UserResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: DbSession,
):
    """Authenticate user and return JWT token."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Update last login
    await auth_service.update_last_login(user)

    # Create token
    access_token = auth_service.create_access_token(str(user.id))

    return Token(access_token=access_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: DbSession,
):
    """Register a new user."""
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """Get current authenticated user info."""
    return current_user
