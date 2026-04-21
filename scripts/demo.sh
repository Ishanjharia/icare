#!/usr/bin/env bash
# Run API + Vite + vitals simulator for local demo (run ./scripts/setup.sh first)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_ACT="$ROOT/icare/backend/.venv/bin/activate"
if [[ -f "$ROOT/icare/backend/.venv/Scripts/activate" ]]; then VENV_ACT="$ROOT/icare/backend/.venv/Scripts/activate"; fi
if [[ ! -f "$VENV_ACT" ]]; then
  echo "Run ./scripts/setup.sh first."
  exit 1
fi
# shellcheck disable=SC1091
source "$VENV_ACT"

PATIENT_ID="11111111-1111-4111-8111-111111111111"
if [[ -f "$ROOT/icare/backend/.demo_env" ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/icare/backend/.demo_env" || true
  set +a
  PATIENT_ID="${DEMO_PATIENT_ID:-$PATIENT_ID}"
fi

cleanup() {
  echo ""
  echo "Stopping demo processes…"
  for pid in $(jobs -p); do kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

echo "==> Starting FastAPI on :8000"
(cd "$ROOT/icare/backend" && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
sleep 2

echo "==> Starting Vite on :3000"
(cd "$ROOT/icare/frontend" && npm run dev -- --host 0.0.0.0 --port 3000) &
sleep 2

echo "==> Starting IoT simulator (normal scenario)"
(cd "$ROOT" && python icare/iot/simulator.py --patient-id "$PATIENT_ID" --scenario normal --api-url http://127.0.0.1:8000) &

echo ""
echo "I-CARE running at http://localhost:3000"
echo "API docs: http://127.0.0.1:8000/docs"
echo "Patient login: demo@patient.com / demo123"
echo "Press Ctrl+C to stop all processes."
echo ""

wait
