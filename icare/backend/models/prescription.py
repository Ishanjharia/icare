"""Prescription ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Prescription(Base):
    """Medication prescription issued by a clinician."""

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    medication: Mapped[str] = mapped_column(String(255))
    dosage: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text())
    language: Mapped[str] = mapped_column(String(32), default="en")
    translated_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
