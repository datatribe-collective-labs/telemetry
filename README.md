# Telemetry Project - Data Tribe

Open-source telemetry project that ingests, processes, and analyzes mission
telemetry data in real-time using publicly available NASA flight data.

**What it provides:**

- Real-time ingestion and processing of telemetry streams
- Storage and analysis of the data
- Dashboard for real-time monitoring and visualization

## MVP

Working end-to-end data pipeline:

**Source → processing → storage → Dashboard**

## Architecture Diagram

```mermaid
flowchart LR
    Source1(["Data Source 1\nJPL Close-Approach Data (CAD)"])
    Source2(["Data Source 2\nJPL Orion Telemetry"])
    Source3(["Data Source 3\nNASA DONKI Space Weather"])
    Ingest1["Ingest Job\npipelines.ingest.jpl_cad"]
    Ingest2["Ingest Job\npipelines.ingest.jpl_orion"]
    Ingest3["Ingest Job\npipelines.ingest.donki"]
    DB[("TimescaleDB\n")]
    Dash["Streamlit Dashboard\n"]

    Source1 --> Ingest1
    Source2 --> Ingest2
    Source3 --> Ingest3
    Ingest1 --> DB
    Ingest2 --> DB
    Ingest3 --> DB
    DB --> Dash

    subgraph Docker["Docker"]
        DB
    end
```

**Data Sources:**

1. **[JPL Close-Approach Data (CAD) API](https://ssd-api.jpl.nasa.gov/doc/cad.html)** — Upcoming and past close approaches of asteroids/comets to Earth
2. **[JPL Horizons / Orion](https://ssd-api.jpl.nasa.gov/horizons.html)** — Artemis II Orion spacecraft telemetry
3. **[NASA CCMC DONKI API](https://ccmc.gsfc.nasa.gov/DONKI-API/get/)** — Space weather events (CME, SEP, FLR, GST, HSS, etc.)

Each source has its own ingest job, database table, and dashboard page.

## What runs where

- **In Docker:** `timescaledb` (via `docker-compose.yml`), on host port
  **5433** (not 5432 - see `.env.example`; a native Postgres install commonly
  already owns 5432) - plus the on-demand `tests` service (see "Tests" below).
- **Not in Docker (run natively via `uv run`):** the ingest job
  (`pipelines.ingest.jpl_cad`) and the Streamlit dashboard. Both have
  `Dockerfile`s in their package folders, but those are for a future
  containerized deployment - the local dev workflow below runs them directly
  on your machine, talking to the Dockerized database over `localhost:5433`.

## Run locally

### 1. Start the database
```bash
docker compose up -d timescaledb
```

### 2. Ingest data (run each pipeline as needed)

**JPL Close-Approach Data (CAD):**
```bash
uv run --package pipelines python -m pipelines.ingest.jpl_cad
# Options: --date-min now --date-max +60 --dist-max 0.05 --body Earth
```

**JPL Orion Telemetry:**
```bash
uv run --package pipelines python -m pipelines.ingest.jpl_orion
# (Requires RUN_ORION_TIMESCALE_INTEGRATION=1 for live integration tests)
```

**NASA DONKI Space Weather Events:**
```bash
uv run --package pipelines python -m pipelines.ingest.donki
# Options: --start-date 2026-04-01 --end-date 2026-04-10 --event-type CME --event-type SEP
#          --request-delay 0.2
```

### 3. Launch the dashboard
```bash
uv run --package streamlit_dashboard streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py
```

Then open **http://localhost:8501** in your browser.

### Dashboard Pages
- **Welcome** — Project overview
- **Close Approaches** — JPL CAD asteroid/comet close approaches
- **Artemis II Orion** — Orion spacecraft telemetry
- **NASA DONKI** — Space weather events (CME, SEP, FLR, GST, HSS, etc.)

Configure via the `DATABASE_URL` environment variable (see `.env.example`).

## Checking the ingested data

The data lives in three tables inside the `timescaledb` container. Query them directly with `psql` via Docker - no local client needed:

**JPL Close Approaches:**
```
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM close_approaches;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT des, close_approach_time, dist_au, v_rel_kms FROM close_approaches ORDER BY close_approach_time LIMIT 10;"
```

**JPL Orion Telemetry:**
```
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM orion_telemetry;"
```

**NASA DONKI Space Weather Events:**
```
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT count(*) FROM donki_events;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT event_type, count(*) FROM donki_events GROUP BY event_type ORDER BY count DESC;"
docker compose exec timescaledb psql -U telemetry -d telemetry -c "SELECT event_type, event_id, event_time, start_time FROM donki_events ORDER BY COALESCE(event_time, start_time) DESC LIMIT 10;"
```

Or connect with any Postgres GUI client (DBeaver, TablePlus, pgAdmin, the
VS Code PostgreSQL extension, etc.) using the `DATABASE_URL` environment variable
configured in `.env.example`:

```
# From .env.example
# DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB
```

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

```
# in Docker - from the repo root
docker compose run --rm tests

# or natively - also from the repo root
uv run --package pipelines pytest tests/unit
```

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

---

## NASA DONKI Space Weather — Details

### Supported Event Types
| Type | Description | ID Field(s) |
|------|-------------|-------------|
| `CME` | Coronal Mass Ejection | `activityID`, `cmeID` |
| `CMEAnalysis` | CME Analysis | `activityID`, `analysisID`, `cmeID`, `associatedCMEID` |
| `SEP` | Solar Energetic Particle | `sepID`, `activityID` |
| `FLR` | Solar Flare | `flrID`, `activityID` |
| `IPS` | Interplanetary Shock | `ipsID`, `activityID` |
| `GST` | Geomagnetic Storm | `gstID`, `activityID` |
| `RBE` | Radiation Belt Enhancement | `rbeID`, `activityID` |
| `HSS` | High Speed Stream | `hssID`, `activityID` |
| `MPC` | Magnetopause Crossing | `mpcID`, `activityID` |
| `WSAEnlilSimulations` | WSA-Enlil Simulation | `simulationID`, `activityID` |

### Ingestion Options
```bash
# Full backfill for a date range (all event types)
uv run --package pipelines python -m pipelines.ingest.donki \
  --start-date 2026-01-01 --end-date 2026-12-31

# Specific event types only
uv run --package pipelines python -m pipelines.ingest.donki \
  --start-date 2026-04-01 --end-date 2026-04-10 \
  --event-type CME --event-type SEP --event-type FLR

# Adjust rate limiting (default 0.2s between requests)
uv run --package pipelines python -m pipelines.ingest.donki \
  --request-delay 0.5
```

### Database Schema
The `donki_events` table retains the **complete DONKI JSON payload** in a `JSONB` column (`payload`), enabling future schema evolution without re-ingestion. Common fields are extracted for indexing:
- `event_type` — One of the 10 types above
- `event_id` — Type-specific ID (e.g., `activityID` for CME)
- `start_time` / `end_time` / `event_time` — Canonical timestamps (UTC)
- `source_url` — Full API URL used for the fetch
- `fetched_at` — Ingestion timestamp (auto)

Indexes exist on `start_time` and `(event_type, event_time)` for efficient time-range queries.

### Dashboard Features
The **NASA DONKI** dashboard page provides:
- **Sidebar filters**: Date range, multi-select event types
- **Metrics**: Total events, unique event types, events with timestamps
- **Inventory table**: Count per event type
- **Events table**: All events with type, ID, timestamps
- **Raw JSON viewer**: Select any event to view the complete DONKI payload

### Correlation with Other Sources
DONKI events provide space weather context for:
- **Orion telemetry** — SEP/GST events correlate with radiation sensor spikes
- **Close approaches** — CME/HSS affect solar wind density (drag, comms)

All three sources share `TIMESTAMPTZ` columns enabling temporal joins for multi-source analysis.
