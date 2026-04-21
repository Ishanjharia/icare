"""Prescriptions CRUD + PDF download."""

from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user, require_doctor
from schemas.prescription import PrescriptionCreate, PrescriptionResponse
from schemas.user import UserResponse, UserRole
from services.records_service import get_records_service
from utils.pdf_generator import generate_prescription_pdf

router = APIRouter()


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access prescriptions for this patient.",
        )


def _can_read_prescription(user: UserResponse, patient_id: uuid.UUID) -> None:
    _ensure_patient_access(user, patient_id)


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "prescriptions", "status": "ok"}


@router.post("/", response_model=PrescriptionResponse)
async def create_prescription_route(
    body: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    doctor: UserResponse = Depends(require_doctor),
) -> PrescriptionResponse:
    """Doctor-only: create prescription for a patient."""
    _ensure_patient_access(doctor, body.patient_id)
    svc = get_records_service(db)
    return await svc.create_prescription(body, doctor_name=body.doctor_name or doctor.name)


@router.get("/{prescription_id:int}/pdf")
async def download_prescription_pdf(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> StreamingResponse:
    svc = get_records_service(db)
    row = await svc.get_prescription(prescription_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")
    _can_read_prescription(user, row.patient_id)
    payload = PrescriptionResponse.model_validate(row).model_dump(mode="json")
    pdf_bytes = generate_prescription_pdf(payload)
    headers = {"Content-Disposition": f'attachment; filename="prescription_{prescription_id}.pdf"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/{patient_id}", response_model=list[PrescriptionResponse])
async def list_prescriptions_route(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[PrescriptionResponse]:
    _ensure_patient_access(user, patient_id)
    svc = get_records_service(db)
    return await svc.list_prescriptions(patient_id)
