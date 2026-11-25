# Backend API

Telemetry API for the Artemis II / Orion Digital Twin project. Provides REST endpoints for querying both real NASA/JPL data sources and synthetic telemetry from physics models.

## Quick Start

```bash
# Install dependencies
uv sync

# Run development server
uv run --package backend uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run --package backend pytest tests/unit/backend -v

# Check schema drift
uv run --package backend alembic check
```

## Architecture

```
packages/backend/
├── alembic/                 # Database migrations (Alembic + TimescaleDB)
├── src/
│   └── backend/
│       ├── api/
│       │   ├── routes/      # FastAPI route modules
│       │   │   ├── close_approaches.py
│       │   │   ├── donki.py
│       │   │   ├── health.py
│       │   │   ├── iswa_goes_protons.py
│       │   │   ├── jpl_dsn_geometry.py
│       │   │   ├── orion.py
│       │   │   └── synthetic.py
│       │   └── __init__.py  # FastAPI app factory
│       ├── db/
│       │   ├── __init__.py
│       │   └── session.py   # SQLAlchemy session management
│       ├── models.py        # SQLAlchemy ORM models (all 12 tables)
│       └── main.py
└── pyproject.toml
```

## Data Sources

### Real Data (JPL/NASA/CCMC)

| Endpoint | Table | Description | Time Column |
|----------|-------|-------------|-------------|
| `/close-approaches` | `close_approaches` | JPL CAD near-Earth object data | `close_approach_time` |
| `/orion` | `orion_ephemeris` | JPL Horizons Orion ephemeris | `epoch` |
| `/donki` | `donki_events` | NASA DONKI space weather events | `event_time`/`start_time` |
| `/iswa-goes-protons` | `goes_integral_protons` | CCMC iSWA GOES proton flux (HAPI) | `time` |
| `/dsn-geometry` | `dsn_site_geometry` | JPL Horizons DSN look angles for Orion | `epoch` |

### Synthetic Telemetry (Physics Models)

| Endpoint | Table | Description |
|----------|-------|-------------|
| `/telemetry/synthetic/state` | `state_snapshot` | State engine snapshot |
| `/telemetry/synthetic/thermal` | `thermal_output` | Thermal model |
| `/telemetry/synthetic/power` | `power_output` | Power model |
| `/telemetry/synthetic/comms` | `comms_output` | Communications model |
| `/telemetry/synthetic/radiation` | `radiation_output` | Radiation model |
| `/telemetry/synthetic/cross-model` | `cross_model_state` | Cross-model coupling bus |
| `/telemetry/synthetic/packet` | `telemetry_packet` | Combined telemetry packet |
| `/telemetry/synthetic/anomalies` | `anomaly_events` | Anomaly detection events |
| `/telemetry/synthetic/ml-features` | `ml_feature_vectors` | ML feature vectors |
| `/telemetry/synthetic/latest` | `telemetry_packet` | Latest telemetry packet |

All synthetic endpoints support: `date_from`, `date_to`, `limit`, `offset`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Database

### Schema Management

All 12 tables are managed by **Alembic** as the single authoritative mechanism:

```bash
# Check for schema drift
alembic check

# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# View history
alembic history --verbose
```

### TimescaleDB Hypertables

11 of 12 tables are TimescaleDB hypertables (all except `donki_events`):

```python
# In alembic/env.py - HYPERTABLES dict
HYPERTABLES = {
    # Synthetic (timestamp_utc)
    "state_snapshot": "timestamp_utc",
    ...
    # Real-data hypertables (different time dimensions)
    "close_approaches": "close_approach_time",
    "orion_ephemeris": "epoch",
    "goes_integral_protons": "time",
    "dsn_site_geometry": "epoch",
}
```

The `process_revision_directives` hook in `alembic/env.py` automatically injects `CREATE EXTENSION IF NOT EXISTS timescaledb` and `create_hypertable()` calls after each table creation.

### Models

SQLAlchemy 2.x declarative models in `src/backend/models.py`:

- **Synthetic tables** (9): lowercase snake_case columns, `timestamp_utc` PK
- **Real-data tables** (3 original + 2 new): preserve existing column names, types, PKs, indexes

```python
from backend.models import Base, StateSnapshot, GoesIntegralProtons, DsnSiteGeometry, ...
```

## Testing

### Unit Tests (No Database Required)

```bash
# All backend unit tests
uv run --package backend pytest tests/unit/backend -v

# Specific module
uv run --package backend pytest tests/unit/backend/api/routes/synthetic -v

# With coverage
uv run --package backend pytest tests/unit/backend --cov=backend --cov-report=term-missing
```

Tests use a **fake session** pattern that records SQL and returns mock results:
- `fake_session` - Records executed SQL and params
- `client` - FastAPI TestClient with `get_db` overridden
- `row_factory` / `result_factory` - Create mock rows/results

### Integration Tests (Require Database)

```bash
# Requires docker compose up
uv run pytest tests/integration -v
```

## Environment

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5433/db

# Optional (defaults shown)
ISWA_HAPI_BASE_URL=https://iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi
JPL_HORIZONS_BASE_URL=https://ssd.jpl.nasa.gov/api/horizons.api
GOES_PROTONS_START=2026-04-01T00:00:00Z
GOES_PROTONS_END=2026-04-12T00:00:00Z
HORIZONS_COMMAND=-1024
HORIZONS_START=2026-04-02 02:00
HORIZONS_STOP=2026-04-10 23:00
HORIZONS_STEP=1 h
```

## Common Patterns

### Adding a New Real-Data Endpoint

1. Add Pydantic model to `packages/contracts/src/contracts/models.py`
2. Export from `packages/contracts/src/contracts/__init__.py`
3. Create route module in `src/backend/api/routes/`
4. Register router in `src/backend/api/__init__.py`
5. Add SQLAlchemy model to `src/backend/models.py`
6. Add to `HYPERTABLES` in `alembic/env.py` if hypertable
7. Create unit tests in `tests/unit/backend/api/routes/`
8. Run `alembic revision --autogenerate` and verify empty migration
9. Run tests

### Adding a New Synthetic Telemetry Endpoint

1. Follow same steps as real-data
2. Use `timestamp_utc` as time column
3. Add to `SYNTHETIC_TABLES` in `alembic/env.py` (also in `HYPERTABLES`)
4. Use `_select_columns()` helper in route for contract-preserving SELECT aliases

### Column Naming Conventions

- **Database**: lowercase snake_case (synthetic) / original case (real-data)
- **API/Contracts**: Original field names (e.g., `temp_sun_face_K`, `eirp_dBW`)
- **Translation**: Route uses `lower_db_col AS "ContractName"` in SELECT

## Dependencies

Core:
- FastAPI 0.142+
- SQLAlchemy 2.0+
- psycopg 3.3+
- Alembic 1.20+
- Pydantic 2+

Development:
- pytest 9+
- pytest-xdist

## CI/CD

```bash
# Lint
uv run ruff check packages/backend

# Type check
uv run mypy packages/backend

# Test
uv run --package backend pytest tests/unit/backend -q

# Schema drift check
uv run --package backend alembic check
```

## Files of Interest

| File | Purpose |
|------|---------|
| `alembic/env.py` | Custom Alembic config with hypertable injection hook |
| `src/backend/models.py` | All 12 SQLAlchemy ORM models |
| `src/backend/api/routes/synthetic.py` | Synthetic telemetry endpoints (largest) |
| `src/backend/api/__init__.py` | FastAPI app with all routers |
| `tests/unit/backend/api/routes/conftest.py` | Shared test fixtures |
| `packages/contracts/src/contracts/models.py` | All Pydantic contracts |