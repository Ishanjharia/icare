"""Appointment Pydantic schemas."""

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    doctor_name: str | None = Field(default=None, max_length=255)
    appt_date: date
    appt_time: time
    status: str = Field(default="scheduled", max_length=32)
    language: str = Field(default="en", max_length=16)
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    doctor_id: uuid.UUID | None = None
    doctor_name: str | None = Field(default=None, max_length=255)
    appt_date: date | None = None
    appt_time: time | None = None
    status: str | None = Field(default=None, max_length=32)
    language: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    appt_date: date
    appt_time: time
    status: str
    language: str
    notes: str | None
    created_at: datetime
