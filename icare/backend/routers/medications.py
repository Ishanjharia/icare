"""Medications CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from schemas.user import UserResponse, UserRole
from services.records_service import get_records_service

router = APIRouter()


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access medications for this patient.",
        )


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "medications", "status": "ok"}


@router.post("/", response_model=MedicationResponse)
async def create_medication_route(
    body: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> MedicationResponse:
    _ensure_patient_access(user, body.patient_id)
    svc = get_records_service(db)
    return await svc.create_medication(body)


@router.put("/{medication_id:int}", response_model=MedicationResponse)
async def update_medication_route(
    medication_id: int,
    body: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> MedicationResponse:
    svc = get_records_service(db)
    row = await svc.get_medication_by_id(medication_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found.")
    if user.role != UserRole.doctor and row.patient_id != uuid.UUID(str(user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    out = await svc.update_medication(medication_id, row.patient_id, body)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found.")
    return out


@router.get("/{patient_id}", response_model=list[MedicationResponse])
async def list_medications_route(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[MedicationResponse]:
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.list_medications(patient_id)
