# GOES SGPS → provisional ≥10 MeV proton flux

## Scope

This is a **physics transform**, not a datasource and not an ODCS contract.

The source is the existing `goes_sgps_flux_avg5m` ingest. Processing remains
restricted to the Artemis II flight interval:

`2026-04-01T22:35:12Z` through `2026-04-11T00:07:27Z`.

## Critical units rule

The existing SGPS table stores differential flux as:

`protons/(cm^2 sr keV s)`

The mathematical fit/integration requires:

`protons/(cm^2 sr MeV s)`

Therefore the adapter must explicitly declare the input units. Per-keV input
is multiplied by 1000 exactly once.

The transform rejects unknown units rather than guessing.

## Table-to-transform adapter

`channels_from_table_rows()` is deliberately the only layer that knows the
table representation:

- `channel_index` → SGPS channel name;
- `energy_lower_mev` / `energy_upper_mev` → source-file calibration bounds;
- differential flux unit conversion;
- `valid_sample_count` and `dqf_sum` quality masking;
- >500 MeV integral extraction.

The mathematical function `derive_ge10_pfu()` receives already normalized,
typed channels and therefore cannot silently reinterpret database units.

**Important:** the final repository adapter must bind the `idx=13` >500 MeV
case to the actual column/index used by the existing DDL. If the committed
table uses a named integral channel rather than index 13, make that mapping in
`channels_from_table_rows()` only. Do not weaken the core function.

## Energy bounds

The source row's energy bounds are authoritative for that observation. The
transform no longer hard-codes the legacy calibration bounds.

P4 crosses the 10 MeV threshold and is therefore handled by the fitted
spectrum. It is not counted as a complete ≥10 MeV channel.

## Quality

Rows with `valid_sample_count <= 0` or non-zero `dqf_sum` are excluded by the
default adapter.

This policy should be reconciled with the exact NOAA DQF semantics before
production use; the transform does not infer that every non-zero DQF is
scientifically unusable without that repository-level policy.

## Zero differential channels

Zero values are excluded from a log-log fit because `log(0)` is undefined.

They are counted in `zero_channel_count`. No arbitrary floor is substituted.

A production method may model zero values as upper limits, but that requires an
explicit statistical method and uncertainty treatment. It must not be hidden
inside this transform.

## Missing / invalid >500 MeV

The >500 MeV integral is required. Missing, NaN, infinite, or negative values
cause a hard failure.

The previous behavior of replacing a missing value with zero is intentionally
removed because it can understate the target flux materially.

## Lower-bound invariant

For every result:

`derived >= direct_measured_subset`

where the direct subset is:

- all measured differential bands wholly above 10 MeV, integrated across
  their source-file energy widths; plus
- the measured >500 MeV integral.

This does not prove the fitted spectrum is correct. It prevents the estimator
from violating an obvious monotonicity constraint of the target quantity.

## Uncertainty

The log-fit RMS is retained only as a rough dispersion indicator when at least
three positive fit channels are available.

For two-channel fits, `uncertainty_pfu = None`.

This value is **not** a complete SGPS measurement uncertainty and must not be
interpreted as one.

A production uncertainty budget should separately consider calibration,
geometric-factor, energy-bound, background, spectral-model, DQF and
GOES-to-Orion proxy uncertainties.

## Sensor units

Do not average +X and -X in the transform. Preserve one result per sensor
unit. Any selection or conservative combination belongs to the radiation
model/input policy and must be explicit.

## Contract boundary

No new contract is introduced.

The continuous derived flux can remain an internal physics-model input if the
existing contracts expose only the thresholded `sep_event_active` state.

Contract 03 currently exposes the SEP event boolean rather than a defined
`SpaceWeatherSnapshot` schema. Therefore this implementation does **not** claim
that continuous flux is already contract-protected.

If a future existing-model integration requires the continuous value to cross
an ODCS boundary and the existing contract cannot represent it, stop and report
that incompatibility. Do not silently create or edit a contract.

## Validation gates

1. Existing GOES fixture/unit tests.
2. New transform unit tests:
   - explicit units conversion;
   - invalid units;
   - NaN/Inf/negative rejection;
   - mandatory >500 MeV;
   - source energy bounds;
   - DQF filtering;
   - P4 threshold handling;
   - lower-bound invariant;
   - zero-channel accounting;
   - two-channel uncertainty behavior.
3. Live archive integration test, using the repository's actual pytest path
   and `uv run --package pipelines ...` invocation.
4. Flight-window replay from liftoff through splashdown.
5. NOAA operational ≥10 MeV comparison (Gate C). Reference data: the
   `goes_integral_protons` table (`p10_pfu`), ingested by
   `pipelines.ingest.iswa_goes_protons`.
6. DONKI SEP correlation.
7. GOES-to-Orion proxy limitations documented before any Orion-local dose
   interpretation.

## Repository commands

Use the repository's package-aware uv invocation, for example:

```bash
uv run --package pipelines pytest \
  tests/unit/pipelines/transforms/sgps_proton_flux/test_sgps_proton_flux.py
```

Run the complete suite with the repository's established command after the
new files are copied into the workspace.

Do not claim the fixture's 8,064 rows are evidence that the live archive test
covered the same volume. The live test and fixture test are separate gates.

## No new dependency

The transform uses only the Python standard library. `netCDF4` remains a
dependency of the `pipelines` package because the existing GOES archive ingest
needs it; this transform does not broaden dependency scope.
