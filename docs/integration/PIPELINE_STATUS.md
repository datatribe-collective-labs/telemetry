# End-to-End Pipeline Status

**Last Updated:** 2026-10-19

## ✅ Completed

### 1. Contracts Normalization (ODCS v3.1.0)
All 5 ODCS YAML files updated with **lowercase field IDs/names** to match PostgreSQL column naming:
- `packages/contracts/src/odcs/01_state_engine.odcs.yaml`
- `packages/contracts/src/odcs/02_thermal_model.odcs.yaml`
- `packages/contracts/src/odcs/03_power_comms_radiation.odcs.yaml`
- `packages/contracts/src/odcs/04_cross_model_telemetry_packet.odcs.yaml`
- `packages/contracts/src/odcs/05_anomaly_ml_features.odcs.yaml`

**39 fields renamed** (e.g., `solar_flux_W_m2` → `solar_flux_w_m2`, `temp_sun_face_K` → `temp_sun_face_k`, `r_RE` → `r_re`)

### 2. Pydantic Models (`packages/contracts/src/contracts/models.py`)
All synthetic telemetry models updated to lowercase field names matching contracts.

### 3. Physics Models Package (`packages/physics_models/`)
- **Producer** (`kafka/producer.py`): Uses `msg.model_dump_json()` → automatically emits lowercase field names
- **Runner** (`runner.py`): ✅ Wired to real models (2026-10-19) — state engine interpolates NASA OEM arcs (`data/oem/`), thermal/power run `ThermalModel3Node` / `PowerModel`; comms, radiation, packet, anomaly and ML remain placeholder values
- **OEM loader** (`oem.py`): Parses CCSDS OEM v2.0 arcs (store zip-of-zips), linear interpolation
- **Cross-Model Bus** (`cross_model/bus.py`): 1-tick lag coupling (live thermal↔power paths)
- **Consumer** (`packages/physics_models/consumer.py`, package root): New Kafka → TimescaleDB consumer service
  - Subscribes to: `trajectory`, `telemetry`, `cross_model_state`, `ml_features`
  - Writes to TimescaleDB hypertables with upsert logic
  - Handles telemetry topic demultiplexing (thermal/power/comms/radiation/packet)

### 4. Database Schema (Alembic)
Tables already exist via `packages/backend/alembic/versions/611662aa06a2_add_synthetic_telemetry_tables.py`:
- `state_snapshot`, `thermal_output`, `power_output`, `comms_output`, `radiation_output`
- `telemetry_packet`, `cross_model_state`, `ml_feature_vectors`, `anomaly_events`

All columns are **lowercase** (PostgreSQL default).

### 5. Backend API (`packages/backend/src/backend/api/routes/synthetic.py`)
12 synthetic telemetry endpoints with lowercase column lists (28 REST endpoints total incl. real data + health):
- `GET /telemetry/synthetic/state`
- `GET /telemetry/synthetic/state/{timestamp_utc}`
- `GET /telemetry/synthetic/thermal`
- `GET /telemetry/synthetic/power`
- `GET /telemetry/synthetic/comms`
- `GET /telemetry/synthetic/radiation`
- `GET /telemetry/synthetic/cross-model`
- `GET /telemetry/synthetic/packet`
- `GET /telemetry/synthetic/packet/{timestamp_utc}`
- `GET /telemetry/synthetic/anomalies`
- `GET /telemetry/synthetic/ml-features`
- `GET /telemetry/synthetic/latest` (combined packet)

### 6. Dashboard (`dashboard/src/prototype/pages/*.py`)
All 6 Streamlit pages updated to use lowercase field names when querying backend API:
- `overview.py`, `trajectory.py`, `thermal.py`, `power.py`, `space_weather.py`, `dsn_coverage.py`

### 7. Docker Compose Services
```yaml
services:
  redpanda:          # Kafka (healthy)
  timescaledb:       # PostgreSQL + TimescaleDB (healthy)
  physics_models:    # Producer → Kafka at 1 Hz
  physics_models_consumer:  # Consumer → TimescaleDB
```

## 🔄 Running Services

### Startup Order (per RUN_SERVICES.md)
```bash
# 1. Infrastructure
docker compose up -d redpanda timescaledb

# 2. Physics Models Producer
docker compose up -d --build --force-recreate physics_models

# 3. Consumer (Kafka → TimescaleDB)
docker compose up -d --build --force-recreate physics_models_consumer

# 4. Backend API (host, port 8000)
uv run --package backend python -m backend.main

# 5. Streamlit Dashboard (host, port 8501)
uv run --package streamlit_dashboard streamlit run dashboard/src/prototype/app.py
```

## ✅ Verified Working

| Component | Status | Verification |
|-----------|--------|--------------|
| Kafka Producer | ✅ | `rpk topic consume trajectory --offset -1` shows lowercase fields |
| Kafka Consumer | ✅ | Logs show "Inserted trajectory/thermal/power/comms/radiation/packet/cross_model_state/ml_features" |
| TimescaleDB | ✅ | Row counts: state_snapshot=216, thermal=1142, power=1142, comms=1142, radiation=1188, packet=44, cross_model=1143, ml_features=1141 |
| Backend API | ✅ | All `/telemetry/synthetic/*` endpoints return data with lowercase JSON keys |
| Dashboard | ✅ | Pages load and query backend successfully |

## 📋 Key Technical Decisions

1. **No hardcoded defaults** - All DB/Kafka config via required env vars (`DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS`)
2. **psycopg[binary]** - Correct SQLAlchemy 2.0 + psycopg v3 driver (`postgresql+psycopg://` URL scheme)
3. **Alembic for schema** - Tables managed via migrations, not auto-create
4. **Lowercase everywhere** - Contracts, Pydantic, SQL, JSON all use snake_case lowercase
5. **Consumer demultiplexing** - Single `telemetry` topic → 5 tables via discriminator fields (check `spacecraft_id` first for packet)

## ⚠️ Known Gaps (Not Blocking)

| Gap | Owner | Status |
|-----|-------|--------|
| Comms model (Rafaela) | Rafaela | Not implemented — placeholder values from runner |
| Radiation model (Rafaela) | Rafaela | Not implemented — placeholder values from runner |
| Packet assembler (Rafaela) | Rafaela | Not implemented — runner assembles inline |
| Anomaly detector + ML features | - | Skeleton only — placeholders |
| WebSocket endpoints (`/ws/live`, `/ws/events`) | Backend | Not implemented |
| OEM loader + wiring of state/thermal/power into runner | - | ✅ Done (2026-10-19) |
| Timeline events fact-check vs PDF | - | Pending — `mission_events` is DRAFT |
| Real data ingestion pipelines | — | Exist in this repo (`packages/pipelines`); run manually, not part of docker stack |

## 🧪 Quick Verification Commands

```bash
# Check Kafka messages have lowercase fields
docker exec telemetry-redpanda-1 rpk topic consume trajectory --offset -1 --num 1

# Check DB row counts
docker exec telemetry-timescaledb-1 psql -U telemetry_artemis_2 -d telemetry -c "SELECT count(*) FROM state_snapshot; SELECT count(*) FROM thermal_output;"

# Test backend endpoints
curl -s "http://localhost:8000/telemetry/synthetic/state?limit=1" | jq .
curl -s "http://localhost:8000/telemetry/synthetic/thermal?limit=1" | jq .
curl -s "http://localhost:8000/telemetry/synthetic/packet?limit=1" | jq .

# Health checks
curl -s http://localhost:8000/health
curl -s http://localhost:8501/_stcore/health
```