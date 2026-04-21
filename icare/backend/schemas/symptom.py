"""Symptom checker API schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SymptomAnalyzeRequest(BaseModel):
    """Patient or doctor submits symptoms for offline LLM triage."""

    symptoms_text: str = Field(..., min_length=3, max_length=8000)
    language: str = Field(default="Hindi", max_length=64)
    include_vitals: bool = Field(
        default=True,
        description="When true, attach latest vitals snapshot to the model prompt.",
    )
    patient_id: uuid.UUID | None = Field(
        default=None,
        description="Required when caller is a doctor analyzing a specific patient.",
    )


class SymptomAnalyzeResponse(BaseModel):
    """Structured output from AIService.analyze_symptoms."""

    success: bool = True
    error: str | None = None
    severity_level: str = "Low"
    urgent_care_needed: bool = False
    symptoms_summary: str = ""
    possible_conditions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    confidence_score: float = 0.5
    medical_disclaimer: str = ""
    escalation_note: str | None = None
    raw_context: dict[str, Any] | None = Field(
        default=None,
        description="Compact vitals + profile context sent to the model (for UI transparency).",
    )
