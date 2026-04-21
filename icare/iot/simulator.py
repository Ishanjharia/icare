"""Development vitals simulator (HTTP → ``/api/vitals/ingest``).

Scenarios exercise threshold logic and (when the FastAPI app is running) the
background alert escalation worker (L1→L2 @ 60s, L2→L3 @ 120s, …) for
unacknowledged alerts.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_IOT_DIR = Path(__file__).resolve().parent
if str(_IOT_DIR) not in sys.path:
    sys.path.insert(0, str(_IOT_DIR))

import httpx

from vitals_client import post_vital_ingest


async def _post(
    client: httpx.AsyncClient,
    base: str,
    pid: uuid.UUID,
    metric: str,
    value: float,
    unit: str | None,
    source: str,
    token: str | None,
) -> None:
    r = await post_vital_ingest(
        client,
        base,
        pid,
        {"metric": metric, "value": value, "unit": unit, "timestamp": datetime.now(timezone.utc), "source": source},
        jwt_token=token,
    )
    r.raise_for_status()


async def run_normal(
    client: httpx.AsyncClient,
    base: str,
    pid: uuid.UUID,
    token: str | None,
    interval: float,
    iterations: int,
) -> None:
    t0 = 0.0
    for i in range(iterations):
        ts = datetime.now(timezone.utc)
        hr = 72 + 6 * math.sin(t0 / 4) + random.uniform(-2, 2)
        spo2 = 97 + random.uniform(-0.8, 0.8)
        sys_bp = 118 + random.uniform(-4, 4)
        dia_bp = 78 + random.uniform(-3, 3)
        steps = 2000 + i * 15 + random.randint(0, 20)
        if random.random() < 0.08:
            hr += random.uniform(8, 14)
        await _post(client, base, pid, "hr", round(hr, 1), "bpm", "simulator", token)
        await _post(client, base, pid, "spo2", round(spo2, 1), "%", "simulator", token)
        await _post(client, base, pid, "bp_sys", round(sys_bp, 1), "mmHg", "simulator", token)
        await _post(client, base, pid, "bp_dia", round(dia_bp, 1), "mmHg", "simulator", token)
        await _post(client, base, pid, "steps", float(steps), "count", "simulator", token)
        t0 += interval
        await asyncio.sleep(interval)


async def run_hr_spike(
    client: httpx.AsyncClient,
    base: str,
    pid: uuid.UUID,
    token: str | None,
    wait_seconds: float,
) -> None:
    """Post sustained high HR to create a level-1 alert; keep server time for escalation."""
    print("Posting HR spike (142 bpm) to breach alert_high …")
    for _ in range(5):
        await _post(client, base, pid, "hr", 142.0, "bpm", "simulator_hr_spike", token)
        await asyncio.sleep(2.0)
    print(
        f"Alert should be active. With uvicorn + FastAPI BackgroundTasks, escalation runs in-process: "
        f"wait ~{int(wait_seconds)}s to observe L1→L2→L3 (do not acknowledge the alert in the UI).",
    )
    step = 15.0
    elapsed = 0.0
    while elapsed < wait_seconds:
        await asyncio.sleep(step)
        elapsed += step
        print(f"  … {elapsed:.0f}s / {wait_seconds:.0f}s")


async def run_spo2_drop(
    client: httpx.AsyncClient,
    base: str,
    pid: uuid.UUID,
    token: str | None,
) -> None:
    print("Posting SpO2 drop (89%) …")
    for _ in range(6):
        await _post(client, base, pid, "spo2", 89.0, "%", "simulator_spo2_drop", token)
        await asyncio.sleep(2.0)


async def main_async(args: argparse.Namespace) -> None:
    base = args.api_url.rstrip("/")
    token = args.token.strip() or None
    if not token:
        print("Warning: no JWT (--token or ICARE_JWT_TOKEN). Ingest may return 401 if auth is required.", flush=True)
    pid = args.patient_id
    async with httpx.AsyncClient() as client:
        if args.scenario == "normal":
            await run_normal(client, base, pid, token, args.interval, args.iterations)
        elif args.scenario == "hr_spike":
            await run_hr_spike(client, base, pid, token, args.wait)
        elif args.scenario == "spo2_drop":
            await run_spo2_drop(client, base, pid, token)
    print("Done.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="I-CARE vitals simulator (demo alert pipeline via /api/vitals/ingest)",
    )
    p.add_argument(
        "--patient-id",
        type=uuid.UUID,
        required=True,
        help="Patient UUID (same as users.id in SQLite)",
    )
    p.add_argument(
        "--scenario",
        choices=("normal", "hr_spike", "spo2_drop"),
        default="normal",
        help="normal=random walk; hr_spike=breach HR thresholds; spo2_drop=low SpO2",
    )
    p.add_argument("--api-url", default=os.environ.get("ICARE_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--token", default=os.environ.get("ICARE_JWT_TOKEN", ""), help="Bearer JWT for /api/vitals/ingest")
    p.add_argument("--interval", type=float, default=2.0, help="Seconds between normal-scenario batches")
    p.add_argument("--iterations", type=int, default=30, help="Batches for normal scenario")
    p.add_argument(
        "--wait",
        type=float,
        default=130.0,
        help="Seconds to wait after hr_spike posts (escalation L3 ~120s)",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
