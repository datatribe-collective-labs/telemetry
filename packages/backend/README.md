# backend

The FastAPI REST API that serves every table, real and synthetic, to the Digital Twin
dashboard. It only reads: ingest jobs and the Kafka consumer do the writing. Where it sits:
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).

## Run

```bash
# In Docker (starts `migrate` first): http://localhost:8000/docs
docker compose up -d --build backend

# Natively, from the repo root (stop the container first: they share port 8000)
uv run --package backend python -m backend.main      # BACKEND_RELOAD=1 for auto-reload
```

Connection settings come from the environment, or from the repo root `.env`:
`DATABASE_URL`, or else `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` on
`localhost:5433`. In Docker, compose sets `DATABASE_URL` to the database service.

## Endpoints

29 GET endpoints. The parameters and response models of each are on the live OpenAPI
page, http://localhost:8000/docs. Responses are the `contracts.models` Pydantic models.
Paged list endpoints return at most 1,000 rows per request (`limit`, `offset`) along with
the `total` row count.

**Health**

| Path | Returns |
|------|---------|
| `/health` | The API is up |
| `/health/db` | The API can reach the database |

**Real data** (one route module per source, filters by time window)

| Path | Table | Extra filters |
|------|-------|---------------|
| `/orion`, `/orion/{target_id}/{epoch}` | `orion_ephemeris` | `target_id` |
| `/moon` | `moon_ephemeris` | - |
| `/oem`, `/oem/arcs` | `oem_state_vectors` | `arc_id` (latest arc by default) |
| `/mission-events` | `mission_events` | `met_from_s`, `met_to_s`, `mode` (by mission elapsed time) |
| `/dsn-geometry`, `/dsn-geometry/{target_id}/{site}/{epoch}` | `dsn_site_geometry` | `site`, `complex`, `visible_only` |
| `/donki`, `/donki/event-types`, `/donki/{event_type}/{event_id}` | `donki_events` | `event_types` |
| `/iswa-goes-protons`, `/iswa-goes-protons/{time}` | `goes_integral_protons` | - |
| `/close-approaches`, `/close-approaches/{des}/{orbit_id}/{close_approach_time}` | `close_approaches` | `dist_max_au`, `designation` |

**Synthetic data** (`/telemetry/synthetic/...`, all in `routes/synthetic.py`)

| Path | Table | Extra filters |
|------|-------|---------------|
| `/state`, `/state/{timestamp_utc}` | `state_snapshot` | - |
| `/thermal` | `thermal_output` | `thermal_state` |
| `/power` | `power_output` | `power_state` |
| `/comms` | `comms_output` | `comm_state` |
| `/radiation` | `radiation_output` | `sep_event_active` |
| `/cross-model` | `cross_model_state` | - |
| `/packet`, `/packet/{timestamp_utc}` | `telemetry_packet` | `all_nominal`, `thermal_state`, `power_state`, `comm_state` |
| `/latest` | `telemetry_packet` | the most recently written packet |
| `/anomalies` | `anomaly_events` (placeholder, empty) | `anomaly_type`, `detection_layer`, `severity`, `mission_phase` |
| `/ml-features` | `ml_feature_vectors` (placeholder values) | - |

The synthetic list endpoints also take `sort_by=timestamp_utc|ingested_at` and
`order=asc|desc`. `sort_by=ingested_at&order=desc` gives the rows written most recently,
which is how the dashboard follows the current run after a replay restarts or loops.

## Database schema

- **Synthetic tables:** created by the Alembic migrations in `alembic/versions/` (nine
  hypertables keyed on `timestamp_utc`, with an `ingested_at` column). In Docker the
  one-shot `migrate` service runs `alembic upgrade head` before the consumer and backend
  start. Natively: `cd packages/backend && uv run --package backend alembic upgrade head`.
  `alembic/env.py` adds the `CREATE EXTENSION timescaledb` and `create_hypertable()` calls
  to new migrations.
- **Real-data tables:** created by their own ingest module in `packages/pipelines`.
  `src/backend/models.py` maps five of them as ORM models. The `moon`, `oem` and
  `mission-events` routes query their tables with plain SQL.

## Key files

| File | Holds |
|------|-------|
| `src/backend/api/__init__.py` | The FastAPI app; registers every router |
| `src/backend/api/routes/<source>.py` | One module per real source, plus `synthetic.py` and `health.py` |
| `src/backend/models.py` | SQLAlchemy models |
| `src/backend/db/session.py` | Engine, session, connection settings |
| `alembic/` | Migrations for the synthetic tables |
| `Dockerfile` | The image (built from the repo root; installs only the backend and `contracts`) |

## Add an endpoint

For a new real-data source (the whole checklist, ingest to dashboard, is in the root
`README.md`):

1. A response model in `packages/contracts/src/contracts/models.py`.
2. An ORM model in `src/backend/models.py` (or plain SQL in the route).
3. A route module in `src/backend/api/routes/<source>.py`, registered in
   `src/backend/api/__init__.py`.
4. Unit tests under `tests/unit/backend/api/routes/`.

## Tests

```bash
uv run pytest tests/unit/backend        # no database: routes run against a fake session
```

The fixtures (`fake_session`, `client`, row and result factories) are in
`tests/unit/backend/api/routes/conftest.py`.
