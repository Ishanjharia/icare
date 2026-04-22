"""FastAPI application entry point for I-CARE API."""

import asyncio
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
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
from services.vitals_ws_manager import VitalsConnectionManager

vitals_ws_manager = VitalsConnectionManager()

app = FastAPI(title="I-CARE API", version="1.0.0")


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
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
    from database import engine as _db_engine

    if _db_engine is None:
        message = (
            "Database failed: DATABASE_URL is not set or empty. "
            "Set DATABASE_URL in Render environment with the Supabase connection string."
        )
        print(message)
        if settings.ENVIRONMENT.lower() != "development":
            raise RuntimeError(message)
        return
    try:
        await init_db()
        print("Database connected")
    except Exception as exc:
        print(f"Database failed: {exc!r}")
        traceback.print_exc()
        raise


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
