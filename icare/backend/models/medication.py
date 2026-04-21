"""Medication ORM model."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Medication(Base):
    """Ongoing medication for a patient."""

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    dosage: Mapped[str] = mapped_column(String(255))
    frequency: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
