# data/oem — NASA OEM ephemeris arcs (source data)

`all-artemis-ii-oem-files.zip` — 10 NASA/JSC planning arcs for Artemis II (EM-2)
as published in April 2026. 9 arcs are CCSDS OEM v2.0 (Earth-centered EME2000, UTC,
km/km/s); 1 arc ("2026.04.10 - Post-RTC3 to EI") is a legacy PROP_MAN entry arc in
FT/FPS units and is skipped by the ingests (see `packages/pipelines/.../nasa_oem.py`).

Consumers:
- `physics_models` state engine interpolates these arcs at runtime (`physics_models/oem.py`)
- `pipelines.ingest.nasa_oem` loads them into the `oem_state_vectors` TimescaleDB hypertable

