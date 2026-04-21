"""BLE wearable discovery and heart-rate streaming (bleak → FastAPI vitals)."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

_IOT_DIR = Path(__file__).resolve().parent
if str(_IOT_DIR) not in sys.path:
    sys.path.insert(0, str(_IOT_DIR))

from datetime import datetime, timezone
import httpx

try:
    from bleak import BleakClient, BleakScanner
except ImportError as _e:  # pragma: no cover
    BleakClient = None  # type: ignore[misc, assignment]
    BleakScanner = None  # type: ignore[misc, assignment]
    _BLEAK_IMPORT_ERROR = _e
else:
    _BLEAK_IMPORT_ERROR = None

from vitals_client import post_vital_ingest


def _parse_heart_rate_measurement(data: bytes) -> int | None:
    """Bluetooth SIG heart-rate measurement (flags + UINT8 or UINT16 BPM)."""
    if len(data) < 2:
        return None
    flags = data[0]
    if flags & 0x01:
        if len(data) < 3:
            return None
        return int.from_bytes(data[1:3], byteorder="little", signed=False)
    return int(data[1])


class BLEScanner:
    """Discover HR peripherals and forward BPM to ``/api/vitals/ingest``."""

    HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
    HEART_RATE_CHAR = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(
        self,
        api_base_url: str | None = None,
        jwt_token: str | None = None,
    ) -> None:
        self.api_base_url = (api_base_url or os.environ.get("ICARE_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.jwt_token = (jwt_token or os.environ.get("ICARE_JWT_TOKEN", "") or "").strip() or None
        self._http: httpx.AsyncClient | None = None

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient()
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _require_bleak(self) -> None:
        if BleakScanner is None or BleakClient is None:
            raise RuntimeError(
                "bleak is required for BLEScanner. Install with: pip install bleak",
            ) from _BLEAK_IMPORT_ERROR

    async def scan_and_connect(self, timeout_seconds: float = 10.0) -> BleakClient | None:
        """Scan for ``timeout_seconds``, prefer devices advertising the HR service UUID."""
        self._require_bleak()
        assert BleakScanner is not None and BleakClient is not None

        target = self.HEART_RATE_SERVICE.lower()
        discovered = await BleakScanner.discover(timeout=timeout_seconds)
        hr_candidates: list = []
        any_devices: list = []
        for d in discovered:
            any_devices.append(d)
            uuids = {str(u).lower() for u in d.metadata.get("uuids", []) if u}
            if target in uuids:
                hr_candidates.append(d)
        chosen = hr_candidates[0] if hr_candidates else None
        if chosen is None and any_devices:
            # Fallback: names often contain "Heart" / "Polar" / "HR" on some stacks without UUID list.
            for d in any_devices:
                name = (d.name or "").lower()
                if any(k in name for k in ("heart", "hr", "polar", "garmin", "whoop")):
                    chosen = d
                    break
        if chosen is None:
            return None
        client = BleakClient(chosen)
        await client.connect()
        return client

    async def stream_heart_rate(
        self,
        patient_id: str,
        *,
        client: BleakClient | None = None,
    ) -> None:
        """
        Subscribe to HR notifications and POST each BPM to the API.

        If ``client`` is None, ``scan_and_connect()`` is used and disconnected on exit.
        """
        self._require_bleak()
        assert BleakClient is not None

        own_client = client is None
        cli = client or await self.scan_and_connect()
        if cli is None:
            return
        http = await self._ensure_http()
        pid = uuid.UUID(str(patient_id))

        async def _handler(_sender: object, data: bytearray) -> None:
            bpm = _parse_heart_rate_measurement(bytes(data))
            if bpm is None or bpm <= 0:
                return
            await post_vital_ingest(
                http,
                self.api_base_url,
                pid,
                {
                    "metric": "hr",
                    "value": float(bpm),
                    "unit": "bpm",
                    "timestamp": datetime.now(timezone.utc),
                    "source": "ble_hr",
                },
                jwt_token=self.jwt_token,
            )

        try:
            await cli.start_notify(self.HEART_RATE_CHAR, _handler)
            while cli.is_connected:
                await asyncio.sleep(0.5)
        finally:
            try:
                await cli.stop_notify(self.HEART_RATE_CHAR)
            except Exception:
                pass
            if own_client:
                await cli.disconnect()
            await self.aclose()


async def _cli_main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Stream BLE heart rate to I-CARE API")
    p.add_argument("--patient-id", type=uuid.UUID, required=True)
    p.add_argument("--api-url", default=os.environ.get("ICARE_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--token", default=os.environ.get("ICARE_JWT_TOKEN", ""))
    args = p.parse_args()
    scanner = BLEScanner(api_base_url=args.api_url, jwt_token=args.token or None)
    await scanner.stream_heart_rate(str(args.patient_id))


if __name__ == "__main__":
    asyncio.run(_cli_main())
