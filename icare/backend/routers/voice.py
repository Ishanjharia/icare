"""Voice: Groq Whisper STT, intent routing, WebSocket streaming from browser."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile, WebSocket, WebSocketDisconnect

from services.voice_service import get_voice_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(..., description="Recorded audio (e.g. webm from MediaRecorder)"),
) -> dict[str, Any]:
    """Server-side STT via Groq Whisper."""
    data = await audio.read()
    if not data:
        return {"success": False, "transcription": "", "detected_language": "", "error": "empty file"}
    return await get_voice_service().transcribe_audio(data)


@router.post("/command")
async def voice_command(
    audio: UploadFile = File(...),
    patient_id: str = Form(...),
    language: str = Form("English"),
) -> dict[str, Any]:
    """Transcribe, classify intent, return text for browser Web Speech API."""
    try:
        pid = uuid.UUID(str(patient_id))
    except ValueError:
        return {
            "transcript": "",
            "intent": "unknown",
            "confidence": 0.0,
            "response_text": "Invalid patient id.",
            "action": "none",
            "action_params": {},
        }
    body = await audio.read()
    if not body:
        return {
            "transcript": "",
            "intent": "unknown",
            "confidence": 0.0,
            "response_text": "No audio received.",
            "action": "none",
            "action_params": {},
        }
    return await get_voice_service().process_voice_command(body, patient_id=pid, language=language)


async def handle_voice_websocket(websocket: WebSocket, patient_id: str) -> None:
    """
    Receive binary audio chunks; flush after ~1.5s idle gap, transcribe, classify, reply in JSON.
    Optional first text frame: {"type":"config","language":"Hindi"}.
    """
    try:
        uuid.UUID(str(patient_id))
    except ValueError:
        await websocket.close(code=4400)
        return

    await websocket.accept()
    svc = get_voice_service()
    buf = bytearray()
    session_language = "English"
    silence_seconds = 1.5

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=silence_seconds)
            except asyncio.TimeoutError:
                if not buf:
                    continue
                try:
                    result = await svc.process_voice_command(
                        bytes(buf),
                        patient_id=patient_id,
                        language=session_language,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("voice ws process failed: %s", exc)
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(exc),
                        },
                    )
                    buf.clear()
                    continue

                buf.clear()
                transcript = str(result.get("transcript", ""))
                await websocket.send_json({"type": "transcription", "text": transcript})
                await websocket.send_json(
                    {
                        "type": "intent",
                        "intent": result.get("intent"),
                        "confidence": result.get("confidence"),
                        "response_text": result.get("response_text"),
                        "action": result.get("action"),
                        "action_params": result.get("action_params", {}),
                    },
                )
                continue

            if message.get("type") == "websocket.disconnect":
                break

            if message.get("type") != "websocket.receive":
                continue

            if "text" in message and message["text"] is not None:
                raw = message["text"]
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "config":
                    lang = payload.get("language")
                    if isinstance(lang, str) and lang.strip():
                        session_language = lang.strip()
                continue

            chunk = message.get("bytes")
            if chunk:
                buf.extend(chunk)

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("voice websocket error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
