"""Authentication and user account service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.health_profile import HealthProfile
from models.user import User
from schemas.health_profile import HealthProfileResponse, HealthProfileUpdate
from schemas.user import TokenResponse, UserCreate, UserResponse, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """JWT + bcrypt user operations."""

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def _create_access_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload: dict[str, str | datetime] = {
            "sub": str(user_id),
            "exp": expire,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    async def create_user(self, db: AsyncSession, data: UserCreate) -> UserResponse:
        """Register a new user with empty health profile."""
        email_norm = str(data.email).strip().lower()
        existing = await db.execute(select(User).where(User.email == email_norm))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            name=data.name.strip(),
            email=email_norm,
            hashed_password=self._hash_password(data.password),
            role=data.role.value,
            language=data.language,
            phone=data.phone.strip() if data.phone else None,
        )
        db.add(user)
        try:
            await db.flush()
            profile = HealthProfile(user_id=user.id)
            db.add(profile)
            await db.commit()
            await db.refresh(user)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            ) from exc
        except Exception:
            await db.rollback()
            raise
        return UserResponse.model_validate(user)

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        """Validate credentials and return JWT + user."""
        email_norm = email.strip().lower()
        result = await db.execute(select(User).where(User.email == email_norm))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not self._verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        token = self._create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def get_current_user(self, db: AsyncSession, token: str) -> UserResponse:
        """Decode JWT and return the active user."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub = payload.get("sub")
            if sub is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            user_id = uuid.UUID(str(sub))
        except (JWTError, ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            ) from None

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return UserResponse.model_validate(user)

    async def update_user(self, db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> UserResponse:
        """Update profile fields for the given user."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updates = data.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"] is not None:
            user.name = updates["name"].strip()
        if "language" in updates and updates["language"] is not None:
            user.language = updates["language"]
        if "phone" in updates:
            user.phone = updates["phone"].strip() if updates["phone"] else None

        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    async def get_health_profile(self, db: AsyncSession, user_id: uuid.UUID) -> HealthProfileResponse:
        """Return health profile, creating an empty row if missing."""
        result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = HealthProfile(user_id=user_id)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        return HealthProfileResponse.model_validate(profile)

    async def update_health_profile(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: HealthProfileUpdate,
    ) -> HealthProfileResponse:
        """Update health profile fields for the user."""
        result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = HealthProfile(user_id=user_id)
            db.add(profile)
            await db.flush()

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(profile)
        return HealthProfileResponse.model_validate(profile)
