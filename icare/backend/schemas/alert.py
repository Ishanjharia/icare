"""Alert API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    """Serialized alert row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    vital_type: str
    value: float
    threshold: float
    level: int
    message: str
    acknowledged: bool
    acknowledged_at: datetime | None
    sms_sent: bool
    caregiver_notified: bool
    created_at: datetime


class PipelineStep(BaseModel):
    """Named escalation step and delay before the next level."""

    from_level: int
    to_level: int
    delay_seconds: int
    action: str


class PipelineStatus(BaseModel):
    """Escalation ladder reference + snapshot of open alerts."""

    patient_id: uuid.UUID
    steps: list[PipelineStep]
    active_alerts: list[AlertOut]


class EmergencyTriggerResponse(BaseModel):
    """Manual emergency trigger."""

    alert: AlertOut
    status: str = "emergency_dispatched"
