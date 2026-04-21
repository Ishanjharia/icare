"""WebSocket connection registry for live vitals (imported by main + routers to avoid cycles)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class VitalsConnectionManager:
    """Manage vitals WebSocket clients per patient."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, patient_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(patient_id, []).append(websocket)

    def disconnect(self, patient_id: str, websocket: WebSocket) -> None:
        clients = self.active_connections.get(patient_id)
        if not clients:
            return
        if websocket in clients:
            clients.remove(websocket)
        if not clients:
            self.active_connections.pop(patient_id, None)

    async def broadcast_to_patient(self, patient_id: str, data: dict[str, Any]) -> None:
        """Push a JSON payload to every open socket for ``patient_id``."""
        stale: list[WebSocket] = []
        for ws in list(self.active_connections.get(patient_id, [])):
            try:
                await ws.send_json(data)
            except Exception as exc:  # noqa: BLE001
                logger.debug("WebSocket send failed, dropping client: %s", exc)
                stale.append(ws)
        for ws in stale:
            self.disconnect(patient_id, ws)


vitals_ws_manager = VitalsConnectionManager()
