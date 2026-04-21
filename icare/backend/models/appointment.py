"""Appointment ORM model."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Time, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Appointment(Base):
    """Scheduled appointment between patient and clinician."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appt_date: Mapped[date] = mapped_column(Date())
    appt_time: Mapped[time] = mapped_column(Time())
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    language: Mapped[str] = mapped_column(String(32), default="en")
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
