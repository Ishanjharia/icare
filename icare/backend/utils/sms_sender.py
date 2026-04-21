"""Fast2SMS outbound SMS (stub)."""

from __future__ import annotations

from typing import Any


class SmsSender:
    """Thin wrapper over httpx + Fast2SMS."""

    async def send_sms(self, numbers: list[str], message: str) -> dict[str, Any]:
        """Send SMS to one or more Indian mobile numbers."""
        ...
