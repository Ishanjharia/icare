"""Health records + AI health context."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.health_record import HealthRecordBody, HealthRecordResponse
from schemas.user import UserResponse, UserRole
from services.records_service import get_records_service

router = APIRouter()


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access records for this patient.",
        )


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "records", "status": "ok"}


@router.get("/{patient_id}/health-context")
async def get_health_context(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> dict:
    """Compact context bundle for LLM prompts."""
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.get_health_context_for_ai(db, patient_id)


@router.post("/{patient_id}", response_model=HealthRecordResponse)
async def create_health_record_route(
    patient_id: uuid.UUID,
    body: HealthRecordBody,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> HealthRecordResponse:
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.create_health_record(
        patient_id=patient_id,
        record_type=body.record_type,
        description=body.description,
        language=body.language,
        report_data=body.report_data,
        vitals_snapshot=body.vitals_snapshot,
    )


@router.get("/{patient_id}", response_model=list[HealthRecordResponse])
async def list_health_records_route(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[HealthRecordResponse]:
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.list_health_records(patient_id)
