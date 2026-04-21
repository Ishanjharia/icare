"""Authentication dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.user import UserResponse, UserRole
from services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Require a valid Bearer JWT and return the current user."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await AuthService().get_current_user(db, token)


async def require_patient(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Allow only users with the patient role."""
    if user.role != UserRole.patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient role required.",
        )
    return user


async def require_doctor(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Allow only users with the doctor role."""
    if user.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor role required.",
        )
    return user
