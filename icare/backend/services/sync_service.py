"""InfluxDB / edge / queue sync (stub)."""

from __future__ import annotations

import uuid
from typing import Any


class SyncService:
    """Bridge local vitals edge to cloud."""

    async def enqueue_vitals(self, patient_id: uuid.UUID, payload: dict[str, Any]) -> int:
        """Push vitals into processing queue."""
        ...

    async def flush_queue_batch(self, *, batch_size: int = 100) -> int:
        """Drain queue to InfluxDB / downstream."""
        ...

    async def write_to_influx(
        self,
        patient_id: uuid.UUID,
        metric: str,
        value: float,
        *,
        unit: str | None = None,
        source: str | None = None,
    ) -> None:
        """Write a point to InfluxDB Cloud measurement ``patient_vitals``."""
        ...
