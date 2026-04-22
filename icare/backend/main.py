"""FastAPI application entry point for I-CARE API (cloud skeleton)."""

import asyncio
from contextlib import asynccontextmanager
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


def _cors_allow_origins() -> list[str]:
    """Build explicit CORS origin list from FRONTEND_URL (comma-separated) plus local dev defaults."""
    raw = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
    for extra in ("http://localhost:5173", "http://localhost:3000"):
        if extra not in raw:
            raw.append(extra)
    return raw


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: DB bootstrap on startup."""
    try:
        await init_db()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database error: {e}")
    yield


app = FastAPI(title="I-CARE API", version="1.0.0", lifespan=lifespan)

_cors_kw: dict = {
    "allow_origins": _cors_allow_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
_rx = (settings.CORS_ORIGIN_REGEX or "").strip()
if _rx:
    _cors_kw["allow_origin_regex"] = _rx

app.add_middleware(CORSMiddleware, **_cors_kw)

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


@app.get("/health")
async def health() -> dict[str, str]:
    """Wake-up / liveness ping."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
    """Voice: binary audio chunks → Groq Whisper → intent JSON for browser TTS."""
    await handle_voice_websocket(websocket, patient_id)
