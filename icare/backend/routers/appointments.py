"""Appointments CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.appointment import AppointmentCreate, AppointmentResponse
from schemas.user import UserResponse, UserRole
from services.records_service import get_records_service

router = APIRouter()


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access appointments for this patient.",
        )


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "appointments", "status": "ok"}


@router.post("/", response_model=AppointmentResponse)
async def create_appointment_route(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> AppointmentResponse:
    _ensure_patient_access(user, body.patient_id)
    doctor_name = body.doctor_name
    if doctor_name is None and user.role == UserRole.doctor:
        doctor_name = user.name
    svc = get_records_service(db)
    return await svc.create_appointment(body, doctor_name=doctor_name)


@router.get("/{patient_id}", response_model=list[AppointmentResponse])
async def list_appointments_route(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[AppointmentResponse]:
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.list_appointments(patient_id)
