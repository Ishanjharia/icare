"""FastAPI application entry point for I-CARE API."""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import (
    alerts,
    appointments,
    auth,
    chat,
    hospitals,
    medications,
    prescriptions,
    records,
    symptoms,
    vitals,
    voice,
)
from routers.voice import handle_voice_websocket
from services.ai_service import get_ai_service
from services.vitals_service import get_vitals_service
from services.vitals_ws_manager import VitalsConnectionManager

logger = logging.getLogger(__name__)
vitals_ws_manager = VitalsConnectionManager()

app = FastAPI(title="I-CARE API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(vitals.router, prefix="/api/vitals", tags=["vitals"])
app.include_router(symptoms.router, prefix="/api/symptoms", tags=["symptoms"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(prescriptions.router, prefix="/api/prescriptions", tags=["prescriptions"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(medications.router, prefix="/api/medications", tags=["medications"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(hospitals.router, prefix="/api/hospitals", tags=["hospitals"])


@app.on_event("startup")
async def startup() -> None:
    """Try to initialize optional services, but never block app boot."""
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database startup failed; continuing without database: %s", exc)

    try:
        get_vitals_service()
        logger.info("InfluxDB service initialized")
    except Exception as exc:  # noqa: BLE001
        logger.exception("InfluxDB startup failed; continuing without InfluxDB: %s", exc)

    try:
        get_ai_service()
        logger.info("Groq AI service initialized")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Groq startup failed; continuing without AI services: %s", exc)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/vitals/{patient_id}")
async def websocket_vitals(websocket: WebSocket, patient_id: str) -> None:
    """Real-time vitals stream with periodic server ping (keep-alive)."""
    await vitals_ws_manager.connect(patient_id, websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json(
                        {"type": "ping", "ts": datetime.now(timezone.utc).isoformat()},
                    )
                except Exception:
                    break
    except WebSocketDisconnect:
        vitals_ws_manager.disconnect(patient_id, websocket)


@app.websocket("/ws/voice/{patient_id}")
async def websocket_voice(websocket: WebSocket, patient_id: str) -> None:
    """Voice: binary audio chunks -> Groq Whisper -> intent JSON for browser TTS."""
    await handle_voice_websocket(websocket, patient_id)
