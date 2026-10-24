# Synthetic Telemetry API

REST endpoints for querying the Artemis II / Orion digital twin's physics
model outputs — deterministic, physically defensible synthetic telemetry that
replaces unavailable AROW attitude telemetry.

## Data Models

**Location:** `packages/contracts/src/contracts/models.py`

Pydantic models matching the ODCS contracts in `packages/contracts/src/odcs/`:

| Model | ODCS contract | Kafka topic | Table |
|-------|---------------|-------------|-------|
| `SyntheticStateSnapshot` | 01_state_engine | `trajectory` | `state_snapshot` |
| `SyntheticThermalOutput` | 02_thermal_model | `telemetry` | `thermal_output` |
| `SyntheticPowerOutput` | 03_power_comms_radiation | `telemetry` | `power_output` |
| `SyntheticCommsOutput` | 03_power_comms_radiation | `telemetry` | `comms_output` |
| `SyntheticRadiationOutput` | 03_power_comms_radiation | `telemetry` | `radiation_output` |
| `SyntheticCrossModelState` | 04_cross_model_telemetry_packet | `cross_model_state` | `cross_model_state` |
| `SyntheticTelemetryPacket` | 04_cross_model_telemetry_packet | `telemetry` | `telemetry_packet` |
| `SyntheticAnomalyEvent` | 05_anomaly_ml_features | `events` | `anomaly_events` |
| `SyntheticMLFeatureVector` | 05_anomaly_ml_features | `ml_features` | `ml_feature_vectors` |

All models use `ConfigDict(from_attributes=True)` for SQLAlchemy ORM
compatibility.

## Endpoints

**Location:** `packages/backend/src/backend/api/routes/synthetic.py`

All under the `/telemetry/synthetic` prefix (kept separate from real JPL/NASA
data endpoints, which have no prefix). All list endpoints support
pagination (`limit`, `offset`) and ISO `date_from`/`date_to` filters, and
return `{items, total, limit, offset}`.

| Endpoint | Extra filters |
|----------|---------------|
| `GET /telemetry/synthetic/state` | — |
| `GET /telemetry/synthetic/state/{timestamp_utc}` | — |
| `GET /telemetry/synthetic/thermal` | `thermal_state` |
| `GET /telemetry/synthetic/power` | `power_state` |
| `GET /telemetry/synthetic/comms` | `comm_state` |
| `GET /telemetry/synthetic/radiation` | `sep_event_active` |
| `GET /telemetry/synthetic/cross-model` | — |
| `GET /telemetry/synthetic/packet` | `all_nominal`, `thermal_state`, `power_state`, `comm_state` |
| `GET /telemetry/synthetic/packet/{timestamp_utc}` | — |
| `GET /telemetry/synthetic/latest` | — |
| `GET /telemetry/synthetic/anomalies` | `anomaly_type`, `detection_layer`, `severity`, `mission_phase` |
| `GET /telemetry/synthetic/ml-features` | — |

## Database & Migrations

- **ORM:** `packages/backend/src/backend/models.py` — declarative SQLAlchemy
  models for all 12 application tables (9 synthetic + the 3 real-data tables
  `close_approaches`, `orion_ephemeris`, `donki_events`).
- **Migrations:** Alembic (`packages/backend/alembic/`) is the authoritative
  schema manager. The `process_revision_directives` hook in `env.py` injects
  `CREATE EXTENSION IF NOT EXISTS timescaledb` and one `create_hypertable()`
  call per synthetic table (real-data tables are pre-existing hypertables /
  regular tables and are deliberately excluded from injection). Initial
  migration: `611662aa06a2_add_synthetic_telemetry_tables`.
- **Column naming:** DB columns are lowercase snake_case
  (`temp_sun_face_k`, `eirp_dbw`, ...). The routes alias them back to contract
  field names in `SELECT` (`_select_columns()`), so JSON keys match the ODCS
  contract exactly; Pydantic validation passes unchanged.

```bash
# verify drift
uv run --package backend alembic check
```

## Data Flow

```
OEM/Horizons → State Engine → [Thermal, Power, Comms, Radiation]
                                        ↓
                              Cross-Model State Bus (1-tick lag)
                                        ↓
                              Telemetry Packet → Kafka → consumer → TimescaleDB
                                        ↓
                              Anomaly Detection → events + ml_features
```

The `SyntheticStateSnapshot` includes nullable `roll_deg`/`pitch_deg`/`yaw_deg`
for AROW; physics models don't need them — they derive geometry from
`solar_incidence_angle_deg` and `solar_array_angle_deg`.
