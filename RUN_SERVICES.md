# How to Run Services

## Prerequisites
- Docker & Docker Compose
- uv (for local development)

## Service Startup Order

### 1. Infrastructure (Docker)
```bash
# Start Redpanda (Kafka) and TimescaleDB
docker compose up -d redpanda timescaledb

# Verify health
docker compose ps
docker compose exec redpanda rpk cluster health
```

### 2. Physics Models (Docker) — produces synthetic telemetry to Kafka
```bash
# Build and start (produces to 4 Kafka topics: trajectory, telemetry, cross_model_state, ml_features;
# the `events` topic is reserved for the anomaly detector, not yet implemented)
docker compose up -d --build --force-recreate physics_models

# Verify it's producing (producer logs may not appear due to Docker stdout buffering)
docker exec telemetry-redpanda-1 rpk topic consume telemetry --num 5
```

### 3. Physics Models Consumer (Docker) — Kafka → TimescaleDB
```bash
docker compose up -d --build --force-recreate physics_models_consumer

# Verify it's inserting (should see "Inserted <topic> message for ..." per tick)
docker compose logs -f physics_models_consumer
```

### 4. Backend API (uv, runs on host port 8000)
```bash
# Runs FastAPI with 25 REST endpoints for real + synthetic data
uv run --package backend python -m backend.main

# Verify
curl http://localhost:8000/health
curl "http://localhost:8000/orion?limit=5"
curl "http://localhost:8000/close-approaches?limit=5"
curl "http://localhost:8000/iswa-goes-protons?limit=5"
curl "http://localhost:8000/donki?limit=5"
curl "http://localhost:8000/dsn-geometry?limit=5"
curl "http://localhost:8000/telemetry/synthetic/latest?limit=5"
```

### 5. Streamlit Prototype Dashboard (uv, runs on host port 8501)
```bash
# Consumes backend REST API
uv run --package streamlit_dashboard streamlit run dashboard/src/prototype/app.py --server.port 8501 --server.headless true

# Verify
curl http://localhost:8501/_stcore/health
# Open http://localhost:8501 in browser
```

### 6. (Optional) Pipelines — ingest real data into TimescaleDB
```bash
# NASA APIs: Orion ephemeris, DONKI events, GOES protons, DSN geometry, close approaches
uv run --package pipelines python -m pipelines.ingest.jpl_orion
uv run --package pipelines python -m pipelines.ingest.donki
uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons
uv run --package pipelines python -m pipelines.ingest.jpl_dsn_geometry
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# Local NASA source data: OEM ephemeris arcs + mission timeline (no network)
uv run --package pipelines python -m pipelines.ingest.nasa_oem
uv run --package pipelines python -m pipelines.ingest.mission_events  # DRAFT data
```

## Key Points
- **Never** `pip install` in system Python — use `uv run --package <pkg>` or Docker
- Physics models run **inside Docker** (connects to `redpanda:9092`)
- Backend & Dashboard run **on host** via `uv` (connect to `localhost:8000`, `localhost:5433`)
- Kafka topics must exist before physics models start (auto-created by Redpanda)
- TimescaleDB must be healthy before pipelines/physics_models start

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

Reference METs (official timeline): ICPS Sep 0/03:24 (12,240 s) · TLI ~1/01:37 (92,220 s) ·
Lunar SOI entry 4/06:59 · close approach 5/01:23:20 (433,400 s) · splashdown 9/01:46.

## Troubleshooting
| Issue | Fix |
|-------|-----|
| Backend 404 on `/telemetry/real/*` | Use correct paths: `/orion`, `/iswa-goes-protons`, `/donki`, `/dsn-geometry` |
| Dashboard can't connect to backend | Ensure backend is running on `localhost:8000` |
| No synthetic data in backend | Start the consumer: `docker compose up -d --build physics_models_consumer` (step 3); check `docker compose logs physics_models_consumer` for "Inserted" lines |
| Old (pre-normalization) Kafka messages show mixed-case fields (e.g. `solar_flux_W_m2`) | Historical junk from old runs; new messages are lowercase (`solar_flux_w_m2`). Consume from end (`-o end`) to verify |
| Redpanda connection refused | `docker compose restart redpanda` then wait for health check |