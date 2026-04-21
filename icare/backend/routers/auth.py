"""Authentication routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.health_profile import HealthProfileResponse, HealthProfileUpdate
from schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse, UserUpdate
from services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Create a new account."""
    return await AuthService().create_user(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Issue a JWT (default expiry from ACCESS_TOKEN_EXPIRE_MINUTES, e.g. 24h)."""
    return await AuthService().authenticate(db, str(payload.email), payload.password)


@router.get("/me", response_model=UserResponse)
async def read_me(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile."""
    return current


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Update profile fields for the authenticated user."""
    return await AuthService().update_user(db, current.id, payload)


@router.get("/profile", response_model=HealthProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current: UserResponse = Depends(get_current_user),
) -> HealthProfileResponse:
    """Return the authenticated user's health profile."""
    return await AuthService().get_health_profile(db, current.id)


@router.put("/profile", response_model=HealthProfileResponse)
async def update_profile(
    payload: HealthProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current: UserResponse = Depends(get_current_user),
) -> HealthProfileResponse:
    """Update the authenticated user's health profile."""
    return await AuthService().update_health_profile(db, current.id, payload)
