"""Hospital finder (AI) + saved hospitals."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps.auth import get_current_user
from models.saved_hospital import SavedHospital
from schemas.hospital import HospitalSearchRequest, HospitalSearchResponse, SavedHospitalCreate
from schemas.user import UserResponse
from services.ai_service import get_ai_service

router = APIRouter()


def _ensure_saved_owner(user: UserResponse, user_id: uuid.UUID) -> None:
    if uuid.UUID(str(user.id)) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access saved hospitals for your own account.",
        )


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "hospitals", "status": "ok"}


@router.post("/search", response_model=HospitalSearchResponse)
async def search_hospitals(
    body: HospitalSearchRequest,
    user: UserResponse = Depends(get_current_user),
) -> HospitalSearchResponse:
    """AI-generated structured hospital listings for a city (demo data)."""
    _ = user
    raw = await get_ai_service().find_hospitals(body.city, body.specialty, body.language)
    return HospitalSearchResponse.model_validate(raw)


@router.get("/saved/{user_id}")
async def list_saved_hospitals(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> list[dict[str, object]]:
    _ensure_saved_owner(user, user_id)
    q = select(SavedHospital).where(SavedHospital.user_id == user_id).order_by(desc(SavedHospital.created_at))
    rows = (await db.scalars(q)).all()
    return [
        {
            "id": r.id,
            "user_id": str(r.user_id),
            "hospital": r.hospital,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/saved/{user_id}", status_code=status.HTTP_201_CREATED)
async def save_hospital(
    user_id: uuid.UUID,
    body: SavedHospitalCreate,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> dict[str, object]:
    _ensure_saved_owner(user, user_id)
    row = SavedHospital(user_id=user_id, hospital=body.hospital)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "user_id": str(row.user_id),
        "hospital": row.hospital,
        "created_at": row.created_at.isoformat(),
    }
