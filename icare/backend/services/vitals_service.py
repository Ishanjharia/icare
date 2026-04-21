"""Vitals ingest, InfluxDB Cloud history, thresholds, and snapshot."""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.patient_vitals_threshold import PatientVitalsThreshold
from models.vitals_queue import VitalsQueue
from schemas.vitals import MetricThresholds, ThresholdConfig, VitalReading, VitalsSnapshot

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "heart_rate": {
        "warn_high": 100,
        "alert_high": 130,
        "critical_high": 180,
        "warn_low": 50,
        "critical_low": 40,
    },
    "spo2": {
        "alert_low": 94,
        "critical_low": 88,
    },
    "bp_systolic": {
        "warn_high": 140,
        "critical_high": 180,
        "warn_low": 90,
        "critical_low": 80,
    },
    "bp_diastolic": {
        "warn_high": 90,
        "critical_high": 120,
        "warn_low": 60,
        "critical_low": 50,
    },
}


def normalize_metric(metric: str) -> str:
    """Map common aliases to canonical threshold keys."""
    m = metric.strip().lower().replace(" ", "_")
    aliases = {
        "hr": "heart_rate",
        "heart-rate": "heart_rate",
        "bpm": "heart_rate",
        "bp_sys": "bp_systolic",
        "bp-systolic": "bp_systolic",
        "systolic": "bp_systolic",
        "bp_dia": "bp_diastolic",
        "bp_diastolic": "bp_diastolic",
        "diastolic": "bp_diastolic",
        "o2": "spo2",
        "sp02": "spo2",
    }
    return aliases.get(m, m)


def _threshold_config_from_defaults() -> ThresholdConfig:
    return ThresholdConfig(
        heart_rate=MetricThresholds(**DEFAULT_THRESHOLDS["heart_rate"]),
        spo2=MetricThresholds(**DEFAULT_THRESHOLDS["spo2"]),
        bp_systolic=MetricThresholds(**DEFAULT_THRESHOLDS["bp_systolic"]),
        bp_diastolic=MetricThresholds(**DEFAULT_THRESHOLDS["bp_diastolic"]),
        steps=None,
    )


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(out[key], val)  # type: ignore[arg-type]
        else:
            out[key] = val
    return out


def _defaults_as_nested() -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items()} for k, v in DEFAULT_THRESHOLDS.items()}


def compute_alert_level(metric: str, value: float) -> int | None:
    """Return escalation level 1–5 or ``None`` if within normal range."""
    key = normalize_metric(metric)
    cfg = DEFAULT_THRESHOLDS.get(key)
    if not cfg:
        return None

    if key in {"heart_rate", "bp_systolic", "bp_diastolic"}:
        ch = cfg.get("critical_high")
        ah = cfg.get("alert_high")
        wh = cfg.get("warn_high")
        cl = cfg.get("critical_low")
        wl = cfg.get("warn_low")
        if ch is not None and value >= ch:
            return 5
        if cl is not None and value <= cl:
            return 5
        if ah is not None and value >= ah:
            return 4
        if wl is not None and value <= wl:
            return 3
        if wh is not None and value >= wh:
            return 2

    if key == "spo2":
        cl = cfg.get("critical_low")
        al = cfg.get("alert_low")
        if cl is not None and value <= cl:
            return 5
        if al is not None and value <= al:
            return 3

    return None


class VitalsService:
    """InfluxDB Cloud writes + Postgres offline queue + thresholds."""

    def __init__(self) -> None:
        self._influx: InfluxDBClientAsync | None = None
        try:
            self._influx = InfluxDBClientAsync(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("InfluxDB async client init failed: %s", exc)
            self._influx = None

    def _ensure_utc(self, ts: datetime) -> datetime:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    async def ingest_reading(
        self,
        db: AsyncSession,
        patient_id: str,
        reading: VitalReading,
        background_tasks: BackgroundTasks,
    ) -> None:
        """Write to InfluxDB, buffer in SQL, evaluate alerts, broadcast over WebSockets."""
        pid = uuid.UUID(str(patient_id))
        canonical = normalize_metric(reading.metric)
        ts = self._ensure_utc(reading.timestamp)

        row = VitalsQueue(
            patient_id=pid,
            metric=canonical,
            value=float(reading.value),
            unit=reading.unit,
            timestamp=ts,
            synced=False,
            source=reading.source,
        )
        db.add(row)
        await db.flush()
        row_id = row.id
        await db.commit()

        if self._influx is not None:
            try:
                write_api = self._influx.write_api()
                point = (
                    Point("patient_vitals")
                    .tag("patient_id", str(pid))
                    .tag("metric", canonical)
                    .tag("source", reading.source)
                    .field("value", float(reading.value))
                    .field("unit", reading.unit)
                    .time(ts, WritePrecision.MS)
                )
                await write_api.write(
                    bucket=settings.INFLUXDB_BUCKET,
                    org=settings.INFLUXDB_ORG,
                    record=point,
                )
                await db.execute(update(VitalsQueue).where(VitalsQueue.id == row_id).values(synced=True))
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("InfluxDB write failed (continuing): %s", exc)

        alert_level = await self.check_threshold(canonical, float(reading.value))

        async def _evaluate_and_escalate() -> None:
            from database import async_session_factory
            from services.alert_service import AlertService, run_alert_escalation

            async with async_session_factory() as session:
                svc = AlertService()
                alert = await svc.evaluate_reading(session, pid, canonical, float(reading.value))
                if alert is None:
                    return
                alert_id_str = str(alert.id)
            asyncio.create_task(run_alert_escalation(alert_id_str))

        background_tasks.add_task(_evaluate_and_escalate)

        try:
            from services.vitals_ws_manager import vitals_ws_manager

            await vitals_ws_manager.broadcast_to_patient(
                str(pid),
                {
                    "metric": canonical,
                    "value": float(reading.value),
                    "unit": reading.unit,
                    "timestamp": ts.isoformat(),
                    "alert_level": alert_level,
                    "source": reading.source,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("WebSocket broadcast failed: %s", exc)

    async def get_vitals_history(
        self,
        patient_id: str,
        metric: str,
        *,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Flux query for recent samples."""
        if self._influx is None:
            return []
        canonical = normalize_metric(metric)
        pid = str(patient_id).replace('"', '\\"')
        m = canonical.replace('"', '\\"')
        bucket = settings.INFLUXDB_BUCKET.replace('"', '\\"')
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -{int(hours)}h)
  |> filter(fn: (r) => r["_measurement"] == "patient_vitals")
  |> filter(fn: (r) => r["patient_id"] == "{pid}")
  |> filter(fn: (r) => r["metric"] == "{m}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> sort(columns: ["_time"])
'''
        try:
            query_api = self._influx.query_api()
            tables = await query_api.query(flux, org=settings.INFLUXDB_ORG)
        except Exception as exc:  # noqa: BLE001
            logger.warning("InfluxDB history query failed: %s", exc)
            return []

        out: list[dict[str, Any]] = []
        for table in tables:
            for record in table.records:
                t = record.get_time()
                out.append(
                    {
                        "timestamp": t.isoformat() if isinstance(t, datetime) else str(t),
                        "value": float(record.get_value()),
                        "unit": "",
                    }
                )
        return out

    async def get_latest_snapshot(self, patient_id: str) -> VitalsSnapshot:
        """Most recent ``value`` / ``unit`` points per metric."""
        if self._influx is None:
            return VitalsSnapshot(patient_id=str(patient_id), readings={})

        pid_esc = str(patient_id).replace('"', '\\"')
        bucket = settings.INFLUXDB_BUCKET.replace('"', '\\"')

        def _flux_value() -> str:
            return f"""
from(bucket: \"{bucket}\")
  |> range(start: -168h)
  |> filter(fn: (r) => r[\"_measurement\"] == \"patient_vitals\" and r[\"patient_id\"] == \"{pid_esc}\" and r[\"_field\"] == \"value\")
  |> group(columns: [\"metric\"])
  |> last()
"""

        def _flux_unit() -> str:
            return f"""
from(bucket: \"{bucket}\")
  |> range(start: -168h)
  |> filter(fn: (r) => r[\"_measurement\"] == \"patient_vitals\" and r[\"patient_id\"] == \"{pid_esc}\" and r[\"_field\"] == \"unit\")
  |> group(columns: [\"metric\"])
  |> last()
"""

        values: dict[str, tuple[float, datetime, str]] = {}
        units: dict[str, str] = {}
        try:
            query_api = self._influx.query_api()
            v_tables = await query_api.query(_flux_value(), org=settings.INFLUXDB_ORG)
            for table in v_tables:
                for record in table.records:
                    metric = record.values.get("metric")
                    if not metric:
                        continue
                    t = record.get_time()
                    if not isinstance(t, datetime):
                        continue
                    src = record.values.get("source") or "wearable"
                    values[metric] = (
                        float(record.get_value()),
                        self._ensure_utc(t),
                        str(src),
                    )
            u_tables = await query_api.query(_flux_unit(), org=settings.INFLUXDB_ORG)
            for table in u_tables:
                for record in table.records:
                    metric = record.values.get("metric")
                    if metric:
                        units[str(metric)] = str(record.get_value())
        except Exception as exc:  # noqa: BLE001
            logger.warning("InfluxDB snapshot query failed: %s", exc)
            return VitalsSnapshot(patient_id=str(patient_id), readings={})

        readings: dict[str, VitalReading] = {}
        for metric, (val, tstamp, src) in values.items():
            readings[metric] = VitalReading(
                metric=metric,
                value=val,
                unit=units.get(metric, ""),
                timestamp=tstamp,
                source=src,
            )
        return VitalsSnapshot(patient_id=str(patient_id), readings=readings)

    async def get_thresholds(self, db: AsyncSession, patient_id: str) -> ThresholdConfig:
        """Return defaults merged with per-patient overrides."""
        base = _defaults_as_nested()
        pid = uuid.UUID(str(patient_id))
        row = await db.get(PatientVitalsThreshold, pid)
        if row and row.config:
            merged = _deep_merge_dict(base, dict(row.config))
            return ThresholdConfig.model_validate(merged)
        return _threshold_config_from_defaults()

    async def put_thresholds(
        self,
        db: AsyncSession,
        patient_id: str,
        data: ThresholdConfig,
    ) -> ThresholdConfig:
        """Merge payload onto defaults and persist."""
        pid = uuid.UUID(str(patient_id))
        base = _defaults_as_nested()
        patch = data.model_dump(exclude_none=True)
        payload = _deep_merge_dict(base, patch)
        now = datetime.now(timezone.utc)
        stmt = (
            insert(PatientVitalsThreshold)
            .values(patient_id=pid, config=payload, updated_at=now)
            .on_conflict_do_update(
                index_elements=[PatientVitalsThreshold.patient_id],
                set_={"config": payload, "updated_at": now},
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await self.get_thresholds(db, patient_id)

    async def check_threshold(self, metric: str, value: float) -> int | None:
        """Public async wrapper used by ingest + WebSocket payloads."""
        return compute_alert_level(metric, value)


_vitals_singleton: VitalsService | None = None


def get_vitals_service() -> VitalsService:
    """Shared service instance (reuses one InfluxDB async client)."""
    global _vitals_singleton
    if _vitals_singleton is None:
        _vitals_singleton = VitalsService()
    return _vitals_singleton
