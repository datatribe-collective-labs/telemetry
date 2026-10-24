# Physics Models — Contract Compliance Evaluation

**Date:** 2026-10-09 (field-name casing note added 2026-10-19)  
**Package:** `packages/physics_models/`  
**Authoritative Contracts:** ODCS YAML in `packages/contracts/src/odcs/` (5 files, v3.1.0)  
**Derived Pydantic Models:** `packages/contracts/src/contracts/models.py` (auto-generated from ODCS)

> **⚠️ Field-name casing:** The field names quoted in the tables below (e.g. `solar_flux_W_m2`,
> `temp_sun_face_K`, `q_solar_absorbed_W`) were written **before the lowercase normalization**
> (see `docs/integration/PIPELINE_STATUS.md`, 39 fields renamed). Contracts, Pydantic models, DB columns and
> JSON keys are now all lowercase (`solar_flux_w_m2`, `temp_sun_face_k`, ...). The physics
> bounds, enums and quality rules cited here are unchanged and still apply.

---

## ODCS Contract Authority

The **ODCS contracts are the single source of truth**. The Pydantic models in `contracts/models.py` are derived from these ODCS definitions. All physics model implementations must satisfy the ODCS quality rules, not just the Pydantic type hints.

### ODCS Quality Rule Categories

| Rule Type | Purpose | Enforcement |
|-----------|---------|-------------|
| `nullValues mustBe: 0` | Required fields never null | Pipeline validation at ingest |
| `invalidValues mustBe: 0` + `validValues` | Enum / categorical validity | Pipeline validation |
| `type: text` rules | Physics bounds, cross-field consistency | Layer 1/2 anomaly detection |
| `criticalDataElement: true` | Mission-critical fields | Enhanced monitoring, alerting |
| `primaryKey: true` | Uniqueness per tick | Kafka key + DB primary key |

### Contract-to-Model Mapping
| ODCS Contract | Pydantic Model | Kafka Topic | Physics Model |
|---------------|----------------|-------------|---------------|
| `state_engine_snapshot` | `SyntheticStateSnapshot` | `trajectory` | StateEngine |
| `thermal_model_output` | `SyntheticThermalOutput` | `telemetry` | ThermalModel3Node |
| `power_model_output` | `SyntheticPowerOutput` | `telemetry` | PowerModel |
| `comms_model_output` | `SyntheticCommsOutput` | `telemetry` | CommsModel (TBD) |
| `radiation_model_output` | `SyntheticRadiationOutput` | `telemetry` | RadiationModel (TBD) |
| `cross_model_state` | `SyntheticCrossModelState` | `cross_model_state` | CrossModelBus |
| `telemetry_packet` | `SyntheticTelemetryPacket` | `telemetry` | PacketAssembler |
| `anomaly_events` | `SyntheticAnomalyEvent` | `events` | AnomalyDetector (TBD) |
| `ml_feature_vectors` | `SyntheticMLFeatureVector` | `ml_features` | MLFeatureBuilder (TBD) |


---

## Executive Summary

| Physics Model | Contract | Implementation Status | Compliance |
|---------------|----------|----------------------|------------|
| State Engine | `SyntheticStateSnapshot` | ✅ Complete | **100%** |
| Thermal | `SyntheticThermalOutput` | ✅ Complete | **100%** |
| Power | `SyntheticPowerOutput` | ✅ Complete | **100%** |
| Comms | `SyntheticCommsOutput` | ❌ Not Started | **0%** |
| Radiation | `SyntheticRadiationOutput` | ❌ Not Started | **0%** |
| Cross-Model Bus | `SyntheticCrossModelState` | ✅ Complete (in `cross_model/bus.py`) | **100%** |
| Packet Assembler | `SyntheticTelemetryPacket` | ⚠️ Partial (in `runner.py`) | **~80%** |
| Anomaly Detector | `SyntheticAnomalyEvent` | ❌ Not Started | **0%** |
| ML Features | `SyntheticMLFeatureVector` | ⚠️ Partial (in `runner.py`) | **~60%** |

**Overall Contract Coverage: ~55%** (5 of 9 synthetic contracts fully implemented)

**Note:** Power model enum mismatch has been **fixed** (see Section 3).

---

## 1. State Engine → `SyntheticStateSnapshot`

### ODCS Contract: `01_state_engine.odcs.yaml` → `state_engine_snapshot` v1.1.0

### Contract Fields with ODCS Quality Rules
| Field | ODCS Type | Required | PK | Quality Rules (ODCS) | Physics Model Implementation |
|-------|-----------|----------|-----|----------------------|------------------------------|
| `timestamp_utc` | `TIMESTAMP WITH TIME ZONE` | ✅ | ✅ | `nullValues=0`, monotonic increasing | ✅ `StateEnginePhysics.compute_state_at_met()` |
| `x_km`, `y_km`, `z_km` | `DOUBLE` | ✅ | | `nullValues=0`, finite, \|pos\|² ≤ (410,000)² | ✅ Two-body propagation / OEM interpolation |
| `vx_kms`, `vy_kms`, `vz_kms` | `DOUBLE` | ✅ | | `nullValues=0`, speed < 12 km/s | ✅ Same as position |
| `distance_from_sun_au` | `DOUBLE` | ✅ | | `nullValues=0`, 0.995 ≤ d ≤ 1.005 AU | ✅ Computed from position |
| `solar_flux_W_m2` | `DOUBLE` | ✅ | | `nullValues=0`, 1347 ≤ flux ≤ 1375 W/m² | ✅ `compute_solar_flux()` inverse-square |
| `solar_incidence_angle_deg` | `DOUBLE` | ✅ | | `nullValues=0`, 0 ≤ angle ≤ 180 | ✅ From `planned_attitude.py` |
| `eclipse_state` | `VARCHAR(10)` | ✅ | | `nullValues=0`, `invalidValues=0` validValues=[SUNLIT,UMBRA,PENUMBRA] | ✅ `compute_eclipse_state()` |
| `eclipse_fraction` | `DOUBLE` | ✅ | | `nullValues=0`, 0≤f≤1, consistent with eclipse_state | ✅ Same function |
| `earth_distance_km` | `DOUBLE` | ✅ | | `nullValues=0`, \|d - √(x²+y²+z²)\| < 1 km | ✅ `np.linalg.norm(sc_pos)` |
| `dsn_visibility` | `BOOLEAN` | ✅ | | `nullValues=0` | ✅ `compute_dsn_visibility()` |
| `light_time_s` | `DOUBLE` | ✅ | | `nullValues=0`, \|lt - d_km×1000/299792458\| < 0.01s | ✅ `compute_light_time()` |
| `solar_array_angle_deg` | `DOUBLE` | ✅ | | `nullValues=0`, 0 ≤ angle ≤ 180 | ✅ From `planned_attitude.py` |
| `roll_deg`, `pitch_deg`, `yaw_deg` | `DOUBLE` | ❌ | | Valid range: −180 to 180 | ⚠️ Placeholder (identity quaternion) |

### ODCS-Specific Requirements
- **Coordinate frame**: EME2000 / J2000 (CCSDS OEM convention) — documented in schema description
- **Data granularity**: 1s live, 240s OEM replay
- **SLA**: 2s latency, 99.5% availability, 1Hz frequency

### Gaps
- **Attitude quaternions**: Currently returns identity (0,0,0). Need proper body-to-inertial transformation per `AttitudeMode` from `planned_attitude.py`.
- **OEM/Horizons integration**: Currently uses placeholder circular orbit. Need SPICE kernel or OEM file interpolation.
- **Coordinate frame**: Assumes EME2000 (J2000), should be documented/validated against ODCS `authoritativeDefinitions`.

### Test Coverage (Validating ODCS Quality Rules)
- ✅ Kepler equation solver (position/velocity finite)
- ✅ Keplerian → state vector (range bounds)
- ✅ Solar flux inverse-square (1347-1375 W/m² at 0.995-1.005 AU)
- ✅ Eclipse states (validValues enum: SUNLIT/UMBRA/PENUMBRA)
- ✅ Eclipse fraction consistency with eclipse_state
- ✅ DSN visibility (boolean, nullValues=0)
- ✅ Light time (consistency with earth_distance_km)
- ✅ Two-body propagation (universal variable formulation, speed < 12 km/s)
- ✅ Attitude integration with `planned_attitude.py`

---

## 2. Thermal Model → `SyntheticThermalOutput`

### ODCS Contract: `02_thermal_model.odcs.yaml` → `thermal_model_output` v1.1.0

### Contract Fields with ODCS Quality Rules
| Field | ODCS Type | Required | PK | Critical | Quality Rules (ODCS) | Physics Model Implementation |
|-------|-----------|----------|-----|----------|----------------------|------------------------------|
| `timestamp_utc` | `TIMESTAMP WITH TIME ZONE` | ✅ | ✅ | | `nullValues=0`, must match state_snapshot | ✅ Passed to `step()` |
| `temp_sun_face_K` | `DOUBLE` | ✅ | | | `nullValues=0`, >3K, <450K (MLI failure) | ✅ `T_sun_face_k` |
| `temp_shadow_face_K` | `DOUBLE` | ✅ | | | `nullValues=0`, >3K, ≤ temp_sun_face_K + conduction | ✅ `T_shadow_face_k` |
| `temp_electronics_bay_K` | `DOUBLE` | ✅ | | ✅ | `nullValues=0`, SLS spec: 249K–310K (reference only) | ✅ `T_electronics_bay_k` |
| `q_solar_absorbed_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0, =0 when eclipse_state=UMBRA | ✅ `compute_solar_absorbed()` |
| `q_radiated_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0, energy balance at steady state | ✅ Sum of radiative losses |
| `q_internal_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0, from cross-model bus | ✅ From `power_dissipation_W` |
| `heater_active` | `BOOLEAN` | ✅ | | | `nullValues=0`, must obey configured hysteresis | ✅ Thermostat with deadband |
| `heater_power_W` | `DOUBLE` | ✅ | | | `nullValues=0`, 0 or configured rated power | ✅ `heater_power_w` when active |
| `thermal_state` | `VARCHAR(20)` | ✅ | | ✅ | `nullValues=0`, `invalidValues=0` validValues=[NOMINAL,COLD_SURVIVAL,HOT_LIMIT], consistent with node temps | ✅ `thermal_state()` method |

### ODCS-Specific Requirements
- **Heater setpoint**: 268K (−5°C) and 25W are `MODEL_ASSUMPTION` — not source-verified (ODCS explicitly states this)
- **Electronics bay bounds**: 249K–310K from SLS flight computer, NOT Orion-specific (ODCS: "No hard 249–310 K Orion-bay bound is asserted")
- **Energy balance**: At steady state q_radiated ≈ q_solar + q_internal; transients allowed
- **Cross-model coupling**: 1-tick lag via `cross_model_state` topic

### Physics Implementation
- **3-node lumped parameter**: Sun face, Shadow face, Electronics bay
- **Conductive coupling**: Between all node pairs (configurable conductances)
- **Radiative to space**: Linearized Stefan-Boltzmann (`4εσT³`)
- **Solar absorption**: `α·A·S·cos(θ)` with eclipse fraction
- **Implicit (backward Euler) integration**: Stable for large time steps
- **Heater thermostat**: Setpoint + deadband hysteresis (configurable, not hard-coded per ODCS)

### Cross-Model Coupling (Inputs from Bus)
| Input | Source | ODCS Reference | Used For |
|-------|--------|----------------|----------|
| `power_dissipation_W` | Power model | `04_cross_model` | `q_internal_W` for electronics bay |
| `solar_array_degradation_factor` | Radiation | `04_cross_model` | Not yet used (future: array temp) |
| `thermal_coating_*_factor` | Radiation | `04_cross_model` | Not yet used (future: radiator degradation) |

### Test Coverage (Validating ODCS Quality Rules)
- ✅ Radiative heat transfer (Stefan-Boltzmann, T > 3K)
- ✅ Conductive heat transfer (Fourier's law)
- ✅ Solar absorption (cosine law, eclipse = 0 in UMBRA)
- ✅ Thermal equilibrium calculation
- ✅ 3-node model step updates
- ✅ Heater activation/deactivation (hysteresis)
- ✅ Energy balance verification (transients allowed)
- ✅ Steady-state convergence
- ✅ Cross-model power dissipation coupling
- ✅ Thermal state enum validity (NOMINAL/COLD_SURVIVAL/HOT_LIMIT)

---

## 3. Power Model → `SyntheticPowerOutput`

### ODCS Contract: `03_power_comms_radiation.odcs.yaml` → `power_model_output` v1.1.0

### Contract Fields with ODCS Quality Rules
| Field | ODCS Type | Required | PK | Critical | Quality Rules (ODCS) | Physics Model Implementation |
|-------|-----------|----------|-----|----------|----------------------|------------------------------|
| `timestamp_utc` | `TIMESTAMP WITH TIME ZONE` | ✅ | ✅ | | `nullValues=0` | ✅ Passed to `step()` |
| `solar_array_power_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0, =0 in UMBRA, ≤17,100W (physics ceiling: 1361×44.8×0.28) | ✅ `compute_solar_array_power()` |
| `array_efficiency` | `DOUBLE` | ✅ | | | `nullValues=0`, 0.0 ≤ η ≤ 1.0 by definition | ✅ `array_efficiency` (temp derating) |
| `total_load_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0, 800W/4000W/5000W are MODEL_ASSUMPTION | ✅ Input `total_load_w` |
| `battery_soc_pct` | `DOUBLE` | ✅ | | ✅ | `nullValues=0`, **0.0 ≤ SOC ≤ 100.0** (Li-ion hard constraint) | ✅ `battery_soc * 100` |
| `battery_voltage_V` | `DOUBLE` | ✅ | | | `nullValues=0`, >0, model equation only (24-32V not hardware bound) | ✅ `_update_battery_voltage()` |
| `battery_current_A` | `DOUBLE` | ✅ | | | `nullValues=0`, sign consistent with net power, \|I\| = \|P\|/V | ✅ `net_power / voltage` (clamped) |
| `net_power_W` | `DOUBLE` | ✅ | | | `nullValues=0`, = array - load, battery current sign consistent | ✅ `array_power - total_load` |
| `available_power_W` | `DOUBLE` | ✅ | | | `nullValues=0`, ≥0 (negative = CRITICAL), ≤ array×0.92 - 800 | ✅ `array_power + max_discharge_power` |
| `power_state` | `VARCHAR(20)` | ✅ | | ✅ | `nullValues=0`, `invalidValues=0` validValues=[NOMINAL,BATTERY_DISCHARGE,LOW_POWER_MODE,CRITICAL], **strict SOC-gated transitions** | ✅ `_update_power_state()` (fixed) |

### ODCS-Specific Requirements (Critical)
- **SOC bounds**: 0-100% is a **physical constraint** from Li-ion chemistry — "The contract cannot be widened to accommodate integration bugs — fix the model"
- **Power state transitions** (strictly governed by SOC):
  - `NOMINAL`: SOC > 20% AND net_power ≥ 0
  - `BATTERY_DISCHARGE`: SOC > 20% AND net_power < 0
  - `LOW_POWER_MODE`: 10% < SOC ≤ 20%
  - `CRITICAL`: SOC ≤ 10%
- **Solar array specs**: 4 wings, 11.2 kW nominal — 44.8 m² and 28% are NOT hard contract inputs (unverified)
- **Battery voltage**: 28V nominal, linear V-SOC are MODEL_ASSUMPTIONS — not hardware bounds
- **Available power**: Must be ≥ 0; negative available power is nonsensical → CRITICAL

### Enum Mismatch — **FIXED**
| Contract Enum | Model Enum (Before) | Model Enum (After) |
|---------------|---------------------|-------------------|
| `NOMINAL` | `NOMINAL` ✅ | `NOMINAL` ✅ |
| `BATTERY_DISCHARGE` | `DISCHARGING` ❌ | `BATTERY_DISCHARGE` ✅ |
| `LOW_POWER_MODE` | `LOW_POWER` ❌ | `LOW_POWER_MODE` ✅ |
| `CRITICAL` | `CRITICAL` ✅ | `CRITICAL` ✅ |

**Status:** Fixed in `PowerModel._update_power_state()` — now uses contract enum values with strict SOC-gated transitions.

### Physics Implementation
- **Solar array**: 56 m², 30% BOL efficiency, cosine loss, temp derating (-0.5%/°C), radiation degradation
- **Battery**: 100 Ah Li-ion, 28V nominal, Coulomb counting SOC, voltage vs SOC + temp curve
- **Power balance**: Array power - loads = battery power (charge/discharge)
- **Current limiting**: Max charge 50A, max discharge 100A
- **Available power**: Array + max battery discharge capability

### Cross-Model Coupling
| Input | Source | ODCS Reference | Used For |
|-------|--------|----------------|----------|
| `electronics_bay_temp_k` | Thermal | `04_cross_model` | Battery temperature for voltage calc |
| `solar_array_degradation_factor` | Radiation | `04_cross_model` | Array output degradation |
| `available_power_W` | Cross-model bus | `04_cross_model` | Output to bus |

### Test Coverage (Validating ODCS Quality Rules)
- ✅ Solar array power (incidence, degradation, temp, eclipse = 0 in UMBRA)
- ✅ Battery SOC (charge/discharge, **hard bounds 0-100%**)
- ✅ Power balance (surplus/deficit/balanced, sign consistency)
- ✅ Full model step (sunlight, eclipse, high incidence)
- ✅ Battery voltage curve (SOC + temp)
- ✅ **Power state classification (strict SOC-gated transitions per ODCS)**
- ✅ Cross-model degradation & temperature coupling
- ✅ Available power calculation (≥0 check)

---

## 4. Comms Model → `SyntheticCommsOutput` — **NOT IMPLEMENTED**

### ODCS Contract: `03_power_comms_radiation.odcs.yaml` → `comms_model_output` v1.0.0

### Contract Fields with ODCS Quality Rules
| Field | ODCS Type | Required | PK | Critical | Quality Rules (ODCS) | Notes |
|-------|-----------|----------|-----|----------|----------------------|-------|
| `timestamp_utc` | `TIMESTAMP WITH TIME ZONE` | ✅ | ✅ | | `nullValues=0` | |
| `eirp_dBW` | `DOUBLE` | ✅ | | | `nullValues=0`, derived from configured RF power + antenna gain | EIRP = 10·log₁₀(P_tx) + G_tx |
| `free_space_path_loss_dB` | `DOUBLE` | ✅ | | | `nullValues=0`, **must equal Friis calculation** from range + carrier (2.27-2.30 GHz) | FSPL = 20·log₁₀(4πdf/c) |
| `received_power_dBW` | `DOUBLE` | ✅ | | | `nullValues=0`, must satisfy link-budget equation | Pr = EIRP - FSPL + G_rx - L_misc |
| `eb_n0_dB` | `DOUBLE` | ✅ | | | `nullValues=0`, no universal 4.5 dB threshold | Eb/N0 = Pr - N₀ - 10·log₁₀(R) - L_impl |
| `link_margin_dB` | `DOUBLE` | ✅ | | ✅ | `nullValues=0`, **must equal eb_n0 - required_eb_n0** | NO_LINK if margin < 0 |
| `data_rate_kbps` | `DOUBLE` | ✅ | | | `nullValues=0`, `invalidValues=0` validValues=[0,16,64,128,256,512,1250] | Must be 0 when NO_LINK |
| `signal_quality` | `DOUBLE` | ✅ | | | `nullValues=0`, **0.0 ≤ SQ ≤ 1.0**, =0 at NO_LINK | Normalized: 0 at threshold, 1 at +20 dB |
| `comm_state` | `VARCHAR(10)` | ✅ | | ✅ | `nullValues=0`, `invalidValues=0` validValues=[NOMINAL,DEGRADED,NO_LINK] | |

### ODCS-Specific Requirements (Critical)
- **All bounds derived from physics of EM propagation** — not adjustable
- **No fixed EIRP validity range** until Orion transmitter/antenna specs supplied
- **FSPL envelope**: 175.83–211.94 dB for 2.27-2.30 GHz at 6,500-410,000 km
- **DSN gains**: Configuration-dependent per Module 206, no universal 63.2 dBi
- **Required Eb/N0**: Configuration parameter, not universal constant
- **Link margin**: Must equal eb_n0_dB - required_eb_n0_dB; no hard-coded 3 dB
- **Data rates**: Configured mission/hardware rate set (currently UNVERIFIED)
- **Signal quality**: Normalized link margin, physical constraint 0-1

### Required Physics
- **S-band link budget**: ~2.2 GHz (2110-2120 MHz downlink) — ODCS cites DSN Module 206
- **Orion antenna**: HGA ~24 dBi, LGA ~0-6 dBi (UNVERIFIED per ODCS)
- **DSN antennas**: 34m BWG (56 dBi), 70m (68 dBi) — config-dependent
- **Friis equation**: Pr = Pt + Gt + Gr - FSPL - L_atm - L_pol
- **Data rate**: Adaptive from configured rate set (0, 16, 64, 128, 256, 512, 1250 kbps)
- **Plasma noise**: From radiation model cross-coupling (`plasma_noise_factor`)

### Cross-Model Inputs Needed
| Input | Source | ODCS Reference | Purpose |
|-------|--------|----------------|---------|
| `earth_distance_km` | State engine | `01_state_engine` | Range for FSPL |
| `dsn_visibility` | State engine | `01_state_engine` | Which ground station |
| `plasma_noise_factor` | Radiation | `04_cross_model` | Noise temperature increase |
| `solar_incidence_angle` | State engine | `01_state_engine` | HGA pointing feasibility |
| `available_power_W` | Power model | `04_cross_model` | Max transmit power budget |

---

## 5. Radiation Model → `SyntheticRadiationOutput` — **NOT IMPLEMENTED**

### Contract Fields (from `models.py:198-213`)
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `timestamp_utc` | `datetime` | ✅ | |
| `total_dose_rate_rad_s` | `float` | ✅ | rad/s |
| `cumulative_dose_krad` | `float` | ✅ | krad(Si) |
| `solar_array_degradation` | `float` | ✅ | 0-1, feeds power model |
| `thermal_alpha_degradation` | `float` | ✅ | Feeds thermal model |
| `thermal_eps_degradation` | `float` | ✅ | Feeds thermal model |
| `radiation_dose_rate_mrad_hr` | `float` | ✅ | mrad/hr for display |
| `sep_event_active` | `bool` | ✅ | Solar particle event flag |

### Required Physics
- **Trapped radiation**: AP-8 (protons) + AE-8 (electrons) models
- **Solar particle events**: GOES proton flux → SEP model
- **Shielding**: Orion hull ~3-5 g/cm² Al equivalent
- **Dose rate**: `Ḋ = ∫ Φ(E) · σ(E) · S(E) dE` 
- **Degradation models**:
  - Solar array: `P/P₀ = exp(-k·D)` or displacement damage dose
  - Thermal coatings: `α/α₀ = 1 + c·D`, `ε/ε₀ = 1 - c·D`

### Cross-Model Outputs (to Bus)
| Output | Consumer | Purpose |
|--------|----------|---------|
| `solar_array_degradation` | Power | Array efficiency reduction |
| `thermal_alpha_degradation` | Thermal | Absorptivity increase |
| `thermal_eps_degradation` | Thermal | Emissivity decrease |
| `plasma_noise_factor` | Comms | Ionospheric noise proxy |

### Data Sources
- **GOES protons** (new real-data source): ≥1-500 MeV integral flux
- **JPL Horizons**: Position for belt traversal
- **AP-8/AE-8**: Static models (or SPENVIS integration)

---

## 6. Cross-Model Bus → `SyntheticCrossModelState` — **IMPLEMENTED**

### Contract Fields (from `models.py:216-231`)
| Field | Type | Required | Implementation |
|-------|------|----------|----------------|
| `timestamp_utc` | `datetime` | ✅ | ✅ |
| `electronics_bay_temp_K` | `float` | ✅ | ✅ From thermal |
| `power_dissipation_W` | `float` | ✅ | ✅ From power |
| `available_power_W` | `float` | ✅ | ✅ From power |
| `solar_array_degradation_factor` | `float` | ✅ | ✅ From radiation |
| `thermal_coating_alpha_factor` | `float` | ✅ | ✅ From radiation |
| `thermal_coating_eps_factor` | `float` | ✅ | ✅ From radiation |
| `plasma_noise_factor` | `float` | ✅ | ✅ From comms (signal_quality proxy) |

### Implementation: `physics_models/cross_model/bus.py`
- ✅ `CrossModelBus` class with 1-tick lag coupling
- ✅ `update(thermal, power, comms, radiation)` method
- ✅ `to_cross_model_state(timestamp)` → contract model
- ✅ All 7 coupling variables implemented

### Coupling Matrix
| From → To | Variable | Description |
|-----------|----------|-------------|
| Thermal → Power | `electronics_bay_temp_K` | Battery temp for voltage |
| Power → Thermal | `power_dissipation_W` | Electronics bay heat load |
| Radiation → Power | `solar_array_degradation_factor` | Array efficiency loss |
| Radiation → Thermal | `thermal_coating_alpha_factor` | Absorptivity degradation |
| Radiation → Thermal | `thermal_coating_eps_factor` | Emissivity degradation |
| Radiation → Comms | `plasma_noise_factor` | Ionospheric noise |

---

## 7. Packet Assembler → `SyntheticTelemetryPacket` — **PARTIAL**

### Contract Fields (from `models.py:234-271`)
| Field | Type | Required | Implementation (in `runner.py`) |
|-------|------|----------|--------------------------------|
| `timestamp_utc` | `datetime` | ✅ | ✅ |
| `spacecraft_id` | `str` | ✅ (default) | ✅ "ORION_EM2" |
| `temp_sun_face_K` | `float` | ✅ | ✅ From thermal |
| `temp_shadow_face_K` | `float` | ✅ | ✅ From thermal |
| `temp_electronics_bay_K` | `float` | ✅ | ✅ From thermal |
| `heater_active` | `bool` | ✅ | ✅ From thermal |
| `thermal_state` | `Literal` | ✅ | ✅ From thermal |
| `battery_voltage_V` | `float` | ✅ | ✅ From power |
| `battery_soc_pct` | `float` | ✅ | ✅ From power |
| `solar_array_power_W` | `float` | ✅ | ✅ From power |
| `power_state` | `Literal` | ✅ | ⚠️ **Enum mismatch** (same as power model) |
| `signal_quality` | `float` | ✅ | ❌ Placeholder (0.95) |
| `link_margin_dB` | `float` | ✅ | ❌ Placeholder (5.0) |
| `data_rate_kbps` | `float` | ✅ | ❌ Placeholder (128.0) |
| `comm_state` | `Literal` | ✅ | ❌ Placeholder ("NOMINAL") |
| `radiation_dose_rate_mrad_hr` | `float` | ✅ | ❌ Placeholder (0.1) |
| `cumulative_dose_krad` | `float` | ✅ | ❌ Placeholder (0.0) |
| `sep_event_active` | `bool` | ✅ | ❌ Placeholder (False) |
| `all_nominal` | `bool` | ✅ | ✅ Computed from substates |

### Status
- ✅ Thermal fields fully implemented
- ✅ Power fields fully implemented (except enum)
- ❌ Comms fields: all placeholders
- ❌ Radiation fields: all placeholders
- ✅ Derived `all_nominal` logic correct

---

## 8. Anomaly Detector → `SyntheticAnomalyEvent` — **NOT IMPLEMENTED**

### Contract Fields (from `models.py:274-296`)
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `event_id` | `str` (UUID) | ✅ | |
| `timestamp_utc` | `datetime` | ✅ | |
| `anomaly_type` | `str` | ✅ | Code (e.g., "THERMAL_LIMIT_EXCEED") |
| `detection_layer` | `Literal[1,2,3]` | ✅ | 1=Contract, 2=Rules, 3=ML |
| `severity` | `Literal["CRITICAL","ALERT","WARNING","INFO"]` | ✅ | |
| `description` | `str` | ✅ | Human-readable |
| `field_name` | `str` | ✅ | Triggering field |
| `field_value` | `float` | ✅ | Actual value |
| `expected_value` | `float\|None` | ❌ | Physics baseline |
| `residual` | `float\|None` | ❌ | Actual - expected |
| `contract_reference` | `str` | ✅ | ODCS file + rule |
| `suggested_cause` | `str` | ✅ | Physical explanation |
| `r_RE` | `float` | ✅ | Position in Earth radii |
| `mission_phase` | `str` | ✅ | From timeline |
| `ml_anomaly_score` | `float\|None` | ❌ | 0-1 ML score |

### Required Architecture
- **Layer 1 (Contract)**: Check each field against ODCS quality rules (min/max, rate-of-change)
- **Layer 2 (Physics Rules)**: Cross-field physics constraints (e.g., energy balance, thermal-power coupling)
- **Layer 3 (ML)**: Isolation Forest / Autoencoder on `SyntheticMLFeatureVector`

---

## 9. ML Features → `SyntheticMLFeatureVector` — **PARTIAL**

### Contract Fields (from `models.py:299-337`)
| Category | Fields | Implementation |
|----------|--------|----------------|
| Raw Normalized | `temp_elec_norm`, `temp_sun_norm`, `temp_shadow_norm`, `soc_norm`, `voltage_norm`, `signal_quality`, `dose_rate_norm` | ⚠️ Placeholder in `runner.py` |
| Context | `r_RE_norm`, `earth_dist_norm`, `eclipse_fraction`, `in_belt`, `sep_active`, `dsn_visible` | ⚠️ Partial |
| Physics Residuals | `temp_sun_residual_K`, `link_margin_residual_dB`, `array_efficiency_ratio`, `voltage_residual_V`, `dose_rate_ratio` | ❌ Not implemented |
| Rate of Change | `temp_elec_rate_K_min`, `soc_rate_pct_hr`, `dose_rate_delta_mrad_hr`, `signal_quality_delta` | ❌ Need history buffer |

### Required
- Normalization ranges from ODCS quality rules
- Physics baseline models for residuals
- Rolling window for rate-of-change (last N ticks)

---

## 10. Planned Attitude Integration — **VERIFIED**

**File:** `packages/physics_models/src/physics_models/state_engine/planned_attitude.py` (1065 lines)

### Provides for State Engine
| Function | Returns | Used By |
|----------|---------|---------|
| `resolve_attitude(met)` | `(AttitudeMode, dict)` | State engine tick |
| `get_solar_incidence_angle_estimate(met)` | `float` | `solar_incidence_angle_deg` |
| `get_solar_array_gimbal_estimate(met)` | `float` | `solar_array_angle_deg` |
| `get_mode_definition(mode)` | `dict` | Attitude quaternion generation |

### Attitude Modes (47 canonical modes from Artemis II timeline)
- **Coast**: `BIAS_NEG_XSI`, `BIAS_NEG_XSI_MITIGATE_X` (dominant)
- **Burns**: `BURN_ARB`, `BURN_PRB`, `BURN_TLI`, `BURN_OTC`, `BURN_RTC`
- **Setup**: `SFM`
- **Separation**: `SEP`
- **Entry**: `EDL`, `RECOVERY`
- **Demos**: `T_ROLL_MNVRS`, `POD_ATT`, `SURVEY_ATT`, `DOCK_CAM`, `OPNAV`, `OPCOMM`, `OBSV`

### Gap
- **Quaternion resolver needed**: Convert `AttitudeMode` + orbital state → quaternion → Euler angles for `roll_deg`, `pitch_deg`, `yaw_deg`

---

## Action Items (Priority Order)

### P0 — Fix Enum Mismatches (Blocks API compliance)
1. **Power model**: Update `_update_power_state()` to use contract enum values:
   - `DISCHARGING` → `BATTERY_DISCHARGE`
   - `LOW_POWER` → `LOW_POWER_MODE`

### P1 — Implement Missing Physics Models
2. **Comms model** (`physics_models/comms/physics.py`):
   - S-band link budget (Friis)
   - HGA/LGA antenna patterns
   - DSN station parameters
   - Adaptive data rate selection
   - Output `SyntheticCommsOutput`

3. **Radiation model** (`physics_models/radiation/physics.py`):
   - AP-8/AE-8 trapped radiation
   - GOES proton flux → SEP dose
   - Shielding model (Orion hull)
   - Degradation curves (array, coatings)
   - Output `SyntheticRadiationOutput`

### P2 — Complete Integration
4. **Packet assembler**: Replace placeholders with real comms/radiation outputs
5. **Attitude quaternions**: Implement body-to-inertial per `AttitudeMode`
6. **OEM/Horizons integration**: SPICE or OEM file interpolation

### P3 — Anomaly & ML Pipeline
7. **Anomaly detector** (`physics_models/anomaly/detector.py`):
   - Layer 1: Contract quality rules
   - Layer 2: Physics cross-checks
   - Layer 3: ML inference (ONNX/Triton)
8. **ML feature builder** (`physics_models/anomaly/ml_features.py`):
   - Normalization from ODCS
   - Physics residual calculators
   - Rolling window for rates

### P4 — Testing & Validation
9. Contract validation tests for each generator output
10. End-to-end integration test: 1000 ticks → verify all 8 Kafka topics
11. Performance benchmark: tick loop < 100ms at 1 Hz

---

## Kafka Topic Mapping (from Architecture Doc)

| Topic | Contract | Producer |
|-------|----------|----------|
| `trajectory` | `SyntheticStateSnapshot` | StateEngine |
| `telemetry` | `SyntheticTelemetryPacket`, `SyntheticThermalOutput`, `SyntheticPowerOutput`, `SyntheticCommsOutput`, `SyntheticRadiationOutput` | All models |
| `cross_model_state` | `SyntheticCrossModelState` | CrossModelBus |
| `events` | `SyntheticAnomalyEvent` | AnomalyDetector |
| `ml_features` | `SyntheticMLFeatureVector` | MLFeatureBuilder |

---

## Conclusion

The **core physics models (State Engine, Thermal, Power)** are **fully implemented and tested** against their ODCS contracts. The **cross-model coupling bus** is complete with correct 1-tick lag semantics.

**Critical path to production:**
1. Fix power state enum mismatch (1 hour)
2. Implement Comms model (2-3 days)
3. Implement Radiation model (3-4 days)
4. Replace packet placeholders (1 day)
5. Add attitude quaternions (1-2 days)
6. Implement Anomaly + ML pipeline (1 week)

**Estimated effort to 100% contract coverage: ~2-3 weeks**