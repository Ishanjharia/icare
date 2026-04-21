"""Health profile Pydantic schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthProfileResponse(BaseModel):
    """Full health profile row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    blood_type: str | None
    height: str | None
    weight: str | None
    date_of_birth: date | None
    gender: str | None
    allergies: str | None
    chronic_conditions: str | None
    current_medications: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    primary_doctor: str | None
    smoking_status: str | None
    alcohol_status: str | None
    exercise_frequency: str | None
    updated_at: datetime


class HealthProfileUpdate(BaseModel):
    """Partial update for health profile."""

    blood_type: str | None = Field(default=None, max_length=8)
    height: str | None = Field(default=None, max_length=64)
    weight: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=32)
    allergies: str | None = None
    chronic_conditions: str | None = None
    current_medications: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    primary_doctor: str | None = Field(default=None, max_length=255)
    smoking_status: str | None = Field(default=None, max_length=64)
    alcohol_status: str | None = Field(default=None, max_length=64)
    exercise_frequency: str | None = Field(default=None, max_length=64)
