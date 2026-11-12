# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A telemetry project building a spacecraft digital twin for NASA Artemis II /
Orion - real-time physics simulation (thermal, power, comms, radiation) fed by JPL
Horizons ephemeris and NASA telemetry, streamed through Kafka, validated against the
ODCS contracts in `packages/contracts/src/odcs/`, and surfaced on a dashboard.

Effort #1 (the digital twin) is partially built and runnable end-to-end (see
`RUN_SERVICES.md`, `docs/integration/PIPELINE_STATUS.md`, `docs/overview/PROJECT_OVERVIEW.md`): `packages/contracts`
contains Pydantic models matching the ODCS contracts; `packages/physics_models`
generates synthetic telemetry (state engine, thermal, power are implemented; comms,
radiation, packet assembler and anomaly/ML are still placeholders emitted by
`runner.py`); it publishes to Redpanda (Kafka) which a consumer persists into
TimescaleDB; `packages/backend` is a working FastAPI with 28 REST endpoints; and
`dashboard/src/prototype/` is a Streamlit Digital Twin v1 consuming the backend.
Superset was dropped - the dashboard strategy is Streamlit now, Vanilla JS +
Plotly.js later (see `docs/architecture/DASHBOARD_ARCHITECTURE.md`).

Effort #2 (the real data path: `packages/pipelines`) is a working lightweight
batch ETL that ingests public NASA/JPL APIs into TimescaleDB - the proven
small-scale version of the same ingest -> store -> visualize shape. Its data is
served by the backend and shown on the Digital Twin dashboard. See "Two efforts in
this repo" below before assuming any two packages are meant to talk to each other.

Docs use one vocabulary for this split: **real data** (published by NASA/JPL:
ingested tables + `data/oem/` files) vs **synthetic data** (simulated by
`physics_models`; tables under `/telemetry/synthetic/*` in the API). There is one
dashboard, the **Digital Twin dashboard** (`dashboard/src/prototype`, synthetic data
with real data alongside, reads the backend); every chart is badged Real / Synthetic /
Placeholder. The earlier real-data-only **Data Explorer** (`packages/streamlit_dashboard`)
was retired in #32 (`docs/decisions/ONE_DASHBOARD.md`) - don't recreate it. Keep these
names in new docs; the root `README.md` "Real data vs synthetic data" section is canonical.

## Commands

This is a `uv` workspace monorepo (Python >=3.12). Linting is `ruff`
(configured in the root `pyproject.toml`; B008 is ignored because FastAPI's
`Query(...)/Depends(...)` default-argument pattern trips it).
`pytest` is wired up for
`packages/pipelines`, `packages/backend` and `packages/physics_models` (see
"Tests" below).

`uv run pytest` from the repo root reuses the single shared `.venv`; a partial
`uv sync --package <pkg>` can prune other workspace packages from it. If test
collection fails with `ModuleNotFoundError` (pydantic, fastapi, ...), run
`uv sync --all-packages` first.

Full service startup order (Docker + host `uv` services): see `RUN_SERVICES.md`.

```
# install/sync a package's deps (creates .venv at repo root)
uv sync --package <backend|pipelines|contracts|physics_models|dashboard>

# bring up local infrastructure (TimescaleDB + Redpanda)
docker compose up -d timescaledb redpanda

# run an ingest job (one module per source: jpl_cad, jpl_orion, jpl_dsn_geometry, donki, iswa_goes_protons)
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# run the Digital Twin dashboard (needs the backend: uv run --package backend python -m backend.main)
uv run --package dashboard streamlit run dashboard/src/prototype/app.py

# check ingested data without a local psql client
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM close_approaches;"
```

### Tests

Tests live in the root `tests/` dir (not inside `packages/<package>/`),
mirroring the source path:

- `tests/unit/<package>/<module path>/test_<function>.py` - no network, no DB
  (HTTP mocked with `responses`, connections with `MagicMock`).
- `tests/integration/<package>/<module path>/test_<feature>.py` - require an
  explicitly configured test database and may call a live datasource.
- Test names: `test_<function>_<expected behavior>`.
- Fixtures go in that module's `conftest.py`. pytest runs with
  `--import-mode=importlib` so different modules can have same-named test
  files (which also means tests can't import each other - share helpers via
  fixtures).

Unit tests exist for all pipeline ingest modules (`jpl_cad`, `donki`,
`iswa_goes_protons`, `jpl_dsn_geometry`), plus `tests/unit/backend` (route and
model tests), `tests/unit/physics_models` and `tests/unit/dashboard` (the
Digital Twin dashboard's helpers; a test keeps `views/_explain.py` in sync with the
pages) and `tests/unit/airflow` (the DAG source lists, natively; the DAGs themselves
only in the `airflow-tests` container).

```
# Docker test environment (compose service `tests`, profile "test")
docker compose run --rm tests

# natively - unit tests only
uv run --package pipelines pytest tests/unit
```

The `tests` service has no Dockerfile: it runs the official
`ghcr.io/astral-sh/uv` image with the repo mounted **read-only** and the venv
in the container (`UV_PROJECT_ENVIRONMENT=/opt/venv`), so it's safe w.r.t.
the Windows/Docker `.venv` gotcha below - keep it read-only.

`DATABASE_URL` (see `.env.example`) configures both the ingest job and the dashboard.
TimescaleDB listens on host port **5433**, not 5432 - a native Postgres install commonly
already owns 5432.

### Windows/Docker gotcha

If `uv sync`/`uv run` is ever run inside a Linux container with this repo bind-mounted
(e.g. for headless verification), it leaves a Unix-style `.venv` (with a `lib64` symlink)
on disk that breaks subsequent native Windows `uv run` with `Access is denied` on
`.venv/lib64`. Fix: delete `.venv` and let `uv` rebuild it natively.

## Two efforts in this repo

1. **Spacecraft digital twin / synthetic data path** (the final target): simulates Artemis II Orion
   telemetry from JPL Horizons ephemeris + NASA OEM/AROW data, through four coupled
   physics models (thermal, power, comms, radiation), publishing a unified telemetry
   packet. Fully specified via ODCS data contracts in `packages/contracts/src/odcs/`
   (numbered `01_state_engine` ... `05_anomaly_ml_features`). Implemented so far:
   `contracts` Pydantic models, `physics_models` state/thermal/power generators +
   Kafka producer/consumer, `backend` REST API, `dashboard/src/prototype` Streamlit
   views. Comms/radiation/packet/anomaly generators remain placeholders
   (other contributors).
2. **Real data path** (`packages/pipelines`): a working, lightweight batch ETL that
   ingests public NASA/JPL data (JPL CAD, JPL Horizons for Orion, the Moon and DSN
   geometry, NASA DONKI, GOES proton flux via NASA iSWA, plus the local NASA OEM arcs
   and mission timeline) into TimescaleDB. It was the first end-to-end functional path
   in the repo and the first step toward effort #1 - proving out the ingest -> store ->
   visualize pattern at small scale. Its own Streamlit app (the Data Explorer) was
   retired once the Digital Twin dashboard showed the same data through the backend.
   `pipelines` depends on `contracts` (only for `contracts.planned_attitude`, the
   mission timeline) but **not** on `backend`, and has no formal ODCS contract - see
   the root `README.md` for the architecture diagram. Airflow (`airflow/`, compose
   profile `airflow`) schedules the ingest jobs: `real_data_backfill` (manual, every
   source) and `real_data_refresh` (daily). The source lists live in
   `airflow/dags/real_data_sources.py`; a new ingest module must be added there (a unit
   test fails otherwise). Each task runs `python -m pipelines.ingest.<source>` with a
   separate `pipelines` venv baked into the image (not Airflow's env), one at a time via
   the one-slot `real_data_ingest` pool (JPL fair use).

When asked to "add a data source," it means an ingest module plus a backend route
and a Digital Twin dashboard chart (see below); "add a page" means a page in
`dashboard/src/prototype/views/` (a module plus its `st.Page` entry in `app.py`; the folder must
not be named `pages/`, see the comment in `app.py`).

## Architecture of the real data path (effort #2)

```
public JSON API --> pipelines.ingest.<source> --> TimescaleDB --> backend --> dashboard/src/prototype
```

Horizons gotchas: VECTORS tables default to **TDB** time stamps (OBSERVER tables
are **UT**, ~69 s apart in 2026) and to **ECLIPTIC** axes (23.44° from EME2000).
`jpl_orion` therefore requests `TIME_TYPE=UT` and `REF_PLANE=FRAME` so its rows
line up with the UT `jpl_dsn_geometry` tables and the EME2000 synthetic state;
keep both parameters on any new VECTORS ingest. Don't request `CSV_FORMAT=YES` for
VECTORS: since Nov 2026 it returns only the time columns (#57), so `jpl_orion` parses
the plain-text table. For CSV OBSERVER tables (`jpl_dsn_geometry`) Horizons prints the
CSV header above `$$SOE`, not inside the data block.

- **`packages/pipelines/src/pipelines/db.py`**: only the shared `get_connection()`.
  Each ingest module owns its own table schema and setup - see
  `pipelines/ingest/jpl_cad.py` for the pattern (schema DDL, hypertable creation via
  `pg_extension` check, dataclass for parsed records, `fetch_*`/`upsert_*`/`main()`).
  A new source is a new self-contained `pipelines/ingest/jpl_<source>.py` module,
  following that same shape - don't centralize per-source schema logic into `db.py`.
- **Backend** serves each real table at a top-level route: response model in
  `packages/contracts/src/contracts/models.py`, ORM model in
  `packages/backend/src/backend/models.py`, route in
  `packages/backend/src/backend/api/routes/<source>.py` registered in
  `backend/api/__init__.py`.
- **`dashboard/src/prototype`** (the Digital Twin dashboard) is a multi-page Streamlit
  app (`st.navigation`/`st.Page`). `dashboard/pyproject.toml` makes `dashboard` a
  *virtual* `uv` workspace member: it only declares the app's deps and is not built,
  so modules import each other as `dashboard.src.prototype...` from the repo root.
  - `data/backend_api.py` - the one HTTP client (sync `httpx`, returns `contracts` models).
  - `views/_data.py` - `@st.cache_data` loaders; `fetch_all` pages past the backend's
    1,000-row cap.
  - `views/_explain.py` - Real / Synthetic / Placeholder badge, summary and explainer
    per chart; a unit test fails if a page and these dicts disagree.
  - Adding a source = ingest module + its entry in `airflow/dags/real_data_sources.py`
    + backend model/route + client method + loader +
    chart and `_explain.py` entries, plus unit tests under
    `tests/unit/pipelines/ingest/<source>/` and `tests/unit/backend/`.
- `pipelines` and `backend` are deliberately independent (no shared import between
  them, each has its own environment-based connection handling; see the Dockerfile
  comments in `packages/backend/Dockerfile` about not pulling in pipeline deps). The
  dashboard never reads the DB directly. Don't "fix" this duplication by introducing a
  shared db/config package unless asked.
- Each package has its own `Dockerfile` where applicable (built from the **repo root**,
  e.g. `docker build -f packages/physics_models/Dockerfile .`, so `uv` can resolve the
  workspace). `docker compose up -d --build` runs the whole app: `timescaledb`,
  `redpanda`, `migrate` (one-shot `alembic upgrade head`; the consumer and backend wait
  for it), `physics_models`, `physics_models_consumer`, `backend` and `dashboard`
  (`dashboard/Dockerfile`; it finds the backend via `BACKEND_URL`, default
  `http://localhost:8000`). The Airflow services (`airflow-init`, `-apiserver` on
  `127.0.0.1:8080`, `-scheduler`, `-dag-processor`; metadata in an `airflow` database on
  the same TimescaleDB; FAB auth manager, user `admin`) are in the `airflow` profile.
  `docker-compose.prod.yml` is the public-server override (#43): only Caddy
  (`infra/caddy/Caddyfile`, HTTPS on `PUBLIC_HOSTNAME`) publishes ports, the rest are
  `!reset`; keep dev ports in `docker-compose.yml` only (`RUN_SERVICES.md`, "Production";
  the UpCloud runbook is `docs/guides/UPCLOUD_DEPLOYMENT.md`).
  The `tests`/`orion-tests`/`airflow-tests` services are in the `test` profile (`orion-tests`
  extends `tests` - same read-only image, plus the database - and runs `make test-orion`); the DAG
  tests need Airflow, which doesn't run on native Windows, so they skip natively and run
  via `docker compose run --rm --build airflow-tests`. For code changes the backend and
  dashboard can still run natively via `uv run` (`BACKEND_RELOAD=1` turns on uvicorn reload; see `RUN_SERVICES.md`). `packages/pipelines/Dockerfile` installs no JDK -
  the `pipelines` package has no PySpark dependency; if one is reintroduced,
  target Spark 4.x (Java 17/21/25) and use `openjdk-21-jre-headless` -
  openjdk-17 no longer exists on the `python:3.12-slim`/Debian trixie base.

## JPL SSD API notes

`https://ssd-api.jpl.nasa.gov/` is an umbrella of ~17 separate APIs (SBDB, Sentry,
Fireball, NHATS, Scout, Horizons, etc.) - "the JPL API" is ambiguous, always confirm
which one. Fair-use policy across the family: one request at a time, no guaranteed
availability - ingest modules must stay sequential, no concurrent requests.

## NASA iSWA HAPI notes

`pipelines.ingest.iswa_goes_protons` reads GOES proton flux from NASA CCMC iSWA's
HAPI 2.0 server (`https://iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi/`). HAPI
gotchas: requested `parameters` must be in the dataset's `/info` order (else error
1411); errors arrive as a JSON `status` object (`1200`/`1201` = OK); fill values are
declared per parameter as strings (`"-100000"`, `"null"`). It is NOAA's real-time
product (provisional). NASA's CDAWeb HAPI (`cdaweb.gsfc.nasa.gov/hapi`) has OMNI
solar-wind data, but its GOES proton columns are all fill values for 2026.
