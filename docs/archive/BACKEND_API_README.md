# Telemetry API

FastAPI backend for querying NASA/JPL telemetry data and synthetic telemetry. REST endpoints for:

- **JPL Close-Approach Data (CAD)** — Asteroid/comet close approaches to Earth
- **JPL Horizons / Orion** — Artemis II Orion spacecraft ephemeris
- **NASA DONKI** — Space weather events (CME, SEP, FLR, etc.)
- **NASA iSWA / GOES** — GOES integral proton flux (`/iswa-goes-protons`)
- **JPL Horizons (observer)** — DSN site geometry (`/dsn-geometry`)
- **Synthetic telemetry** — 12 endpoints under `/telemetry/synthetic/*` (see [`SYNTHETIC_TELEMETRY_API.md`](SYNTHETIC_TELEMETRY_API.md))

## Quick Start

### Prerequisites

- Python 3.12+
- TimescaleDB running (via Docker)
- `uv` package manager

### Start Database

```bash
docker compose up -d timescaledb
```

### Run API

```bash
# From repo root
uv run --package backend uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

### Access

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Endpoints

### Health Checks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/db` | Health check with database connectivity |

**Response:**
```json
{
  "status": "ok",
  "service": "telemetry-api",
  "version": "0.1.0"
}
```

---

### Close Approaches (JPL CAD)

#### List Close Approaches

```
GET /close-approaches
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | datetime | — | Start date (UTC, ISO 8601) |
| `date_to` | datetime | — | End date (UTC, ISO 8601) |
| `dist_max_au` | float | 0.05 | Maximum distance in AU |
| `designation` | string | — | Partial match on object designation |
| `limit` | int | 100 | Max results (1–1000) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "items": [
    {
      "des": "2023 BU",
      "orbit_id": "123",
      "close_approach_jd": 2460000.5,
      "close_approach_time": "2023-01-26T21:00:00Z",
      "dist_au": 0.0001,
      "dist_min_au": 0.00009,
      "dist_max_au": 0.00011,
      "v_rel_kms": 9.3,
      "v_inf_kms": 8.1,
      "h_mag": 29.5,
      "body": "Earth"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### Get Single Close Approach

```
GET /close-approaches/{des}/{orbit_id}/{close_approach_time}
```

Path parameters:
- `des` — Object designation
- `orbit_id` — Orbit solution ID
- `close_approach_time` — ISO 8601 timestamp (UTC)

---

### Orion Ephemeris (JPL Horizons)

#### List Ephemeris Records

```
GET /orion
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | datetime | — | Start date (UTC, ISO 8601) |
| `date_to` | datetime | — | End date (UTC, ISO 8601) |
| `target_id` | string | `-1024` | Target ID (Orion = -1024) |
| `limit` | int | 100 | Max results (1–1000) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "items": [
    {
      "target_id": "-1024",
      "epoch": "2026-04-02T02:00:00Z",
      "jd": 2460764.5833,
      "x_km": -123456.7,
      "y_km": 234567.8,
      "z_km": -34567.9,
      "vx_kms": -0.5,
      "vy_kms": 1.2,
      "vz_kms": -0.1,
      "speed_kms": 1.3,
      "light_time_s": 1.23,
      "range_km": 384400.0,
      "range_rate_kms": -0.02
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### Get Single Ephemeris Record

```
GET /orion/{target_id}/{epoch}
```

---

### DONKI Space Weather Events

#### List Events

```
GET /donki
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | datetime | — | Start date (UTC, ISO 8601) |
| `date_to` | datetime | — | End date (UTC, ISO 8601) |
| `event_types` | string | — | Comma-separated list (e.g., `CME,SEP,FLR`) |
| `limit` | int | 100 | Max results (1–1000) |
| `offset` | int | 0 | Pagination offset |

**Supported Event Types:**
- `CME` — Coronal Mass Ejection
- `CMEAnalysis` — CME Analysis
- `SEP` — Solar Energetic Particle
- `FLR` — Solar Flare
- `IPS` — Interplanetary Shock
- `GST` — Geomagnetic Storm
- `RBE` — Radiation Belt Enhancement
- `HSS` — High Speed Stream
- `MPC` — Magnetopause Crossing
- `WSAEnlilSimulations` — WSA-Enlil Simulation

**Response:**
```json
{
  "items": [
    {
      "event_type": "CME",
      "event_id": "2026-04-09T17:09:00-CME-001",
      "start_time": "2026-04-09T17:09:00Z",
      "end_time": null,
      "event_time": "2026-04-09T17:09:00Z",
      "fetched_at": "2026-10-04T07:51:13Z",
      "source_url": "https://ccmc.gsfc.nasa.gov/DONKI-API/get/CME?...",
      "payload": { ... }
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### Get Event Types

```
GET /donki/event-types
```

Returns array of supported event type strings.

#### Get Single Event

```
GET /donki/{event_type}/{event_id}
```

---

## Data Models

All models are defined in the [`contracts`](../../contracts/src/contracts/models.py) package and re-exported from `backend.api`.

### CloseApproach

```python
des: str
orbit_id: str
close_approach_jd: float
close_approach_time: datetime
dist_au: float | None
dist_min_au: float | None
dist_max_au: float | None
v_rel_kms: float | None
v_inf_kms: float | None
h_mag: float | None
body: str = "Earth"
```

### OrionEphemeris

```python
target_id: str
epoch: datetime
jd: float
x_km: float | None
y_km: float | None
z_km: float | None
vx_kms: float | None
vy_kms: float | None
vz_kms: float | None
speed_kms: float | None
light_time_s: float | None
range_km: float | None
range_rate_kms: float | None
```

### DonkiEvent

```python
event_type: str
event_id: str
start_time: datetime | None
end_time: datetime | None
event_time: datetime | None
fetched_at: datetime
source_url: str
payload: dict[str, Any]  # Complete DONKI JSON
```

---

## Configuration

Environment variables (from `.env` in project root):

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name |
| `DATABASE_URL` | Full connection string (overrides above) |

Default database URL: `postgresql://USER:PASSWORD@localhost:5433/DB`

---

## Development

### Install Dependencies

```bash
uv sync --package backend
```

### Run Tests

```bash
# Unit tests
uv run --package backend pytest tests/unit/backend/

# Integration tests (requires running DB)
uv run --package backend pytest tests/integration/backend/
```

### Project Structure

```
packages/backend/src/backend/
├── api/
│   ├── __init__.py          # FastAPI app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── synthetic.py          # 12 synthetic telemetry endpoints
│   │   ├── close_approaches.py
│   │   ├── orion.py
│   │   ├── donki.py
│   │   ├── iswa_goes_protons.py
│   │   └── jpl_dsn_geometry.py
├── db/
│   └── session.py           # Database connection
├── main.py                  # Uvicorn entry point
├── static/                  # Static files (if any)
└── ws/                      # WebSocket handlers (future)
```

---

## Adding New Endpoints

1. Add Pydantic models to `packages/contracts/src/contracts/models.py`
2. Create route module in `api/routes/`
3. Import and include router in `api/__init__.py`
4. Add tests in `tests/unit/backend/api/routes/`

---

## License

Part of the Telemetry Project — Data Tribe.