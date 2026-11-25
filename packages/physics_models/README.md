# physics_models

The **synthetic data** path: a simulator that replays the Artemis II flight at 1 tick per
second, computes Orion's state, thermal, power, comms and radiation telemetry, and publishes
it to Kafka (Redpanda). A consumer writes it to TimescaleDB. How the models work:
[`docs/architecture/PHYSICS_MODELS.md`](../../docs/architecture/PHYSICS_MODELS.md).

## Run

Both run in Docker, next to Redpanda (they reach it as `redpanda:9092`):

```bash
docker compose up -d --build physics_models physics_models_consumer

# Watch Orion move: start at the OEM arc (MET 12300 s), 60 simulated seconds per tick
PHYSICS_MODELS_START_MET_SECONDS=12300 PHYSICS_MODELS_TIME_SCALE=60 \
  docker compose up -d --force-recreate physics_models

docker compose logs -f physics_models_consumer     # "Inserted ..." per message
```

| Variable | Default | Meaning |
|----------|---------|---------|
| `PHYSICS_MODELS_TIME_SCALE` | 1.0 | Simulated seconds per tick |
| `PHYSICS_MODELS_START_MET_SECONDS` | 0 | Mission elapsed time to start from |
| `PHYSICS_MODELS_LOOP` | 0 | `1`: restart at the end of the OEM arc |
| `PHYSICS_MODELS_CONFIG` | set by the image | Config file (`configs/docker.yaml` in the image) |

The consumer needs `DATABASE_URL` and `KAFKA_BOOTSTRAP_SERVERS`; compose sets both. More
replay examples: [`RUN_SERVICES.md`](../../RUN_SERVICES.md), "Demo Replay Controls".

## Layout

| Path | Holds |
|------|-------|
| `src/physics_models/runner.py` | `SimulatorRunner`: the tick loop |
| `src/physics_models/oem.py` | NASA OEM reader and interpolation |
| `src/physics_models/state_engine/` | Solar flux and eclipse, DSN visibility (`dsn.py`), Moon position (`moon.py` + bundled `moon_ephemeris.csv`) |
| `src/physics_models/thermal/`, `power/`, `comms/`, `radiation/` | The four subsystem models |
| `src/physics_models/cross_model/bus.py` | One-tick-lag coupling between the models |
| `src/physics_models/packet/` | Telemetry packet assembly and whole-tick validation |
| `src/physics_models/kafka/producer.py` | Kafka producer |
| `consumer.py` | Kafka -> TimescaleDB consumer (package root, its own image) |
| `configs/default.yaml`, `configs/docker.yaml` | Model parameters, Kafka address, OEM source, liftoff time |
| `Dockerfile`, `Dockerfile.consumer` | The two images (built from the repo root) |

Anomaly detection and ML features are placeholders: the runner emits fixed values.

## Tests

```bash
uv run pytest tests/unit/physics_models
```

`radiation/test_calibration.py` checks the dose calibration on the real OEM trajectory
(`data/oem/`).
