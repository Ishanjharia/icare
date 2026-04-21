"""Hospital search + saved hospital schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HospitalSearchRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=128)
    specialty: str | None = Field(default=None, max_length=128)
    language: str = Field(default="English", max_length=64)


class HospitalObject(BaseModel):
    """Loose shape for LLM-generated rows (extra keys ignored)."""

    model_config = {"extra": "ignore"}

    name: str = ""
    address: str = ""
    phone: str = ""
    specialties: list[str] = Field(default_factory=list)
    distance_km: float = 0.0
    rating: float = 0.0
    emergency: bool = False
    type: str = ""


class HospitalSearchResponse(BaseModel):
    success: bool
    error: str | None = None
    hospitals: list[dict[str, Any]] = Field(default_factory=list)


class SavedHospitalCreate(BaseModel):
    hospital: dict[str, Any] = Field(..., description="Hospital payload from search (stored as JSON).")


class SavedHospitalOut(BaseModel):
    id: int
    user_id: str
    hospital: dict[str, Any]
    created_at: str
