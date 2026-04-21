# I-CARE (cloud skeleton)

IoT-oriented, cloud-based, AI-assisted remote healthcare web app — **skeleton only** (no business logic yet).

- **Backend**: `backend/` — FastAPI, PostgreSQL (asyncpg), Groq, InfluxDB Cloud, Alembic.
- **Frontend**: `frontend/` — React 18, TypeScript, Vite, Tailwind, TanStack Query, Recharts.

Copy `icare/.env.example` to `icare/backend/.env`, fill secrets, then implement services and routers.

See `icare/.cursorrules` for architecture rules and folder layout.

## Demo: vitals simulator & alerts

Wearable data is ingested over HTTPS (`POST /api/vitals/ingest`). For demos without a physical device:

1. Sign in as a **patient** (or as a doctor with the patient UUID in the sidebar).
2. Navigate to **`/simulator`** (not shown in the main nav).
3. Enter your **patient ID**, choose **HR spike**, click **Start simulation** — every 3 seconds the page POSTs vitals using your JWT; open **Dashboard** or **Alerts** in another tab to watch the pipeline.
4. Or click **Start server simulation (60s)** to call **`POST /api/vitals/simulate`** with `{ patient_id, scenario, duration_seconds }` so the backend emits readings for 60 seconds while this page is closed.

Example: *Navigate to `/simulator`, enter your patient ID, select HR Spike scenario, and watch the alert pipeline trigger on the dashboard.*
