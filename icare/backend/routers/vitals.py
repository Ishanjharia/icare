"""Vitals ingest, history, thresholds, and snapshot routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from schemas.user import UserResponse, UserRole
from schemas.vitals import ThresholdConfig, VitalsIngestRequest, VitalsSimulateRequest, VitalsSnapshot
from services.vitals_service import get_vitals_service
from services.vitals_simulator import run_vitals_simulation

router = APIRouter()


def _ensure_patient_access(user: UserResponse, patient_id: uuid.UUID) -> None:
    """Doctors may access any patient; others only their own UUID."""
    if user.role == UserRole.doctor:
        return
    if uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access vitals for this patient.",
        )


@router.post("/ingest", status_code=status.HTTP_200_OK)
async def ingest_vitals(
    body: VitalsIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> dict[str, str]:
    """IoT / wearable posts a single reading (requires auth)."""
    patient_uuid = uuid.UUID(str(body.patient_id))
    _ensure_patient_access(user, patient_uuid)
    svc = get_vitals_service()
    await svc.ingest_reading(db, str(patient_uuid), body.reading, background_tasks)
    return {"status": "ok"}


@router.post("/simulate", status_code=status.HTTP_202_ACCEPTED)
async def simulate_vitals(
    body: VitalsSimulateRequest,
    background_tasks: BackgroundTasks,
    user: UserResponse = Depends(get_current_user),
) -> dict[str, str | int]:
    """Run a demo vitals generator on the server for ``duration_seconds`` (does not require the browser)."""
    patient_uuid = uuid.UUID(str(body.patient_id))
    _ensure_patient_access(user, patient_uuid)
    duration = min(max(body.duration_seconds, 10), 300)
    background_tasks.add_task(
        run_vitals_simulation,
        str(patient_uuid),
        body.scenario,
        duration,
    )
    return {
        "status": "started",
        "patient_id": str(patient_uuid),
        "scenario": body.scenario,
        "duration_seconds": duration,
    }


@router.get("/snapshot/{patient_id}", response_model=VitalsSnapshot)
async def vitals_snapshot(
    patient_id: uuid.UUID,
    user: UserResponse = Depends(get_current_user),
) -> VitalsSnapshot:
    """Latest reading per metric from InfluxDB."""
    _ensure_patient_access(user, patient_id)
    return await get_vitals_service().get_latest_snapshot(str(patient_id))


@router.get("/history/{patient_id}")
async def vitals_history(
    patient_id: uuid.UUID,
    metric: str = Query(..., description="Canonical or alias metric, e.g. heart_rate"),
    hours: int = Query(24, ge=1, le=168),
    user: UserResponse = Depends(get_current_user),
) -> list[dict]:
    """Time-ordered samples from InfluxDB."""
    _ensure_patient_access(user, patient_id)
    return await get_vitals_service().get_vitals_history(str(patient_id), metric, hours=hours)


@router.get("/thresholds/{patient_id}", response_model=ThresholdConfig)
async def get_thresholds(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> ThresholdConfig:
    """Merged default + stored thresholds."""
    _ensure_patient_access(user, patient_id)
    return await get_vitals_service().get_thresholds(db, str(patient_id))


@router.put("/thresholds/{patient_id}", response_model=ThresholdConfig)
async def put_thresholds(
    patient_id: uuid.UUID,
    body: ThresholdConfig,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> ThresholdConfig:
    """Persist merged threshold overrides (same access rules as GET)."""
    _ensure_patient_access(user, patient_id)
    return await get_vitals_service().put_thresholds(db, str(patient_id), body)
