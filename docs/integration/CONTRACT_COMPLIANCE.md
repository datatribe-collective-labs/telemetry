# Contract compliance

How well the simulator's output (the **synthetic data**) meets the ODCS data contracts in
`packages/contracts/src/odcs/`, contract by contract. How the models work:
[`architecture/PHYSICS_MODELS.md`](../architecture/PHYSICS_MODELS.md). Open work is
tracked in GitHub issues; this doc only records the current state.

## The contracts

Five ODCS v3.1.0 files define nine data products. Each field has a type, a unit, whether it
is required, and quality rules: no nulls, allowed values, physical bounds and cross-field
consistency. The contracts are the source of truth. The Pydantic models in
`contracts.models` follow them, and every name is lowercase snake_case all the way from
the simulator to the dashboard.

| File | Contract (version) | Pydantic model | Kafka topic | Table | Status |
|------|--------------------|----------------|-------------|-------|--------|
| `01_state_engine` | `state_engine_snapshot` (1.1.0) | `SyntheticStateSnapshot` | `trajectory` | `state_snapshot` | Implemented; attitude angles are 0 |
| `02_thermal_model` | `thermal_model_output` (1.1.0) | `SyntheticThermalOutput` | `telemetry` | `thermal_output` | Implemented |
| `03_power_comms_radiation` | `power_model_output` (1.2.0) | `SyntheticPowerOutput` | `telemetry` | `power_output` | Implemented; two consistency rules open (#73) |
| `03_power_comms_radiation` | `comms_model_output` (1.2.0) | `SyntheticCommsOutput` | `telemetry` | `comms_output` | Implemented |
| `03_power_comms_radiation` | `radiation_model_output` (1.1.0) | `SyntheticRadiationOutput` | `telemetry` | `radiation_output` | Implemented; degradation factors are 1.0 |
| `04_cross_model_telemetry_packet` | `cross_model_state` (1.2.0) | `SyntheticCrossModelState` | `cross_model_state` | `cross_model_state` | Implemented; radiation couplings are 1.0 |
| `04_cross_model_telemetry_packet` | `telemetry_packet` (1.2.0) | `SyntheticTelemetryPacket` | `telemetry` | `telemetry_packet` | Implemented |
| `05_anomaly_ml_features` | `anomaly_events` (1.2.0) | `SyntheticAnomalyEvent` | `events` | `anomaly_events` | **Placeholder**: nothing is detected |
| `05_anomaly_ml_features` | `ml_feature_vectors` (1.2.0) | `SyntheticMLFeatureVector` | `ml_features` | `ml_feature_vectors` | **Placeholder**: fixed values |

## How the rules are enforced

| Layer | Where | What it catches |
|-------|-------|-----------------|
| Types and enums | `contracts.models` (Pydantic) | Wrong types, missing required fields, values outside an enum (for example `power_state`), a few numeric bounds |
| Tick validation | `physics_models/packet/validation.py` | The contract rules that span fields or models, checked before a tick is published (see below). An invalid tick is not published |
| Unit tests | `tests/unit/physics_models/`, `tests/unit/contracts/` | Each model's physics against the contract bounds; the radiation calibration on the real trajectory |
| Database | Alembic migrations | Column types; `timestamp_utc` primary key, so a replayed tick overwrites the old row |

Tick validation covers a selection of the rules, not all of them: timestamps match and
numbers are finite in every output; eclipse fraction and battery charge are in range;
temperatures are above 0 K; solar array power is 0 in `UMBRA`; `power_state` matches the
battery charge; the comms state, rate, quality, margin and loss reason agree with each
other and with DSN visibility; the dose rates add up and their units agree; the packet
matches its subsystems. Other rules (for example the solar flux band or speed limits) are
covered by the unit tests, not checked live.

## Contract by contract

### State engine (`01`)

All required fields are computed from the NASA OEM arc and the models in
`state_engine/` (EME2000, UTC). DSN visibility uses the three DSN sites with a 10°
elevation cutoff and the Moon's line of sight. Solar incidence and array angles are
estimates from the planned attitude mode, not a resolved attitude.

**Deviation:** `roll_deg`, `pitch_deg` and `yaw_deg` are 0 on every tick. They are optional
in the contract, and Orion's attitude is not public.

### Thermal (`02`)

All fields are implemented by the three-node model. `thermal_state` follows the contract's
temperature limits. The heater setpoint (−5 °C) and power (25 W) are marked
`MODEL_ASSUMPTION` in the contract. The 249–310 K electronics band comes from the SLS
flight computer and is used as a reference, not as an Orion requirement.

### Power (`03`)

All fields are implemented. `power_state` is set strictly from the battery charge, as the
contract requires, and `available_power_w` is `array x 0.92 − 800 W`. Array size,
efficiency, battery capacity and the 1,200 W load are model assumptions.

**Open (#73):**
- `net_power_w` is `array − load`, without the 0.92 distribution factor that the battery
  current sign rule uses.
- `|battery_current_a| = |net_power_w| / battery_voltage_v` does not hold while charging,
  because charge current is capped at 50 A and the surplus is not reported anywhere.

Neither changes the battery behaviour on the mission arc. Both need a decision on
contract 03 first.

### Comms (`03`)

All fields are implemented, including `link_loss_reason`. The path loss follows the Friis
equation, the margin is `Eb/N0 − required Eb/N0`, and the data rate comes from the contract's
rate set. Orion's EIRP is calibrated, because its transmit power and antenna gain are not
published. The lower rate steps are `UNVERIFIED` in the contract.

**Scope:** only the Deep Space Network is modelled. The real Orion also used the Near
Space Network close to Earth, so the simulated link has gaps there that the real one did
not.

### Radiation (`03`)

All fields are implemented: belt and cosmic-ray dose rates, cumulative doses and
`radiation_zone`, at one simulated cabin sensor calibrated to Artemis I.
`sep_event_active` is false, because the GOES proton flux during the mission stayed below
10 pfu.

**Deviation:** `solar_array_degradation`, `thermal_alpha_degradation` and
`thermal_eps_degradation` are 1.0 (not modelled). That is within the contract's (0, 1] range.

### Cross-model state (`04`)

All eight fields are published every tick, with a one-tick lag. The radiation-driven
factors and `plasma_noise_factor` are 1.0, so they have no effect. The thermal model does
not read the coating factors.

### Telemetry packet (`04`)

All fields are filled from that tick's model outputs, also on `NO_LINK` ticks.
`all_nominal` is derived from the subsystem states, and validation checks that it agrees.

### Anomaly events and ML features (`05`)

**Placeholders.** The contract describes a three-layer detector (contract rules, physics
rules, ML) and a 23-field feature vector. The runner's detector never fires, so the `events`
topic stays empty. The feature vector is published with fixed values, apart from
`signal_quality` and `dsn_visible`. Both are kept so that the topics, tables and routes
exist end to end.

## Known weaknesses

- **NaN hidden by clamps (#91).** Some model limits use `max(low, min(high, x))`, which
  turns `NaN` into the upper limit, so tick validation would not see it. There is no known
  trigger on the mission arc.
- **Timeline is a draft.** The planned attitude timeline (`contracts.planned_attitude`),
  which drives the solar angles, was extracted from NASA's timeline PDF but not checked
  row by row (checklist in [`docs/archive/`](../archive/TIMELINE_FACTCHECK_CHECKLIST.md)).
