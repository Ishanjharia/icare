"""Patient health profile (one row per user)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class HealthProfile(Base):
    """Extended health information linked to a user account."""

    __tablename__ = "health_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    blood_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    height: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date(), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text(), nullable=True)
    chronic_conditions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text(), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    caregiver_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_doctor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smoking_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    alcohol_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exercise_frequency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="health_profile")
