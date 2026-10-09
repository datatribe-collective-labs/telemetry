# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A telemetry project working toward a full spacecraft digital twin for NASA Artemis II /
Orion - real-time physics simulation (thermal, power, comms, radiation) fed by JPL
Horizons ephemeris and NASA telemetry, streamed through Kafka, validated against the
ODCS contracts in `packages/contracts/src/odcs/`, and surfaced on a dashboard. That
target is fully specified but almost entirely unbuilt.

Rather than build toward it directly, the strategy is incremental: prove the pattern
small, then scale it up. The current working piece ("Telemetry Project - Data Tribe")
ingests a public API (JPL Solar System Dynamics data) and shows it on a dashboard -
the simplest possible version of the same ingest -> store -> visualize shape the
digital twin will eventually need at much larger scale. It's an early step, not a
permanent side-project, and the two don't share code yet - see "Two efforts in this
repo" below before assuming any two packages are meant to talk to each other.

## Commands

This is a `uv` workspace monorepo (Python >=3.12). There is no lint/CI tooling
configured yet - don't invent `ruff`/etc. commands. `pytest` exists only for
`packages/pipelines` so far (see "Tests" below) - don't assume it's wired up
for other packages.

```
# install/sync a package's deps (creates .venv at repo root)
uv sync --package <backend|pipelines|contracts|streamlit_dashboard>

# bring up local TimescaleDB (the only long-running Docker service for local dev)
docker compose up -d timescaledb

# run the JPL close-approach ingest job
uv run --package pipelines python -m pipelines.ingest.jpl_cad

# run the dashboard
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

Unit tests exist for the `jpl_cad`, `donki` and `iswa_goes_protons` ingest modules.

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

1. **Spacecraft digital twin** (the final target): simulates Artemis II Orion
   telemetry from JPL Horizons ephemeris + NASA OEM/AROW data, through four coupled
   physics models (thermal, power, comms, radiation), publishing a unified telemetry
   packet. Fully specified via ODCS data contracts in `packages/contracts/src/odcs/`
   (numbered `01_state_engine` ... `05_anomaly_ml_features`), but almost nothing is
   implemented - `packages/backend` is a FastAPI "hello world" stub, `packages/contracts`
   has no actual Pydantic models (despite depending on `pydantic`), and
   `digital_twin_dashboard/`, `airflow/`, `superset/` are empty scaffolding for a
   _planned_ TypeScript + Superset dashboard that does not exist yet.
2. **JPL data-source dashboard** ("Telemetry Project - Data Tribe", `packages/pipelines`
   - `packages/streamlit_dashboard`): a working, lightweight ETL + Streamlit app that
     ingests public NASA/JPL APIs (JPL CAD, JPL Horizons for Orion, NASA DONKI, and
     GOES proton flux via NASA iSWA) into TimescaleDB and visualizes it. This is the only end-to-end functional path in the repo, and the
     first step toward effort #1 - proving out the ingest -> store -> visualize pattern at
     small scale. It intentionally does **not** depend on `contracts` or `backend` yet, and
     has no formal ODCS contract - see the root `README.md` for the full architecture
     diagram and rationale.

When asked to "add a data source" or "add a page," it almost always means effort #2.

## Architecture of the working pipeline (effort #2)

```
public JSON API --> pipelines.ingest.<source> --> TimescaleDB --> streamlit_dashboard
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
    one line in `app.py`'s `pages` list, plus unit tests under
    `tests/unit/pipelines/ingest/<source>/` (see "Tests" above).
- Both `pipelines` and `streamlit_dashboard` are deliberately independent (no shared
  import between them, each has its own environment-based connection handling) -
  this mirrors the existing isolation between `backend` and `pipelines` (see the
  Dockerfile comments in `packages/backend/Dockerfile` about not pulling in pipeline
  deps). Don't "fix" this duplication by introducing a shared db/config package unless
  asked.
- Each package has its own `Dockerfile` (built from the **repo root**, e.g.
  `docker build -f packages/pipelines/Dockerfile .`, so `uv` can resolve the workspace),
  but for local dev only `timescaledb` (and the on-demand `tests` service) run in
  Docker - `pipelines` and `streamlit_dashboard` run natively via `uv run`. `packages/pipelines/Dockerfile`
  currently fails to build (`openjdk-17-jre-headless` isn't available on the current
  `python:3.12-slim`/Debian trixie base image) - it's pre-existing and unrelated to
  anything needing Java yet (`pyproject.toml` has no PySpark dependency despite the
  Dockerfile provisioning for it).

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
