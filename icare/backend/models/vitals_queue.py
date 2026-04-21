"""Offline buffer for vitals when cloud sync is delayed."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class VitalsQueue(Base):
    """Queued vital row for retry / audit (Influx write companion)."""

    __tablename__ = "vitals_queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float())
    unit: Mapped[str] = mapped_column(String(32), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    synced: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), index=True)
    source: Mapped[str] = mapped_column(String(64), default="wearable")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
