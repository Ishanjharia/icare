"""Shared HTTP client for POST /api/vitals/ingest (IoT scripts)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


async def post_vital_ingest(
    client: httpx.AsyncClient,
    api_base_url: str,
    patient_id: uuid.UUID,
    reading: dict[str, Any],
    *,
    jwt_token: str | None = None,
) -> httpx.Response:
    """POST a single vital reading (shape matches FastAPI VitalsIngestRequest)."""
    base = api_base_url.rstrip("/")
    headers: dict[str, str] = {}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    body = {
        "patient_id": str(patient_id),
        "reading": {
            "metric": reading["metric"],
            "value": float(reading["value"]),
            "unit": reading.get("unit"),
            "timestamp": _iso_timestamp(reading.get("timestamp")),
            "source": reading.get("source") or "iot",
        },
    }
    return await client.post(f"{base}/api/vitals/ingest", json=body, headers=headers, timeout=30.0)


def _iso_timestamp(ts: Any) -> str:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return datetime.now(timezone.utc).isoformat()
