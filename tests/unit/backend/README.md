# Backend Unit Tests

## Overview

Unit tests for the Telemetry backend API (`packages/backend`). Tests run without a database by overriding the `get_db` dependency with a recording fake session that verifies SQL fragments, parameters, response serialization, status codes, pagination, filters, and empty-result behavior.

## Layout

```
tests/unit/backend/
├── api/
│   ├── test_create_app.py                 # FastAPI app creation + route registration
│   └── routes/
│       ├── conftest.py                    # Shared fixtures: fake_session, client, row_factory, result_factory
│       ├── synthetic/                     # Synthetic telemetry endpoints (14 tests)
│       │   ├── test_column_lists.py
│       │   ├── test_get_latest_synthetic_telemetry.py
│       │   ├── test_get_synthetic_state.py
│       │   ├── test_get_synthetic_telemetry_packet.py
│       │   ├── test_helpers.py
│       │   ├── test_list_synthetic_anomalies.py
│       │   ├── test_list_synthetic_comms.py
│       │   ├── test_list_synthetic_cross_model.py
│       │   ├── test_list_synthetic_ml_features.py
│       │   ├── test_list_synthetic_power.py
│       │   ├── test_list_synthetic_radiation.py
│       │   ├── test_list_synthetic_state.py
│       │   ├── test_list_synthetic_state_filters.py
│       │   ├── test_list_synthetic_telemetry_packets.py
│       │   └── test_list_synthetic_thermal.py
│       ├── orion/                         # Orion ephemeris (2 tests)
│       ├── close_approaches/              # Close approaches (2 tests)
│       ├── health/                        # Health checks (3 tests)
│       └── donki/                         # DONKI space weather (4 tests)
└── models/
    └── test_schema_conventions.py         # SQLAlchemy model conventions (synthetic + real-data)
```

## Running Tests

### From Repository Root (Recommended)

```bash
# Run all backend unit tests
uv run --package backend pytest tests/unit/backend -v

# Run specific test file
uv run --package backend pytest tests/unit/backend/api/routes/synthetic/test_list_synthetic_state.py -v

# Collect only (no execution)
uv run --package backend pytest tests/unit/backend --collect-only -q

# Run with coverage
uv run --package backend pytest tests/unit/backend --cov=backend --cov-report=term-missing
```

### From Backend Package

```bash
cd packages/backend
uv run pytest ../../tests/unit/backend -v
```

## Test Conventions

### No Database Required
All tests use a **fake session** (`FakeSession`) that:
- Records executed SQL statements and parameters
- Returns pre-configured mock results
- Validates SQL fragments without touching PostgreSQL

### Fixtures (from `routes/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `fake_session` | Recording fake DB session with `.calls` list and `.results` queue |
| `client` | FastAPI `TestClient` with `get_db` dependency overridden |
| `row_factory` | Creates mock row dicts with appropriate types for each column |
| `result_factory` | Creates `Result` objects wrapping rows or scalar values |

### Writing New Tests

```python
from backend.api.routes.synthetic import STATE_COLUMNS

def test_my_endpoint(client, fake_session, row_factory, result_factory):
    # Queue expected results: first COUNT(*), then SELECT rows
    fake_session.results = [
        result_factory(scalar_value=1),           # COUNT(*)
        result_factory([row_factory(STATE_COLUMNS)])  # SELECT rows
    ]
    
    r = client.get('/telemetry/synthetic/state?limit=50')
    assert r.status_code == 200
    body = r.json()
    assert body['total'] == 1
    assert body['limit'] == 50
    assert body['items'][0]['x_km'] == 1.234
    
    # Verify SQL generated
    assert 'FROM state_snapshot' in fake_session.calls[1][0]
    assert 'LIMIT :limit OFFSET :offset' in fake_session.calls[1][0]
```

### Contract Models
The root `tests/conftest.py` imports the real `contracts` package from the workspace (`packages/contracts/src/contracts`). This package provides all Pydantic models for both real data sources (JPL/NASA) and synthetic telemetry. The test conftest adds the contracts source to `sys.path` and registers it as the `contracts` module so the backend can import it normally.

### Column Lists
Each route module exports a `*_COLUMNS` list (e.g., `STATE_COLUMNS`, `THERMAL_COLUMNS`) containing the **contract field names** (mixed case). The test verifies these match the actual DB columns and contract models.

## Test Coverage

| Area | Tests | Focus |
|------|-------|-------|
| Synthetic routes | 14 | List, get by ID, filters, pagination, helpers, column validation |
| Orion | 2 | List, get 404 |
| Close Approaches | 2 | List with defaults, get 404 |
| Health | 3 | Basic, DB ok, DB degraded |
| DONKI | 4 | List, get event, event types, invalid type |
| Models | 1 | Schema conventions (synthetic: lowercase columns, `timestamp_utc` PK; real-data: TEXT, JSONB, composite PKs) |
| App | 1 | OpenAPI schema + 12 synthetic routes |

**Total: 37 backend unit tests**

## Schema Conventions Test

`test_schema_conventions.py` validates two table categories:

**Synthetic tables** (9): `state_snapshot`, `thermal_output`, `power_output`, `comms_output`, `radiation_output`, `cross_model_state`, `telemetry_packet`, `anomaly_events`, `ml_feature_vectors`
- All columns lowercase snake_case
- Primary key on `timestamp_utc` (or composite for `anomaly_events`)
- Timezone-aware `DateTime` for timestamp columns

**Real-data tables** (3): `close_approaches`, `orion_ephemeris`, `donki_events`
- Exist in metadata with correct primary keys
- Use `Text`, `JSONB`, composite primary keys as defined in live DB
- Not required to follow synthetic naming conventions

## Adding New Route Tests

1. Create test file in appropriate subdirectory under `routes/`
2. Import the route's `*_COLUMNS` constant
3. Use the standard fixtures: `client`, `fake_session`, `row_factory`, `result_factory`
4. Queue results: `[count_result, select_result]`
5. Assert status, pagination envelope, item shape, and SQL fragments

## CI Integration

Tests run in CI with:
```bash
uv run --package backend pytest tests/unit/backend -q
```

No external services (PostgreSQL, TimescaleDB) are required for unit tests.