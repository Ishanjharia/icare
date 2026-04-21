"""Alert ORM model — vitals escalation pipeline (levels 1–5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Alert(Base):
    """Threshold breach or manual emergency; escalates with timed SMS + WebSocket updates."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    vital_type: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float())
    threshold: Mapped[float] = mapped_column(Float())
    level: Mapped[int] = mapped_column(Integer(), default=1)
    message: Mapped[str] = mapped_column(Text(), default="")
    acknowledged: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sms_sent: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    caregiver_notified: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
