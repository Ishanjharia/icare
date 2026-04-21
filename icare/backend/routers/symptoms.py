"""Symptom checker — Groq-backed triage."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.health_record import HealthRecordResponse
from schemas.symptom import SymptomAnalyzeRequest, SymptomAnalyzeResponse
from schemas.user import UserResponse, UserRole
from schemas.vitals import VitalsSnapshot
from services.ai_service import get_ai_service
from services.records_service import get_records_service
from services.vitals_service import get_vitals_service

router = APIRouter()


def _ensure_symptom_patient_scope(user: UserResponse, patient_id: uuid.UUID | None) -> uuid.UUID:
    """Doctors may pass patient_id; patients use self."""
    if user.role == UserRole.doctor:
        if patient_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id is required when the caller is a doctor.",
            )
        return patient_id
    if patient_id is not None and uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot analyze for another patient.")
    return uuid.UUID(str(user.id))


def _ensure_history_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to read symptom history for this patient.",
        )


def _vitals_dict_from_snapshot(snap: VitalsSnapshot) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m, vr in snap.readings.items():
        out[m] = {
            "value": vr.value,
            "unit": vr.unit,
            "timestamp": vr.timestamp.isoformat(),
            "source": vr.source,
        }
    return out


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "symptoms", "status": "ok"}


@router.post("/analyze", response_model=SymptomAnalyzeResponse)
async def analyze_symptoms(
    body: SymptomAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> SymptomAnalyzeResponse:
    """Structured symptom triage via Groq; optionally persists analysis as a health record."""
    target_patient = _ensure_symptom_patient_scope(user, body.patient_id)
    svc = get_records_service(db)
    ctx = await svc.get_health_context_for_ai(db, target_patient)
    profile = ctx.get("profile") or {}

    vitals_snap: dict[str, Any] | None = None
    vitals_stored: dict[str, Any] | None = None
    if body.include_vitals:
        snap = await get_vitals_service().get_latest_snapshot(str(target_patient))
        vitals_snap = _vitals_dict_from_snapshot(snap) if snap.readings else {}
        vitals_stored = vitals_snap or None

    raw = await get_ai_service().analyze_symptoms(
        body.symptoms_text,
        body.language,
        health_profile=profile,
        vitals_snapshot=vitals_snap if vitals_snap else None,
    )
    result = SymptomAnalyzeResponse.model_validate(raw)

    description = (result.symptoms_summary or body.symptoms_text).strip()[:8000]
    report_payload = result.model_dump(mode="json")
    await svc.create_health_record(
        patient_id=target_patient,
        record_type="symptom_analysis",
        description=description,
        language=body.language,
        report_data=report_payload,
        vitals_snapshot=vitals_stored,
    )
    return result


@router.get("/history/{patient_id}", response_model=list[HealthRecordResponse])
async def symptom_analysis_history(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[HealthRecordResponse]:
    """All saved symptom analysis records for a patient."""
    _ensure_history_access(user, patient_id)
    return await get_records_service(db).list_symptom_analysis_records(patient_id)
