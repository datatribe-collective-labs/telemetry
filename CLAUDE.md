# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A spacecraft digital-twin telemetry project (NASA Artemis II / Orion), plus a separate,
independent side-project ("Telemetry Project - Data Tribe") that ingests public JPL
Solar System Dynamics API data. These two efforts share this repo but are otherwise
unrelated - see "Two separate efforts" below before assuming any two packages are meant
to talk to each other.

## Commands

This is a `uv` workspace monorepo (Python >=3.12). There is no lint/test/CI tooling
configured yet - don't invent `ruff`/`pytest`/etc. commands.

```
# install/sync a package's deps (creates .venv at repo root)
uv sync --package <backend|pipelines|contracts|streamlit_dashboard>

# bring up local TimescaleDB (the only thing that runs in Docker for local dev)
docker compose up -d timescaledb

# run the JPL close-approach ingest job
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# run the dashboard
uv run --package streamlit_dashboard streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py

# check ingested data without a local psql client
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM close_approaches;"
```

`DATABASE_URL` (see `.env.example`) configures both the ingest job and the dashboard.
TimescaleDB listens on host port **5433**, not 5432 - a native Postgres install commonly
already owns 5432.

### Windows/Docker gotcha

If `uv sync`/`uv run` is ever run inside a Linux container with this repo bind-mounted
(e.g. for headless verification), it leaves a Unix-style `.venv` (with a `lib64` symlink)
on disk that breaks subsequent native Windows `uv run` with `Access is denied` on
`.venv/lib64`. Fix: delete `.venv` and let `uv` rebuild it natively.

## Two separate efforts in this repo

1. **Spacecraft digital twin** (the original scaffold): simulates Artemis II Orion
   telemetry from JPL Horizons ephemeris + NASA OEM/AROW data, through four coupled
   physics models (thermal, power, comms, radiation), publishing a unified telemetry
   packet. Fully specified via ODCS data contracts in `packages/contracts/src/odcs/`
   (numbered `01_state_engine` ... `05_anomaly_ml_features`), but almost nothing is
   implemented - `packages/backend` is a FastAPI "hello world" stub, `packages/contracts`
   has no actual Pydantic models (despite depending on `pydantic`), and `dashboard/`,
   `airflow/`, `superset/` are empty scaffolding for a *planned* TypeScript + Superset
   dashboard that does not exist yet.
2. **JPL data-source dashboard** ("Telemetry Project - Data Tribe", `packages/pipelines`
   + `packages/streamlit_dashboard`): a working, independent, lightweight ETL + Streamlit
   app that ingests JPL SSD API data (currently only Close-Approach Data / CAD) into
   TimescaleDB and visualizes it. This is the only end-to-end functional path in the repo.
   It intentionally does **not** depend on `contracts` or `backend`, and has no formal
   ODCS contract - see the root `README.md` for the full architecture diagram and
   rationale.

When asked to "add a data source" or "add a page," it almost always means effort #2.

## Architecture of the working pipeline (effort #2)

```
JPL SSD CAD API --> pipelines.ingest.<source> --> TimescaleDB --> streamlit_dashboard
```

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
    one line in `app.py`'s `pages` list.
- Both `pipelines` and `streamlit_dashboard` are deliberately independent (no shared
  import between them, each has its own `DEFAULT_DATABASE_URL`/connection handling) -
  this mirrors the existing isolation between `backend` and `pipelines` (see the
  Dockerfile comments in `packages/backend/Dockerfile` about not pulling in pipeline
  deps). Don't "fix" this duplication by introducing a shared db/config package unless
  asked.
- Each package has its own `Dockerfile` (built from the **repo root**, e.g.
  `docker build -f packages/pipelines/Dockerfile .`, so `uv` can resolve the workspace),
  but for local dev only `timescaledb` actually runs in Docker - `pipelines` and
  `streamlit_dashboard` run natively via `uv run`. `packages/pipelines/Dockerfile`
  currently fails to build (`openjdk-17-jre-headless` isn't available on the current
  `python:3.12-slim`/Debian trixie base image) - it's pre-existing and unrelated to
  anything needing Java yet (`pyproject.toml` has no PySpark dependency despite the
  Dockerfile provisioning for it).

## JPL SSD API notes

`https://ssd-api.jpl.nasa.gov/` is an umbrella of ~17 separate APIs (SBDB, Sentry,
Fireball, NHATS, Scout, Horizons, etc.) - "the JPL API" is ambiguous, always confirm
which one. Fair-use policy across the family: one request at a time, no guaranteed
availability - ingest modules must stay sequential, no concurrent requests.