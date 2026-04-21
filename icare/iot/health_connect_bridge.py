"""Android Health Connect → FastAPI vitals bridge (simulation + HTTP ingest).

Production: a companion Android service reads Health Connect and POSTs vitals
(or streams to this process via IPC). This module provides the same HTTP
contract with a built-in random-walk simulator for laptops without Health Connect.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_IOT_DIR = Path(__file__).resolve().parent
if str(_IOT_DIR) not in sys.path:
    sys.path.insert(0, str(_IOT_DIR))
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import httpx

from vitals_client import post_vital_ingest

VitalMetric = Literal["hr", "spo2", "bp_sys", "bp_dia", "steps"]


@dataclass
class VitalReading:
    """One measurement aligned with backend ``schemas.vitals.VitalReading``."""

    metric: VitalMetric
    value: float
    unit: str | None
    timestamp: datetime
    source: str = "health_connect_sim"


class HealthConnectBridge:
    """Poll (or simulate) vitals and POST each reading to ``/api/vitals/ingest``."""

    def __init__(
        self,
        patient_id: str | uuid.UUID,
        api_base_url: str,
        interval_seconds: float = 5.0,
        *,
        jwt_token: str | None = None,
        simulate: bool | None = None,
    ) -> None:
        self.patient_id = uuid.UUID(str(patient_id))
        self.api_base_url = api_base_url.rstrip("/")
        self.interval_seconds = interval_seconds
        self.jwt_token = jwt_token or os.environ.get("ICARE_JWT_TOKEN", "").strip() or None
        if simulate is None:
            simulate = os.environ.get("HEALTH_CONNECT_SIMULATE", "1").lower() in ("1", "true", "yes")
        self._simulate = simulate
        self._client: httpx.AsyncClient | None = None
        # Random-walk state (simulation)
        self._hr = 75.0
        self._spo2 = 98.0
        self._bp_sys = 120.0
        self._bp_dia = 80.0
        self._steps = 4000.0

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def start_streaming(self) -> None:
        """Run forever: fetch readings, POST to API, sleep."""
        try:
            while True:
                readings = await self.get_latest_readings()
                await self.post_to_api(readings)
                await asyncio.sleep(self.interval_seconds)
        finally:
            await self.aclose()

    async def get_latest_readings(self) -> list[VitalReading]:
        if self._simulate:
            return self._simulated_readings()
        return await self._query_health_connect_android()

    def _simulated_readings(self) -> list[VitalReading]:
        now = datetime.now(timezone.utc)
        self._hr += random.uniform(-3.0, 3.0)
        self._hr = max(45.0, min(110.0, 0.92 * self._hr + 0.08 * 75.0))
        self._spo2 += random.uniform(-0.3, 0.3)
        self._spo2 = max(94.0, min(100.0, 0.95 * self._spo2 + 0.05 * 98.0))
        self._bp_sys += random.uniform(-2.0, 2.0)
        self._bp_dia += random.uniform(-2.0, 2.0)
        self._bp_sys = max(95.0, min(135.0, 0.9 * self._bp_sys + 0.1 * 120.0))
        self._bp_dia = max(65.0, min(95.0, 0.9 * self._bp_dia + 0.1 * 80.0))
        self._steps += random.uniform(0, 8)

        return [
            VitalReading("hr", round(self._hr, 1), "bpm", now),
            VitalReading("spo2", round(self._spo2, 1), "%", now),
            VitalReading("bp_sys", round(self._bp_sys, 1), "mmHg", now),
            VitalReading("bp_dia", round(self._bp_dia, 1), "mmHg", now),
            VitalReading("steps", round(self._steps, 0), "count", now),
        ]

    async def _query_health_connect_android(self) -> list[VitalReading]:
        """Production hook: populate from Health Connect (Android-side pipeline)."""
        raise NotImplementedError(
            "Health Connect is queried on Android. Build a companion service that "
            "POSTs to /api/vitals/ingest, or set HEALTH_CONNECT_SIMULATE=1 for development.",
        )

    async def post_to_api(self, readings: list[VitalReading]) -> None:
        client = await self._ensure_client()
        for r in readings:
            resp = await post_vital_ingest(
                client,
                self.api_base_url,
                self.patient_id,
                {
                    "metric": r.metric,
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp,
                    "source": r.source,
                },
                jwt_token=self.jwt_token,
            )
            resp.raise_for_status()


async def _cli_main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Health Connect bridge (simulated by default)")
    p.add_argument("--patient-id", type=uuid.UUID, required=True)
    p.add_argument("--api-url", default=os.environ.get("ICARE_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--token", default=os.environ.get("ICARE_JWT_TOKEN", ""))
    p.add_argument("--no-sim", action="store_true", help="Use real Health Connect path (NotImplemented)")
    args = p.parse_args()
    bridge = HealthConnectBridge(
        args.patient_id,
        args.api_url,
        args.interval,
        jwt_token=args.token or None,
        simulate=not args.no_sim,
    )
    await bridge.start_streaming()


if __name__ == "__main__":
    asyncio.run(_cli_main())
