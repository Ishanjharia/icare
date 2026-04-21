"""Chat / streaming AI schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """User message with optional conversation turns (role: user|assistant, content: str)."""

    message: str = Field(..., min_length=1, max_length=8000)
    language: str = Field(default="English", max_length=64)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    patient_id: uuid.UUID | None = Field(
        default=None,
        description="Required when caller is a doctor; scopes health context to that patient.",
    )
