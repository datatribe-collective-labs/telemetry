# Telemetry Project - Data Tribe

Open-source telemetry project building a **digital twin of NASA's Artemis II /
Orion spacecraft** from publicly available NASA/JPL data.

**What it provides:**

- Batch ingestion of public NASA/JPL APIs and NASA source files into TimescaleDB
- Synthetic spacecraft telemetry from physics models (state, thermal, power),
  streamed through Redpanda (Kafka) and persisted to TimescaleDB
- A FastAPI REST API over both real and synthetic data
- Streamlit dashboards for monitoring and visualization

The repo holds two related efforts:

1. **Digital twin** (the final target) - `packages/contracts` (ODCS data
   contracts + Pydantic models), `packages/physics_models` (synthetic telemetry
   generators + Kafka producer/consumer), `packages/backend` (FastAPI), and the
   Streamlit prototype in `dashboard/src/prototype/`. State engine, thermal and
   power are implemented; comms, radiation, packet assembler and anomaly/ML are
   still placeholders.
2. **Pipeline explorer** - `packages/pipelines` + `packages/streamlit_dashboard`:
   a lightweight ETL that ingests each public source into its own table and shows
   one dashboard page per source. It does not depend on `contracts` or `backend`.

More docs: [`docs/README.md`](docs/README.md) (index),
[`RUN_SERVICES.md`](RUN_SERVICES.md) (full startup order and troubleshooting),
[`packages/backend/README.md`](packages/backend/README.md) (API reference).

## Architecture Diagram

```mermaid
flowchart LR
    subgraph Sources["Public NASA / JPL data"]
        CAD(["JPL CAD API"])
        HZN(["JPL Horizons\nOrion + DSN geometry"])
        DONKI(["NASA DONKI"])
        ISWA(["NASA iSWA HAPI\nGOES protons"])
        OEM(["NASA OEM arcs\ndata/oem (local)"])
        EVT(["Mission timeline\n(local, draft)"])
    end

    Ingest["pipelines.ingest.*\n(batch, uv run)"]
    Physics["physics_models\nstate / thermal / power"]
    Kafka[["Redpanda (Kafka)"]]
    Consumer["physics_models_consumer"]
    DB[("TimescaleDB")]
    API["backend\nFastAPI :8000"]
    Explorer["Pipeline explorer\nStreamlit :8501"]
    Proto["Digital twin prototype\nStreamlit :8501"]

    CAD & HZN & DONKI & ISWA & OEM & EVT --> Ingest --> DB
    OEM --> Physics --> Kafka --> Consumer --> DB
    DB --> API --> Proto
    DB --> Explorer

    subgraph Docker["Docker"]
        DB
        Kafka
        Physics
        Consumer
    end
```

**Data sources** (one ingest module and one table each):

| Source | Ingest module | Table |
|--------|---------------|-------|
| [JPL Close-Approach Data (CAD)](https://ssd-api.jpl.nasa.gov/doc/cad.html) - asteroid/comet close approaches | `jpl_cad` | `close_approaches` |
| [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) - Artemis II Orion ephemeris | `jpl_orion` | `orion_ephemeris` |
| JPL Horizons - Orion geometry as seen from the DSN sites | `jpl_dsn_geometry` | `dsn_site_geometry` |
| [NASA CCMC DONKI](https://ccmc.gsfc.nasa.gov/DONKI-API/get/) - space weather events (CME, SEP, FLR, GST, HSS, ...) | `donki` | `donki_events` |
| [NASA CCMC iSWA HAPI](https://iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi/) - GOES integral proton flux | `iswa_goes_protons` | `goes_integral_protons` |
| NASA OEM ephemeris arcs (`data/oem/`, no network) | `nasa_oem` | `oem_state_vectors` |
| Artemis II mission timeline (curated, **draft** data, no network) | `mission_events` | `mission_events` |

The synthetic telemetry tables (`state_snapshot`, `thermal_output`,
`power_output`, `comms_output`, `radiation_output`, `cross_model_state`,
`telemetry_packet`, `anomaly_events`, `ml_feature_vectors`) are created by the
backend's Alembic migration and filled by `physics_models_consumer`.

## What runs where

- **In Docker** (`docker-compose.yml`): `timescaledb` (host port **5433**, not
  5432 - a native Postgres install commonly already owns 5432), `redpanda`
  (Kafka on `:9092`), `physics_models` (producer) and `physics_models_consumer`,
  plus the on-demand `tests` service (see "Tests" below).
- **Natively via `uv run`**: the ingest jobs, the backend API (`:8000`) and the
  Streamlit dashboards (`:8501`). They talk to the Dockerized database over
  `localhost:5433`.

## How to run

Prerequisites: Docker (with Compose) and [`uv`](https://docs.astral.sh/uv/).
Run all commands from the **repo root** unless noted.

### 0. One-time setup

```bash
cp .env.example .env        # then set POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
uv sync --all-packages      # one shared .venv with every workspace package
```

`.env` is read by Docker Compose, the ingest jobs, the backend and the
dashboards. `DATABASE_URL` is optional; without it, host-side tools connect to
`localhost:5433` using the three `POSTGRES_*` values.

### Option A - Pipeline explorer only (real data, no Kafka)

```bash
# 1. Database
docker compose up -d timescaledb

# 2. Ingest whichever sources you want (each job creates its own table)
uv run --package pipelines python -m pipelines.ingest.jpl_cad
uv run --package pipelines python -m pipelines.ingest.jpl_orion
uv run --package pipelines python -m pipelines.ingest.jpl_dsn_geometry
uv run --package pipelines python -m pipelines.ingest.donki
uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons

# 3. Dashboard -> http://localhost:8501
uv run --package streamlit_dashboard streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py
```

Pages: Welcome, Close Approaches, Artemis II Orion, DSN Coverage, NASA DONKI,
GOES Proton Flux.

### Option B - Full digital twin (synthetic telemetry + API + prototype dashboard)

```bash
# 1. Infrastructure
docker compose up -d timescaledb redpanda

# 2. Create the synthetic telemetry tables (before the consumer and the backend)
cd packages/backend
uv run --package backend alembic upgrade head
cd ../..

# 3. Real data for the backend's real-data endpoints: the Option A ingest jobs, plus
uv run --package pipelines python -m pipelines.ingest.nasa_oem
uv run --package pipelines python -m pipelines.ingest.mission_events

# 4. Physics models -> Redpanda -> TimescaleDB
docker compose up -d --build physics_models physics_models_consumer

# 5. Backend API -> http://localhost:8000 (interactive docs at /docs)
uv run --package backend python -m backend.main

# 6. Prototype dashboard, in a second terminal -> http://localhost:8501
uv run streamlit run dashboard/src/prototype/app.py
```

Prototype pages: Overview / Health, Trajectory, Thermal, Power, Space Weather,
DSN Coverage. Both dashboards default to port 8501, so run one at a time or pass
`--server.port 8502` to the second.

The simulator replays the mission from liftoff in real time. To speed it up or
jump ahead, set `PHYSICS_MODELS_TIME_SCALE` / `PHYSICS_MODELS_START_MET_SECONDS`
(see "Demo Replay Controls" in [`RUN_SERVICES.md`](RUN_SERVICES.md)). That file
also covers health checks, stopping services and troubleshooting.

### Ingest options

```bash
uv run --package pipelines python -m pipelines.ingest.jpl_cad --date-min now --date-max +60 --dist-max 0.05 --body Earth
uv run --package pipelines python -m pipelines.ingest.donki --start-date 2026-04-01 --end-date 2026-04-10 --event-type CME --event-type SEP --request-delay 0.2
uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons --start 2026-04-01T00:00:00Z --end 2026-04-12T00:00:00Z
```

Run any ingest module with `--help` for its full option list.

## Checking the data

Query the `timescaledb` container directly - no local `psql` client needed
(replace `telemetry` with your `POSTGRES_USER` / `POSTGRES_DB` if they differ):

```
docker compose exec timescaledb psql -U telemetry -d telemetry -c "\dt"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT des, close_approach_time, dist_au, v_rel_kms FROM close_approaches ORDER BY close_approach_time LIMIT 10;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM orion_ephemeris;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM dsn_site_geometry;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT event_type, count(*) FROM donki_events GROUP BY event_type ORDER BY count DESC;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*), min(time), max(time), max(p10_pfu) FROM goes_integral_protons;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM oem_state_vectors;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*), max(timestamp_utc) FROM telemetry_packet;"
```

You can also query through the API, e.g. `curl "http://localhost:8000/orion?limit=5"`
or `curl http://localhost:8000/telemetry/synthetic/latest`, or connect any
Postgres GUI client (DBeaver, TablePlus, pgAdmin, ...) to `localhost:5433`.

## Tests

```
tests/
├── unit/
    └── <package>/<module path>/
        ├── conftest.py            # fixtures for that module's tests
        └── test_<function>.py     # one file per function under test
└── integration/
      └── <package>/<module path>/test_<feature>.py
```

Each test file covers one function (e.g.
`tests/unit/pipelines/ingest/jpl_cad/test_fetch_close_approaches.py` tests
`pipelines.ingest.jpl_cad.fetch_close_approaches`), and every test is named
`test_<function>_<expected behavior>`. HTTP calls are mocked with
`responses`, database connections with `unittest.mock.MagicMock`.

Unit tests cover all pipeline ingest modules, the backend (`tests/unit/backend`)
and the physics models (`tests/unit/physics_models`).

```
# in Docker - from the repo root
docker compose run --rm tests

# or natively - also from the repo root
uv sync --all-packages   # ensure the shared root venv has every workspace package
uv run pytest tests/unit
```

The root `uv run pytest` reuses the single shared `.venv`. A partial
`uv sync --package <pkg>` can prune other workspace packages from it, making
imports like `pydantic`/`fastapi` fail at test collection. Run
`uv sync --all-packages` first if you hit `ModuleNotFoundError` in tests.

Live datasource and database checks belong under `tests/integration/` and have
their own datasource-specific runner.

## Adding another data source

The dashboard is structured as one Streamlit page per JPL data source
(`packages/streamlit_dashboard/src/streamlit_dashboard/`):

- `data/` - one query module per source (e.g. `data/close_approaches.py`),
  plus the shared `data/engine.py` (`get_engine()`, cached with
  `st.cache_resource`)
- `pages/` - one page per source, wired into the sidebar nav via
  `st.Page(...)` in `app.py`

To add a new source: add its ingest job under
`packages/pipelines/src/pipelines/ingest/`, a matching `data/<source>.py`
query module, a `pages/<source>.py` page, and register the page in the
`pages` list in `app.py`. Add unit tests for the ingest job under
`tests/unit/pipelines/ingest/<source>/`, following the layout in "Tests" above.
