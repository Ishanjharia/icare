"""Vitals Pydantic schemas."""

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VitalReading(BaseModel):
    """Single vital reading from a device or simulator."""

    metric: str
    value: float
    unit: str
    timestamp: datetime
    source: str = Field(default="wearable", max_length=64)


class VitalsIngestRequest(BaseModel):
    """Ingest one reading for a patient."""

    patient_id: str
    reading: VitalReading


class VitalsSimulateRequest(BaseModel):
    """Start a time-limited server-side vitals simulation (demo)."""

    patient_id: str
    scenario: Literal["normal", "hr_spike", "spo2_drop", "bp_high"]
    duration_seconds: int = Field(60, ge=10, le=300)


class MetricThresholds(BaseModel):
    """Threshold band for one metric (fields optional per metric type)."""

    model_config = ConfigDict(extra="ignore")

    warn_high: float | None = None
    alert_high: float | None = None
    critical_high: float | None = None
    warn_low: float | None = None
    critical_low: float | None = None
    alert_low: float | None = None


class ThresholdConfig(BaseModel):
    """Per-metric threshold configuration."""

    model_config = ConfigDict(extra="ignore")

    heart_rate: MetricThresholds | None = None
    spo2: MetricThresholds | None = None
    bp_systolic: MetricThresholds | None = None
    bp_diastolic: MetricThresholds | None = None
    steps: MetricThresholds | None = None


class VitalsSnapshot(BaseModel):
    """Latest readings keyed by canonical metric name."""

    patient_id: str
    readings: dict[str, VitalReading] = Field(default_factory=dict)
