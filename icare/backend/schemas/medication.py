"""Medication Pydantic schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MedicationCreate(BaseModel):
    patient_id: uuid.UUID
    name: str = Field(..., max_length=255)
    dosage: str = Field(..., max_length=128)
    frequency: str = Field(..., max_length=128)
    start_date: date | None = None
    end_date: date | None = None
    status: str = Field(default="active", max_length=32)
    notes: str | None = None


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    dosage: str | None = Field(default=None, max_length=128)
    frequency: str | None = Field(default=None, max_length=128)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: uuid.UUID
    name: str
    dosage: str
    frequency: str
    start_date: date | None
    end_date: date | None
    status: str
    notes: str | None
    created_at: datetime
