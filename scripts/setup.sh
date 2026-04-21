#!/usr/bin/env bash
# I-CARE one-time / repeat local setup (Linux, macOS, or Git Bash on Windows)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> I-CARE setup from $ROOT"

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }

need_cmd python3
need_cmd node
need_cmd npm

PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYMAJ="$(echo "$PYVER" | cut -d. -f1)"
PYMIN="$(echo "$PYVER" | cut -d. -f2)"
if [[ "$PYMAJ" -lt 3 ]] || [[ "$PYMAJ" -eq 3 && "$PYMIN" -lt 11 ]]; then
  echo "Python 3.11+ required (found $PYVER)"
  exit 1
fi

NODEVER="$(node -p "process.versions.node.split('.')[0]")"
if [[ "${NODEVER:-0}" -lt 18 ]]; then
  echo "Node.js 18+ required (found $(node -v))"
  exit 1
fi

echo "==> Checking Ollama (optional but recommended)"
if command -v ollama >/dev/null 2>&1; then
  if curl -sf http://localhost:11434/api/tags >/dev/null; then
    echo "    Ollama reachable — pulling models (may take a while)…"
    ollama pull biomistral 2>/dev/null || ollama pull biomistral:latest || echo "    (warn) biomistral pull skipped or failed"
    ollama pull llama3.2 2>/dev/null || ollama pull llama3.2:latest || echo "    (warn) llama3.2 pull skipped or failed"
  else
    echo "    Ollama binary found but server not responding on :11434 — start Ollama then re-run pulls."
  fi
else
  echo "    Ollama not installed — AI/voice features need it (https://ollama.com)."
fi

echo "==> CUDA check (optional)"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L || true
else
  echo "    nvidia-smi not found — Whisper/Ollama will use CPU if configured."
fi

echo "==> Python dependencies (backend)"
cd "$ROOT/icare/backend"
python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
if [[ -f .venv/Scripts/activate ]]; then source .venv/Scripts/activate; elif [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; else echo "venv activate script not found"; exit 1; fi
pip install -U pip wheel
pip install -r requirements.txt

echo "==> Frontend dependencies"
cd "$ROOT/icare/frontend"
npm install

echo "==> Environment files"
if [[ ! -f "$ROOT/icare/backend/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/icare/backend/.env"
  echo "    Created icare/backend/.env from .env.example — review SECRET_KEY and tokens."
else
  echo "    icare/backend/.env already exists — skipped."
fi

if [[ ! -f "$ROOT/icare/frontend/.env.local" ]]; then
  {
    echo "VITE_API_BASE_URL="
    echo "VITE_DEFAULT_PATIENT_ID=11111111-1111-4111-8111-111111111111"
  } > "$ROOT/icare/frontend/.env.local"
  echo "    Created icare/frontend/.env.local (demo patient UUID)."
fi

echo "==> SQLite schema + demo seed (no Alembic — tables via SQLAlchemy create_all)"
cd "$ROOT/icare/backend"
if [[ -f .venv/Scripts/activate ]]; then source .venv/Scripts/activate; else source .venv/bin/activate; fi
python -m scripts.seed_data

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  I-CARE setup finished."
echo ""
echo "  Start the demo stack:"
echo "    ./scripts/demo.sh"
echo ""
echo "  Or with Docker:"
echo "    docker compose up --build"
echo ""
echo "  Then open http://localhost:3000 (demo.sh) or http://localhost:5173 (npm run dev default)"
echo "  Login: demo@patient.com / demo123  |  Doctor: demo@doctor.com / demo123"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
