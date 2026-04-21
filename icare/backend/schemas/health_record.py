"""Health record Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthRecordBody(BaseModel):
    """Create health record when ``patient_id`` comes from the URL path."""

    record_type: str = Field(..., max_length=64)
    description: str
    language: str = Field(default="en", max_length=32)
    report_data: dict[str, Any] | None = None
    vitals_snapshot: dict[str, Any] | None = None


class HealthRecordCreate(BaseModel):
    """Create health record payload (includes patient for internal callers)."""

    patient_id: uuid.UUID
    record_type: str = Field(..., max_length=64)
    description: str
    language: str = Field(default="en", max_length=32)
    report_data: dict[str, Any] | None = None
    vitals_snapshot: dict[str, Any] | None = None


class HealthRecordResponse(BaseModel):
    """Serialized health record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: uuid.UUID
    record_type: str
    description: str
    language: str
    report_data: dict[str, Any] | None
    vitals_snapshot: dict[str, Any] | None
    created_at: datetime
