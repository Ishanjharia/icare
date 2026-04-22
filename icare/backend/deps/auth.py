"""Authentication dependencies — file-backed user store; Bearer token = email."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from schemas.user import UserResponse, UserRole
from simple_auth_store import user_for_email_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> UserResponse:
    """Require a Bearer token (email) that matches a saved user."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_for_email_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unknown token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


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
