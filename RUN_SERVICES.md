# How to Run Services

The project has two kinds of data: **real data** (published by NASA/JPL, ingested by
`packages/pipelines` or read from `data/oem/`) and **synthetic data** (spacecraft
telemetry simulated by `packages/physics_models`). See "Real data vs synthetic data"
in the root `README.md`. Steps 0-1 are shared; step 3 is the real data path; steps 2 and 4-5 the
synthetic data path; steps 6-7 (backend + dashboard) serve both.

## Prerequisites
- Docker & Docker Compose
- uv (for local development)

## Quick start: everything in Docker

After the one-time setup (step 0), one command starts the whole app in order:
TimescaleDB and Redpanda → `migrate` (one-shot `alembic upgrade head`) → physics
models, consumer and backend → dashboard.
```bash
docker compose up -d --build

docker compose ps -a      # migrate shows "Exited (0)", the rest "Up" / "healthy"
curl http://localhost:8000/health
# Open http://localhost:8501
```
Then load the real data (step 3). Demo replay knobs work the same way, e.g.
`PHYSICS_MODELS_START_MET_SECONDS=12300 PHYSICS_MODELS_TIME_SCALE=60 docker compose up -d`.

The numbered steps below do the same thing piece by piece, and show how to run the
backend and dashboard natively (steps 6-7) while working on their code.

## Service Startup Order

### 0. One-time setup
Run from the **repo root**.
```bash
# Database credentials, read by Docker Compose and every host-side service
cp .env.example .env   # then set POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB

# One shared .venv with every workspace package
uv sync --all-packages
```

### 1. Infrastructure (Docker)
```bash
# Start Redpanda (Kafka) and TimescaleDB
docker compose up -d redpanda timescaledb

# Verify health
docker compose ps
docker compose exec redpanda rpk cluster health
```

### 2. Database Migration (required before consumer and backend)
Creates the nine synthetic telemetry hypertables; the real-data tables are created by their ingest jobs in step 3.
In Docker this is the `migrate` service, which the consumer and backend wait for:
```bash
docker compose up migrate    # runs alembic upgrade head, then exits
```
Or natively, starting from the **repo root** (Alembic runs from `packages/backend`, where `alembic.ini` lives):
```bash
cd packages/backend
uv run --package backend alembic upgrade head
cd ../..
```

### 3. Real data — ingest jobs into TimescaleDB
Run from the **repo root**. These populate the tables that the backend real-data endpoints serve.
```bash
# NASA APIs: Orion and Moon ephemeris, DONKI events, GOES protons, DSN geometry,
# close approaches (API only, not shown on the dashboard)
uv run --package pipelines python -m pipelines.ingest.jpl_orion
uv run --package pipelines python -m pipelines.ingest.jpl_moon
uv run --package pipelines python -m pipelines.ingest.donki
uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons
uv run --package pipelines python -m pipelines.ingest.jpl_dsn_geometry
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# Local NASA source data: OEM ephemeris arcs + mission timeline (no network)
uv run --package pipelines python -m pipelines.ingest.nasa_oem
uv run --package pipelines python -m pipelines.ingest.mission_events  # DRAFT data
```

#### Or scheduled by Airflow (Docker, profile `airflow`)
Airflow runs the same commands as DAGs (`airflow/dags/`): `real_data_backfill` (manual
trigger, every source above) and `real_data_refresh` (daily: DONKI, GOES protons, JPL
CAD; the mission ephemeris and timeline are final). Tasks run strictly one at a time
(JPL fair use), and a failed source doesn't stop the others. Airflow keeps its own
metadata in an `airflow` database on the same TimescaleDB, created by `airflow-init`.
```bash
docker compose --profile airflow up -d --build   # the whole app plus Airflow

# UI: http://localhost:8080 (user admin, password AIRFLOW_ADMIN_PASSWORD, default "admin")
# Load all real data once (or use the ▶ button on real_data_backfill in the UI):
docker compose exec airflow-scheduler airflow dags trigger real_data_backfill
docker compose exec airflow-scheduler airflow dags list-runs real_data_backfill
```
The UI is published on `127.0.0.1` only; on a server, open it through
`ssh -L 8080:localhost:8080 <server>`. Task logs are in the UI (or the `airflow_logs`
volume). The DAG unit tests need Airflow, so they run in its image:
`docker compose run --rm --build airflow-tests`.

### 4. Synthetic data — physics models (Docker) produce telemetry to Kafka
```bash
# Build and start (produces to 4 Kafka topics: trajectory, telemetry, cross_model_state, ml_features;
# the `events` topic is reserved for the anomaly detector, not yet implemented)
docker compose up -d --build --force-recreate physics_models

# Demo tip: the simulated Orion only moves once NASA's OEM trajectory data starts
# (Apr 2 02:00 UTC = 12,300 s after liftoff; before that the state engine holds it at the
# first OEM point). To watch it fly on the dashboard, start there and speed up 60x
# (1 tick/s stays; each tick covers 60 s of mission, so the 9-day flight takes ~3.5 h):
#   PHYSICS_MODELS_START_MET_SECONDS=12300 PHYSICS_MODELS_TIME_SCALE=60 docker compose up -d --force-recreate physics_models

# Verify it's producing (producer logs may not appear due to Docker stdout buffering)
docker exec telemetry-redpanda-1 rpk topic consume telemetry --num 5
```

### 5. Synthetic data — consumer (Docker) writes Kafka → TimescaleDB
```bash
docker compose up -d --build --force-recreate physics_models_consumer

# Verify it's inserting (should see "Inserted <topic> message for ..." per tick)
docker compose logs -f physics_models_consumer
```

### 6. Backend API (host port 8000)
In Docker: `docker compose up -d --build backend` (starts `migrate` first).

Natively, for working on the backend code: stop the container first
(`docker compose stop backend dashboard`, they share the ports), then from the **repo root**:
```bash
# Runs FastAPI with 28 REST endpoints for real + synthetic data.
# BACKEND_RELOAD=1 turns on auto-reload (off by default: a dead reloader can leave
# its worker holding port 8000).
uv run --package backend python -m backend.main

# Verify (interactive API docs: http://localhost:8000/docs)
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl "http://localhost:8000/orion?limit=5"
curl "http://localhost:8000/close-approaches?limit=5"
curl "http://localhost:8000/iswa-goes-protons?limit=5"
curl "http://localhost:8000/donki?limit=5"
curl "http://localhost:8000/dsn-geometry?limit=5"
curl "http://localhost:8000/telemetry/synthetic/latest?limit=5"
```

### 7. Digital Twin dashboard (host port 8501)

Source: `dashboard/src/prototype`. Shows synthetic data with real data alongside, all
read through the backend REST API (step 6 must be running). It finds the backend via
`BACKEND_URL` (default `http://localhost:8000`; the container uses `http://backend:8000`).
The earlier real-data-only Data Explorer was retired (`docs/decisions/ONE_DASHBOARD.md`).

In Docker: `docker compose up -d --build dashboard` (starts the backend first).

Natively, from the **repo root** (after `docker compose stop dashboard`):
```bash
# `dashboard` is a virtual workspace member that only declares the dashboard's deps
uv run --package dashboard streamlit run dashboard/src/prototype/app.py --server.port 8501 --server.headless true

# Verify
curl http://localhost:8501/_stcore/health
# Open http://localhost:8501 in browser
```

## Key Points
- **Never** `pip install` in system Python — use `uv run --package <pkg>` or Docker
- Physics models run **inside Docker** (connects to `redpanda:9092`)
- Backend & dashboard run **in Docker** by default (backend at `timescaledb:5432`, dashboard at
  `BACKEND_URL=http://backend:8000`); run natively via `uv` they use `localhost:5433` / `localhost:8000`
- Kafka topics must exist before physics models start (auto-created by Redpanda)
- TimescaleDB must be healthy before pipelines/physics_models start; Compose waits for it,
  and for `migrate` before the consumer and backend
- Airflow is **opt-in** (`--profile airflow`); a plain `docker compose up` doesn't start it.
  Its ingest tasks reach the database at `timescaledb:5432` (container `DATABASE_URL`)

## Demo Replay Controls (physics_models)
The simulator replays the mission from liftoff on the sim clock. Ticks stay 1 Hz on the
wall clock; two knobs control in-mission speed and offset (also in `configs/*.yaml` as
`time_scale` / `start_met_seconds`; env vars override):

```bash
# ×300 acceleration (mission day 5 reached in ~24 min)
PHYSICS_MODELS_TIME_SCALE=300 docker compose up -d --force-recreate physics_models

# Seek to lunar close approach (MET 5d 1h 23m = 433,800 s), then watch at real-time
PHYSICS_MODELS_START_MET_SECONDS=433800 docker compose up -d --force-recreate physics_models

# Both at once: flyby starts ~now, running fast
PHYSICS_MODELS_TIME_SCALE=300 PHYSICS_MODELS_START_MET_SECONDS=430000 docker compose up -d --force-recreate physics_models

# Back to real-time 1:1 replay
docker compose up -d --force-recreate physics_models
```
Thermal/power dynamics scale with sim time (heater cycles, SOC curves stay physically
meaningful); dashboards just plot the sim timestamps — nothing to change there.

**Seeking backwards is safe.** Synthetic tables are keyed on the sim `timestamp_utc`,
but each row also records when it was written (`ingested_at`, refreshed on every
upsert), and the Digital Twin dashboard shows the most recently *written* rows. A
restart at an earlier MET than a previous run reached therefore shows up live right
away; the live pages also hide that previous run's leftover later rows. This needs the
`d5159fa9708e` migration (step 2) applied before the consumer starts. To clear old runs
anyway (e.g. to free space), truncate the synthetic tables:

```bash
docker compose exec timescaledb psql -U telemetry -d telemetry -c "TRUNCATE state_snapshot, thermal_output, power_output, comms_output, radiation_output, cross_model_state, telemetry_packet, anomaly_events, ml_feature_vectors;"
```

**The first ~3 h 23 min after liftoff are static.** The NASA OEM arc starts at
Apr 2 01:57:37 UTC (MET 12,157 s); before that the state engine clamps to the arc's
first point, so position and distance from Earth do not change. Start at
`PHYSICS_MODELS_START_MET_SECONDS=12300` or later to see Orion move immediately.

Reference METs (official timeline): ICPS Sep 0/03:24 (12,240 s) · TLI ~1/01:37 (92,220 s) ·
Lunar SOI entry 4/06:59 · close approach 5/01:23:20 (433,400 s) · splashdown 9/01:46.

## Stopping Services

### Stop Docker containers
```bash
# Stop every service (including the backend, dashboard and Airflow containers)
docker compose down

# Stop only Airflow, keep the rest running
docker compose --profile airflow stop airflow-apiserver airflow-scheduler airflow-dag-processor

# Full reset — also delete DB volume and Kafka topics (start from scratch). This also
# deletes Airflow's run history (its `airflow` database lives in the same volume) and
# the real data, so trigger real_data_backfill again afterwards.
docker compose down -v
```

### Stop host processes (backend & dashboard, when run natively)
Press `Ctrl+C` in the terminal running each one. If one was started in the background:
```bash
# macOS / Linux
pkill -f "uv run --package backend python -m backend.main"   # Backend API (port 8000)
pkill -f "streamlit run"                                      # Dashboards (port 8501)
```
```powershell
# Windows (PowerShell)
# Match on the command line, NOT on the port: when the containers publish 8000/8501,
# the process owning those ports is Docker Desktop itself, and killing it crashes Docker.
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "backend\.main|streamlit(\.exe)?\W+run" -and $_.CommandLine -notmatch "Get-CimInstance" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Verify nothing is left running
```bash
# Check Docker
docker compose ps

# Check host ports (macOS / Linux)
lsof -i :8000
lsof -i :8501
```
```powershell
# Check host ports (Windows)
Get-NetTCPConnection -LocalPort 8000,8501 -State Listen
```

## Troubleshooting
| Issue | Fix |
|-------|-----|
| Backend 404 on `/telemetry/real/*` | Use correct paths: `/orion`, `/iswa-goes-protons`, `/donki`, `/dsn-geometry` |
| Dashboard can't connect to backend | Ensure the backend is running (`docker compose ps backend`, or the native one on `localhost:8000`); the error names the URL tried, set by `BACKEND_URL` |
| Backend/consumer never start, `migrate` exited non-zero | `docker compose logs migrate` (usually the DB credentials in `.env`) |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | A native backend/dashboard is still running; stop it (see "Stopping Services") or run only the native one |
| No synthetic data in backend | Start the consumer: `docker compose up -d --build physics_models_consumer` (step 5); check `docker compose logs physics_models_consumer` for "Inserted" lines |
| Old (pre-normalization) Kafka messages show mixed-case fields (e.g. `solar_flux_W_m2`) | Historical junk from old runs; new messages are lowercase (`solar_flux_w_m2`). Consume from end (`-o end`) to verify |
| Redpanda connection refused | `docker compose restart redpanda` then wait for health check |
| `ModuleNotFoundError` (`contracts`, `httpx`, `fastapi`, ...) when starting a host service | A partial `uv sync --package <pkg>` pruned the shared `.venv`; run `uv sync --all-packages` |
| `RuntimeError: DATABASE_URL or POSTGRES_USER, ... must be set` | Create `.env` from `.env.example` in the repo root (step 0) |
| Native `uv run` fails with `Access is denied` on `.venv/lib64` (Windows) | A Linux container wrote a Unix-style `.venv`; delete `.venv` and run `uv sync --all-packages` again |
| Airflow services never start, `airflow-init` exited non-zero | `docker compose --profile airflow logs airflow-init` (usually the DB credentials in `.env`) |
| Airflow login rejected after changing `AIRFLOW_ADMIN_PASSWORD` | The password is applied by `airflow-init`: `docker compose --profile airflow up -d --force-recreate airflow-init` |
| Airflow task failed | Open the task in the UI's Grid view → **Logs** (the ingest module's own output and traceback); fix, then **Clear** the task to re-run it |
