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

Effort #2 (the real data path: `packages/pipelines` + the Data Explorer in
`packages/streamlit_dashboard`) is a working lightweight ETL + Streamlit app that
ingests public NASA/JPL APIs into TimescaleDB - the proven small-scale version of
the same ingest -> store -> visualize shape. See "Two efforts in this repo" below
before assuming any two packages are meant to talk to each other.

Docs use one vocabulary for this split: **real data** (published by NASA/JPL:
ingested tables + `data/oem/` files) vs **synthetic data** (simulated by
`physics_models`; tables under `/telemetry/synthetic/*` in the API). The two
dashboards are the **Data Explorer** (`packages/streamlit_dashboard`, real data
only, reads the DB) and the **Digital Twin dashboard** (`dashboard/src/prototype`,
synthetic data with real data alongside, reads the backend). Keep these names in
new docs; the root `README.md` "Real data vs synthetic data" section is canonical.

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
uv sync --package <backend|pipelines|contracts|physics_models|streamlit_dashboard>

# bring up local infrastructure (TimescaleDB + Redpanda)
docker compose up -d timescaledb redpanda

# run an ingest job (one module per source: jpl_cad, jpl_orion, jpl_dsn_geometry, donki, iswa_goes_protons)
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# run the pipeline-explorer dashboard
uv run --package streamlit_dashboard streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py

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
model tests) and `tests/unit/physics_models`.

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
   (other contributors). `airflow/dags/` is empty scaffolding.
2. **Real data path / Data Explorer** (`packages/pipelines`
   - `packages/streamlit_dashboard`): a working, lightweight ETL + Streamlit app that
     ingests public NASA/JPL data (JPL CAD, JPL Horizons for Orion and DSN geometry,
     NASA DONKI, GOES proton flux via NASA iSWA, plus the local NASA OEM arcs and
     mission timeline) into TimescaleDB and visualizes it. It was the first end-to-end functional path in the repo (effort #1 is now runnable too), and the
     first step toward effort #1 - proving out the ingest -> store -> visualize pattern at
     small scale. It intentionally does **not** depend on `contracts` or `backend` yet, and
     has no formal ODCS contract - see the root `README.md` for the full architecture
     diagram and rationale.

When asked to "add a data source" or "add a page," it almost always means effort #2.

## Architecture of the working pipeline (effort #2)

```
public JSON API --> pipelines.ingest.<source> --> TimescaleDB --> streamlit_dashboard
```

Horizons gotcha: VECTORS tables are stamped in **TDB** and OBSERVER tables in
**UT** (~69 s apart in 2026). `jpl_dsn_geometry` stores UT; `jpl_orion`
currently stores its TDB calendar dates as if they were UTC, so joins between
the two are off by ~69 s.

- **`packages/pipelines/src/pipelines/db.py`**: only the shared `get_connection()`.
  Each ingest module owns its own table schema and setup - see
  `pipelines/ingest/jpl_cad.py` for the pattern (schema DDL, hypertable creation via
  `pg_extension` check, dataclass for parsed records, `fetch_*`/`upsert_*`/`main()`).
  A new source is a new self-contained `pipelines/ingest/jpl_<source>.py` module,
  following that same shape - don't centralize per-source schema logic into `db.py`.
- **`packages/streamlit_dashboard`** is a multi-page Streamlit app (`st.navigation`/
  `st.Page`, requires `streamlit>=1.36`):
  - `data/engine.py` - the one shared piece, a `@st.cache_resource`-cached
    `get_engine()`.
  - `data/<source>.py` - one `@st.cache_data`-cached query module per data source.
  - `pages/<source>.py` - one page per data source (filters, table, chart).
  - `app.py` - thin entrypoint only: `st.set_page_config` + registers pages in a
    `st.Page(...)` list. `pages/welcome.py` is the landing page.
  - Adding a source = one file in each of `pipelines/ingest/`, `data/`, `pages/`, plus
    one line in `app.py`'s `pages` list, plus unit tests under
    `tests/unit/pipelines/ingest/<source>/` (see "Tests" above).
- Both `pipelines` and `streamlit_dashboard` are deliberately independent (no shared
  import between them, each has its own environment-based connection handling) -
  this mirrors the existing isolation between `backend` and `pipelines` (see the
  Dockerfile comments in `packages/backend/Dockerfile` about not pulling in pipeline
  deps). Don't "fix" this duplication by introducing a shared db/config package unless
  asked.
- Each package has its own `Dockerfile` where applicable (built from the **repo root**,
  e.g. `docker build -f packages/physics_models/Dockerfile .`, so `uv` can resolve the
  workspace). For local dev, the Docker stack is `timescaledb`, `redpanda`,
  `physics_models`, `physics_models_consumer` (plus the on-demand `tests` service);
  `backend` and the Streamlit dashboards run natively via `uv run`
  (see `RUN_SERVICES.md`). `packages/pipelines/Dockerfile` installs no JDK -
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
