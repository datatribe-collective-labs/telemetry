# Physics models

How `packages/physics_models/` simulates Orion's telemetry (the **synthetic data**): the
tick loop, the five models, how they are coupled, and how each tick is checked and
published. Where it sits in the whole system: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
Field-by-field contract status: [`CONTRACT_COMPLIANCE.md`](../integration/CONTRACT_COMPLIANCE.md).

## The tick loop

`physics_models.runner.SimulatorRunner` runs one tick per wall-clock second (`tick_hz: 1.0`).
Each tick (`_run_tick`):

1. **Clock.** Simulated time is `liftoff + start_met_seconds + ticks x time_scale`, so
   the replay can start mid-mission and run faster than real time.
2. **State engine.** Interpolates Orion's position and velocity from the NASA OEM arc, then
   computes Sun distance, solar flux, eclipse, DSN visibility and light time.
3. **Models.** Thermal, power, comms and radiation each compute their output for the tick.
   They read each other's results from the **previous** tick only (see Coupling).
4. **Packet.** `packet.assemble_packet` combines the outputs into one telemetry packet.
   A placeholder ML feature vector is built next to it.
5. **Validation.** `packet.validate_tick` checks every output against the contract rules.
   If anything fails, the tick publishes nothing and does not update the coupling bus.
   The clock still moves on, and the models' internal state is not rolled back.
6. **Coupling bus.** The valid outputs are stored for the next tick.
7. **Kafka.** Everything is published (see Publishing).

With `loop` on, the first tick past the end of the OEM arc (atmospheric entry) starts the
replay over from `start_met_seconds` with fresh models. The ticks fall on the same
timestamps as before, so the consumer overwrites the previous loop's rows instead of adding
new ones.

If the OEM file cannot be loaded, the state engine falls back to a 300 km circular
placeholder orbit and prints a warning.

## The models

| Model | Code | What it computes | Main inputs |
|-------|------|------------------|-------------|
| State engine | `oem.py`, `state_engine/` | Position and velocity (EME2000, km), solar flux, eclipse (`SUNLIT`/`PENUMBRA`/`UMBRA`), DSN visibility, light time, solar angles | NASA OEM arc, planned attitude timeline |
| Thermal | `thermal/physics.py` (`ThermalModel3Node`) | Temperatures of three nodes (sun face, shadow face, electronics bay), heat flows, survival heater, `thermal_state` | Solar flux, incidence, eclipse; electrical load from power |
| Power | `power/physics.py` (`PowerModel`) | Solar array power, battery charge, voltage and current, net and available power, `power_state` | Solar flux, array angle, eclipse; bay temperature from thermal; heater load |
| Comms | `comms/physics.py` (`CommsModel`) | S-band downlink budget (EIRP, path loss, Eb/N0, margin), data rate, `comm_state`, `link_loss_reason` | Earth distance, DSN view; power state from power |
| Radiation | `radiation/physics.py` (`DoseProfile`) | Dose rate and cumulative dose at one cabin sensor, split into radiation belts and cosmic rays; `radiation_zone` | Orion's distance from Earth along the OEM arc |

### State engine

- **Trajectory.** `oem.py` reads the newest arc from `data/oem/all-artemis-ii-oem-files.zip`
  (CCSDS OEM v2.0, Earth-centred EME2000, UTC). Orion's position is interpolated
  linearly between points. Orion does not move before the arc starts, on April 2 around
  02:00 UTC (MET about 12,300 s), so the server demo starts there.
- **Sun.** A circular orbit at 1 AU, accurate enough for solar flux (about ±1 %) and
  eclipse geometry.
- **Moon.** `state_engine/moon.py` interpolates a JPL Horizons table bundled with the
  package (`moon_ephemeris.csv`, 10-minute steps).
- **DSN visibility.** `state_engine/dsn.py` places the three DSN antennas used
  (DSS-14 Goldstone, DSS-43 Canberra, DSS-63 Madrid) on the rotating Earth. Orion is
  visible from a site above 10° elevation, unless the Moon is in the line of sight.
  When no site can see Orion, it names the cause: `MOON_BLOCKED` or `OUT_OF_VIEW`.
- **Attitude.** Solar incidence and solar array angles are rough estimates from the planned
  attitude mode at that moment (`contracts.planned_attitude`). Roll, pitch and yaw are
  published as 0, because Orion's real attitude is not public.

### Thermal

A three-node lumped model. Each node has a heat capacity, area and surface properties,
and conducts heat to the other nodes and radiates it to space. Node parameters come from
the config (`thermal:` in `configs/*.yaml`). A survival heater with hysteresis switches on
below the contract's −5 °C setpoint. A share of the electrical load (`bay_heat_fraction`,
30 %) heats the electronics bay. `thermal_state` follows contract 02: `COLD_SURVIVAL` below
249 K in the bay (or below 100 K on a face), `HOT_LIMIT` above 310 K in the bay (or 450 K
on the sun face).

### Power

Solar arrays (44.8 m², 28 % efficiency at beginning of life, temperature derated) charge a
100 Ah, 28 V Li-ion battery. The load is a fixed 1,200 W placeholder, plus the heater when
it is on: Orion's real load profile is not published. Available power is
`array power x 0.92 − 800 W`, and net power is `array power x 0.92 − load` before battery
current limiting (contract 03). Battery current uses the reported post-update voltage and
is clamped to the model's charge/discharge limits. `power_state` is set from the battery charge:
`CRITICAL` at or below 10 %, `LOW_POWER_MODE` up to 20 %, `BATTERY_DISCHARGE` while the
battery drains, otherwise `NOMINAL`.

### Comms

An S-band downlink budget from Orion to a DSN 34 m antenna, recomputed every tick (the
model keeps no state). The 2216.5 MHz carrier, the 1939.4 kbps top rate and the DSN receiver
figures come from published sources. Orion's transmit power and antenna gain are not
published, so their product (EIRP) is calibrated so that the top rate still works at
410,000 km. The model picks the highest data rate that keeps a 3 dB operating margin
(`NOMINAL`). If none does, it uses the lowest rate while the margin is still positive
(`DEGRADED`). Otherwise the state is `NO_LINK`, with one `link_loss_reason`:

- `MOON_BLOCKED` or `OUT_OF_DSN_VIEW` if no antenna can see Orion (geometry wins),
- `NO_POWER` if the transmitter was off because the previous power tick was `CRITICAL`,
- `LINK_BUDGET` if the signal is simply too weak.

### Radiation

A simplified dose in water at one cabin sensor (HERA HSU2), not the crew's actual dose:

- **Radiation belts:** two Gaussian shells by distance from Earth, calibrated against the
  Artemis I measurements (Nature 634, 48-52, 2024). `tests/unit/physics_models/radiation/test_calibration.py`
  checks the calibration on the real trajectory.
- **Galactic cosmic rays:** the measured deep-space rate, reduced by the part of the sky
  that Earth and the Moon block.

The dose is computed once for the whole OEM arc on a 10 s grid (`DoseProfile`), so it
depends only on the timestamp, not on the replay speed, and the cumulative dose never
goes down. `sep_event_active` is false: the real GOES proton flux during the mission stayed
below the 10 pfu storm threshold. The radiation degradation factors are not modelled and
stay 1.0.

## Coupling

`cross_model.CrossModelBus` passes values between models with a **one-tick lag**: a model at
tick N reads what the others produced at tick N−1. This avoids circular dependencies
inside a tick.

| From -> to | Value | Effect |
|------------|-------|--------|
| Thermal -> power | Electronics bay temperature | Used as a stand-in for the array and battery temperatures: solar array derating, battery charge and voltage |
| Power -> thermal | Total electrical load | 30 % of it heats the electronics bay |
| Power -> comms | `power_state` | `CRITICAL` switches the transmitter off |
| Radiation -> power | Solar array degradation | Always 1.0 (not modelled) |
| Radiation -> thermal | Coating α / ε degradation | Published on the bus, always 1.0, not read by the thermal model |
| Radiation -> comms | Plasma noise factor | Always 1.0 (not modelled) |

In the same tick, the heater's power is added to the power model's load.

The bus state is published on the `cross_model_state` topic every tick.

## Validation

`packet/validation.py` runs before anything leaves the simulator. Among other checks:

- all timestamps in the tick match and every number is finite,
- eclipse fraction is within [0, 1], temperatures are above 0 K, and battery charge is within [0, 100] %,
- solar array power is 0 in `UMBRA`, and `power_state` matches the battery charge,
- `comm_state`, data rate, signal quality and `link_loss_reason` agree, and there is no
  link while no antenna has a clear view,
- the total dose rate equals belt plus cosmic rays, and the unit conversions agree,
- the packet's `all_nominal` matches the subsystem states.

The tests are in `tests/unit/physics_models/packet/`.

## Publishing

`kafka/producer.py` uses `confluent_kafka` (`acks=all`, zstd compression, small batches).
Each message is keyed by its `timestamp_utc`. Each tick sends:

| Topic | Messages |
|-------|----------|
| `trajectory` | state snapshot |
| `telemetry` | thermal, power, comms, radiation, packet |
| `cross_model_state` | coupling bus state |
| `ml_features` | ML feature vector (**placeholder**: fixed values) |
| `events` | anomaly events: the detector is a **placeholder** that never fires, so nothing is sent |

`consumer.py` (package root, its own container) subscribes to all five topics, tells the
message types on `telemetry` apart by a field only that type has, and upserts each row on
`timestamp_utc` into its TimescaleDB table.

## Configuration

`configs/default.yaml` (native runs) and `configs/docker.yaml` (the image, chosen with
`PHYSICS_MODELS_CONFIG`) hold the Kafka address, OEM source, liftoff time
(2026-04-01 22:35 UTC) and model parameters. Three environment variables override the
replay settings:

| Variable | Default | Meaning |
|----------|---------|---------|
| `PHYSICS_MODELS_TIME_SCALE` | 1.0 | Simulated seconds per tick |
| `PHYSICS_MODELS_START_MET_SECONDS` | 0 | Mission elapsed time to start from |
| `PHYSICS_MODELS_LOOP` | 0 | `1`: restart at the end of the OEM arc |

The public server runs `12300` / `60` / `1` (`docker-compose.prod.yml`): from the start of
the OEM arc, one simulated minute per second, looping.

## Docker images

Both images are built from the repo root so `uv` can resolve the workspace:

- `Dockerfile`: the simulator, with the OEM zip copied to `/app/oem/`.
- `Dockerfile.consumer`: the Kafka -> TimescaleDB consumer.

Both run as a non-root user.

## Not built

- **Anomaly detection** (contract 05): `_check_anomaly` returns nothing, so no events are
  published.
- **ML features** (contract 05): `_build_ml_features` fills fixed values.
- **Real attitude**: roll, pitch and yaw are 0, and solar angles are estimates from the
  planned attitude mode.
- **Radiation effects on other models**: degradation and plasma noise stay 1.0.
