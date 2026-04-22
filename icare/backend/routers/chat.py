"""Health chat — streaming medical assistant (SSE)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory, get_db
from deps.auth import get_current_user
from schemas.chat import ChatMessageRequest
from schemas.user import UserResponse, UserRole
from services.ai_service import get_ai_service
from services.auth_service import AuthService
from services.records_service import get_records_service

router = APIRouter()


def _resolve_chat_patient(user: UserResponse, patient_id: uuid.UUID | None) -> uuid.UUID:
    if user.role == UserRole.doctor:
        if patient_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id is required when the caller is a doctor.",
            )
        return patient_id
    if patient_id is not None and uuid.UUID(str(user.id)) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot open chat context for another patient.",
        )
    return uuid.UUID(str(user.id))


def _normalize_history(rows: list[object]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for x in rows[-24:]:
        if not isinstance(x, dict):
            continue
        role = str(x.get("role", "")).lower().strip()
        content = str(x.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content})
    return out


async def _sse_chat_chunks(
    *,
    message: str,
    language: str,
    role: str,
    profile: dict[str, Any],
    history: list[dict[str, str]],
) -> AsyncIterator[bytes]:
    try:
        async for piece in get_ai_service().chat_response(message, language, role, profile, history):
            line = f"data: {json.dumps(piece)}\n\n"
            yield line.encode("utf-8")
        yield b'data: "[DONE]"\n\n'
    except Exception as exc:  # noqa: BLE001
        err = json.dumps(f"\n[stream error: {exc!s}]")
        yield f"data: {err}\n\n".encode("utf-8")
        yield b'data: "[DONE]"\n\n'


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"router": "chat", "status": "ok"}


@router.post("/message")
async def chat_message_stream(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> StreamingResponse:
    """Stream assistant reply as Server-Sent Events (``data: …`` per chunk)."""
    target = _resolve_chat_patient(user, body.patient_id)
    ctx = await get_records_service(db).get_health_context_for_ai(db, target)
    profile = ctx.get("profile") or {}
    role = str(user.role)
    history = _normalize_history(body.conversation_history)

    return StreamingResponse(
        _sse_chat_chunks(message=body.message, language=body.language, role=role, profile=profile, history=history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream")
async def chat_stream_get(
    token: str = Query(..., description="JWT (EventSource cannot send Authorization header)."),
    message: str = Query(..., min_length=1, max_length=8000),
    language: str = Query("English", max_length=64),
    patient_id: uuid.UUID | None = Query(default=None),
    history: str | None = Query(default=None, description="JSON array of {role, content} turns."),
) -> StreamingResponse:
    """SSE stream for browsers using EventSource (token passed as query param)."""
    hist_raw: list[object] = []
    if history:
        try:
            parsed = json.loads(history)
            if isinstance(parsed, list):
                hist_raw = parsed
        except json.JSONDecodeError:
            pass
    history_norm = _normalize_history(hist_raw)

    if async_session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not configured")

    async with async_session_factory() as db:
        user = await AuthService().get_current_user(db, token)
        target = _resolve_chat_patient(user, patient_id)
        ctx = await get_records_service(db).get_health_context_for_ai(db, target)
        profile = ctx.get("profile") or {}
        role = str(user.role)

    return StreamingResponse(
        _sse_chat_chunks(message=message, language=language, role=role, profile=profile, history=history_norm),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
