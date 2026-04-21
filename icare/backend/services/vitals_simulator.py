"""Server-side vitals demo simulation (POST /api/vitals/simulate)."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone

from database import async_session_factory
from schemas.vitals import VitalReading
from services.vitals_service import get_vitals_service
from starlette.background import BackgroundTasks

logger = logging.getLogger(__name__)

SCENARIOS = frozenset({"normal", "hr_spike", "spo2_drop", "bp_high"})


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _readings_for_scenario(scenario: str, elapsed_sec: float) -> list[VitalReading]:
    """Build one batch of vitals for the current elapsed time (since sim start)."""
    ts = datetime.now(timezone.utc)
    source = "server_simulator"
    readings: list[VitalReading] = []

    if scenario == "normal":
        hr = _clamp(75 + random.uniform(-5, 5), 62, 95)
        spo2 = _clamp(98 + random.uniform(-1.2, 1.2), 94, 100)
        sys_v = _clamp(120 + random.uniform(-4, 4), 105, 135)
        dia_v = _clamp(80 + random.uniform(-3, 3), 68, 92)
        steps = max(0, int(1200 + random.uniform(-200, 400)))
        readings = [
            VitalReading(metric="heart_rate", value=hr, unit="bpm", timestamp=ts, source=source),
            VitalReading(metric="spo2", value=spo2, unit="%", timestamp=ts, source=source),
            VitalReading(metric="bp_systolic", value=sys_v, unit="mmHg", timestamp=ts, source=source),
            VitalReading(metric="bp_diastolic", value=dia_v, unit="mmHg", timestamp=ts, source=source),
            VitalReading(metric="steps", value=float(steps), unit="steps", timestamp=ts, source=source),
        ]
    elif scenario == "hr_spike":
        p = min(1.0, elapsed_sec / 30.0)
        hr = 75 + (145 - 75) * p + random.uniform(-1, 1)
        spo2 = _clamp(98 + random.uniform(-0.5, 0.5), 95, 100)
        sys_v = _clamp(118 + random.uniform(-2, 2), 110, 128)
        dia_v = _clamp(78 + random.uniform(-2, 2), 72, 85)
        readings = [
            VitalReading(metric="heart_rate", value=_clamp(hr, 55, 190), unit="bpm", timestamp=ts, source=source),
            VitalReading(metric="spo2", value=spo2, unit="%", timestamp=ts, source=source),
            VitalReading(metric="bp_systolic", value=sys_v, unit="mmHg", timestamp=ts, source=source),
            VitalReading(metric="bp_diastolic", value=dia_v, unit="mmHg", timestamp=ts, source=source),
        ]
    elif scenario == "spo2_drop":
        p = min(1.0, elapsed_sec / 20.0)
        spo2 = 98 + (89 - 98) * p + random.uniform(-0.3, 0.3)
        hr = _clamp(78 + random.uniform(-3, 3), 60, 100)
        sys_v = _clamp(118 + random.uniform(-2, 2), 108, 128)
        dia_v = _clamp(78 + random.uniform(-2, 2), 70, 88)
        readings = [
            VitalReading(metric="heart_rate", value=hr, unit="bpm", timestamp=ts, source=source),
            VitalReading(metric="spo2", value=_clamp(spo2, 85, 100), unit="%", timestamp=ts, source=source),
            VitalReading(metric="bp_systolic", value=sys_v, unit="mmHg", timestamp=ts, source=source),
            VitalReading(metric="bp_diastolic", value=dia_v, unit="mmHg", timestamp=ts, source=source),
        ]
    elif scenario == "bp_high":
        p = min(1.0, elapsed_sec / 30.0)
        sys_v = 118 + (168 - 118) * p + random.uniform(-1, 1)
        dia_v = 78 + (92 - 78) * p * 0.6 + random.uniform(-1, 1)
        hr = _clamp(82 + random.uniform(-3, 3), 65, 105)
        spo2 = _clamp(97 + random.uniform(-0.8, 0.8), 94, 99)
        readings = [
            VitalReading(metric="heart_rate", value=hr, unit="bpm", timestamp=ts, source=source),
            VitalReading(metric="spo2", value=spo2, unit="%", timestamp=ts, source=source),
            VitalReading(metric="bp_systolic", value=_clamp(sys_v, 100, 200), unit="mmHg", timestamp=ts, source=source),
            VitalReading(metric="bp_diastolic", value=_clamp(dia_v, 60, 105), unit="mmHg", timestamp=ts, source=source),
        ]
    else:
        readings = _readings_for_scenario("normal", elapsed_sec)

    return readings


async def run_vitals_simulation(patient_id: str, scenario: str, duration_seconds: int) -> None:
    """Emit vitals every 3s for ``duration_seconds`` (used as FastAPI background task)."""
    if scenario not in SCENARIOS:
        scenario = "normal"
    svc = get_vitals_service()
    t_start = time.monotonic()
    logger.info("Vitals simulation started patient=%s scenario=%s duration=%ss", patient_id, scenario, duration_seconds)

    try:
        while time.monotonic() - t_start < duration_seconds:
            elapsed = time.monotonic() - t_start
            batch = _readings_for_scenario(scenario, elapsed)
            async with async_session_factory() as db:
                bt = BackgroundTasks()
                for reading in batch:
                    await svc.ingest_reading(db, patient_id, reading, bt)
                await bt()
            remaining = duration_seconds - (time.monotonic() - t_start)
            if remaining <= 0:
                break
            await asyncio.sleep(min(3.0, max(0.1, remaining)))
    except asyncio.CancelledError:
        logger.info("Vitals simulation cancelled patient=%s", patient_id)
        raise
    except Exception:
        logger.exception("Vitals simulation failed patient=%s", patient_id)
    finally:
        logger.info("Vitals simulation finished patient=%s", patient_id)
