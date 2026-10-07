# Physics Transforms

This package contains physics-derived transforms that operate on existing ingested data.

## GOES SGPS Proton Flux Transform

`sgps_proton_flux.py` derives a provisional ≥10 MeV integral proton flux (PFU) from GOES Space Environment Monitor (SEM) Solar and Galactic Proton Sensor (SGPS) differential flux channels.

### Key Characteristics

- **Not a data source** — operates on existing `goes_sgps_flux_avg5m` table
- **Not an ODCS contract** — produces internal physics-model input
- **Standard library only** — no new dependencies
- **Explicit units** — requires declared input units (per-keV → per-MeV conversion ×1000)
- **Fails closed** — non-finite, negative, or missing required channels raise `SgpsDerivationError`

### Usage

```python
from pipelines.transforms import (
    derive_ge10_pfu,
    channels_from_table_rows,
    SgpsChannel,
    DIFFERENTIAL_PER_KEV,
)

# 1. Fetch rows from goes_sgps_flux_avg5m for one sensor/time group
rows = fetch_sgps_rows(sensor="EPEAD", time_bucket="2026-04-01T12:00:00Z")

# 2. Convert table rows to typed channels (adapter knows table schema)
channels, gt500 = channels_from_table_rows(
    rows,
    differential_units=DIFFERENTIAL_PER_KEV,  # table stores per-keV
    mask_quality=True,
)

# 3. Derive ≥10 MeV integral flux
result = derive_ge10_pfu(channels, gt500)

print(f"≥10 MeV flux: {result.flux_ge10_pfu:.2f} PFU")
print(f"Method: {result.method}, Status: {result.status}")
print(f"Fit channels: {result.fit_channel_names}")
print(f"Lower bound (direct): {result.direct_lower_bound_pfu:.2f} PFU")
```

### Validation Gates (from integration docs)

1. Existing GOES fixture/unit tests
2. New transform unit tests (units, bounds, DQF, P4 threshold, lower-bound invariant, etc.)
3. Live archive integration test
4. Flight-window replay (liftoff through splashdown)
5. NOAA operational ≥10 MeV comparison
6. DONKI SEP correlation
7. GOES-to-Orion proxy limitations documented

### Channel Convention

The transform uses the repository's channel-index convention established by the GOES ingest:

| Index | Channel | Notes |
|-------|---------|-------|
| 0–12 | P1–P11 | 13 differential channels |
| 13 | >500 MeV | Integral channel (already in PFU) |

P4 (index 3) crosses the 10 MeV threshold and is handled by the fitted spectrum — **not** counted as a complete ≥10 MeV channel.

### Quality Masking

By default, `channels_from_table_rows()` excludes rows where:
- `valid_sample_count <= 0`
- `dqf_sum != 0`

This policy should be reconciled with NOAA DQF semantics before production use.