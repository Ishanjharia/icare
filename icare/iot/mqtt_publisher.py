"""MQTT publisher for IoT vitals devices."""

from typing import Any


class MQTTPublisher:
    """Publish vitals topics to a local or edge broker."""

    async def publish_vitals(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a JSON-serializable vitals payload."""
        ...
