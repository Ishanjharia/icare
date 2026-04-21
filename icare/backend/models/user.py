"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    """Application user (patient, doctor, caregiver)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(64), server_default="Hindi", default="Hindi")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    health_profile: Mapped["HealthProfile | None"] = relationship(
        "HealthProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
