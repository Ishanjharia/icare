"""Prescription Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionCreate(BaseModel):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    doctor_name: str | None = Field(default=None, max_length=255)
    medication: str = Field(..., max_length=255)
    dosage: str = Field(..., max_length=255)
    instructions: str
    language: str = Field(default="en", max_length=16)
    translated_text: str | None = None


class PrescriptionUpdate(BaseModel):
    doctor_id: uuid.UUID | None = None
    medication: str | None = Field(default=None, max_length=255)
    dosage: str | None = Field(default=None, max_length=255)
    instructions: str | None = None
    language: str | None = Field(default=None, max_length=16)
    translated_text: str | None = None


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    medication: str
    dosage: str
    instructions: str
    language: str
    translated_text: str | None
    created_at: datetime
