"""User-related Pydantic schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """Application roles."""

    patient = "patient"
    doctor = "doctor"
    caregiver = "caregiver"


class UserCreate(BaseModel):
    """Register payload."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.patient
    language: str = Field(default="Hindi", max_length=64)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("password")
    @classmethod
    def password_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes (bcrypt limit).")
        return value


class UserLogin(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Profile update payload (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    language: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)


class UserResponse(BaseModel):
    """Serialized user (no secrets)."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    language: str
    phone: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT envelope with embedded user."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
