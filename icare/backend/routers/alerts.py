"""Alert listing, acknowledgement, manual emergency, escalation pipeline metadata."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from models.alert import Alert
from schemas.alert import AlertOut, EmergencyTriggerResponse, PipelineStatus
from schemas.user import UserResponse, UserRole
from services.alert_service import AlertService

router = APIRouter()


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Router liveness (must stay above ``/{id}`` routes)."""
    return {"router": "alerts", "status": "ok"}


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access alerts for this patient.",
        )


@router.post("/emergency/{patient_id}", response_model=EmergencyTriggerResponse)
async def post_emergency(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> EmergencyTriggerResponse:
    """Create a level-5 emergency alert, SMS all contacts, broadcast WebSocket."""
    _ensure_patient_access(user, patient_id)
    svc = AlertService()
    row = await svc.trigger_emergency(db, patient_id)
    return EmergencyTriggerResponse(alert=AlertOut.model_validate(row))


@router.post("/{alert_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def post_acknowledge_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> None:
    """Mark an alert acknowledged (stops escalation)."""
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    _ensure_patient_access(user, alert.patient_id)
    svc = AlertService()
    ok = await svc.acknowledge_alert(db, str(alert_id), alert.patient_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")


@router.get("/{patient_id}/history", response_model=list[AlertOut])
async def get_alert_history(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[AlertOut]:
    """All alerts for the patient (recent first)."""
    _ensure_patient_access(user, patient_id)
    return await AlertService().list_history(db, patient_id)


@router.get("/{patient_id}/pipeline", response_model=PipelineStatus)
async def get_pipeline_status(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> PipelineStatus:
    """Escalation ladder definition plus active unacknowledged alerts."""
    _ensure_patient_access(user, patient_id)
    return await AlertService().pipeline_status(db, patient_id)


@router.get("/{patient_id}", response_model=list[AlertOut])
async def get_active_alerts(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[AlertOut]:
    """Active unacknowledged alerts."""
    _ensure_patient_access(user, patient_id)
    return await AlertService().list_active_unacknowledged(db, patient_id)
