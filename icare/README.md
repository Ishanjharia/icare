# I-CARE (cloud skeleton)

IoT-oriented, cloud-based, AI-assisted remote healthcare web app — **skeleton only** (no business logic yet).

- **Backend**: `backend/` — FastAPI, PostgreSQL (asyncpg), Groq, InfluxDB Cloud, Alembic.
- **Frontend**: `frontend/` — React 18, TypeScript, Vite, Tailwind, TanStack Query, Recharts.

Copy `icare/.env.example` to `icare/backend/.env`, fill secrets, then implement services and routers.

See `icare/.cursorrules` for architecture rules and folder layout.

## Deploy: Render (API) + Vercel (frontend)

**Backend (Render)**  
- Root directory: `icare/backend`. The **`Procfile`** starts **`uvicorn` only** (no `alembic upgrade head` on boot — that was exiting with status 1 when `DATABASE_URL` was missing or unreachable). If you use PostgreSQL again, run migrations once from a shell or a one-off job: `alembic upgrade head`.  
- Optional: set **`DATABASE_URL`** for DB-backed routes (`postgresql+asyncpg://…` or `postgresql://…`). **URL-encode** special characters in the password (`@` → `%40`, `[` → `%5B`, `]` → `%5D`).  
- Set **`SECRET_KEY`**, **`DATABASE_URL`**, **`FRONTEND_URL`** (your Vercel URL(s), comma-separated). Optional: **`GROQ_*`**, **`INFLUXDB_*`**, **`FAST2SMS_API_KEY`** (defaults allow the process to boot; AI/SMS routes need real keys).  
- **`CORS_ORIGIN_REGEX`**: default in `config.py` allows Vercel preview hosts; set in `.env` to override or disable (empty string).

**Frontend (Vercel)**  
- Root directory: `icare/frontend`. Build: `npm run build`, output: **`dist`**.  
- Set **`VITE_API_URL`** to your Render API base (e.g. `https://your-api.onrender.com`) **with no trailing slash**. Without this, the SPA cannot reach `/api/auth/login` from the browser.  
- `vercel.json` rewrites client routes to `index.html` for React Router.

## Demo: vitals simulator & alerts

Wearable data is ingested over HTTPS (`POST /api/vitals/ingest`). For demos without a physical device:

1. Sign in as a **patient** (or as a doctor with the patient UUID in the sidebar).
2. Navigate to **`/simulator`** (not shown in the main nav).
3. Enter your **patient ID**, choose **HR spike**, click **Start simulation** — every 3 seconds the page POSTs vitals using your JWT; open **Dashboard** or **Alerts** in another tab to watch the pipeline.
4. Or click **Start server simulation (60s)** to call **`POST /api/vitals/simulate`** with `{ patient_id, scenario, duration_seconds }` so the backend emits readings for 60 seconds while this page is closed.

Example: *Navigate to `/simulator`, enter your patient ID, select HR Spike scenario, and watch the alert pipeline trigger on the dashboard.*
