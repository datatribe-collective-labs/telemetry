# Physics Audit: ODCS Contracts & Owned Physics Models

**Date:** 2026-10-19 (wiring fixes applied same day — see banner below)
**Scope:** Contracts `01_state_engine`, `02_thermal_model`, `03_power` (the power section of
`03_power_comms_radiation`) and their implementations in
`packages/physics_models/src/physics_models/{state_engine,thermal,power}` + `runner.py`.
Comms/radiation contracts reviewed only superficially (owned by others).

> **✅ UPDATE 2026-10-19:** the §3 runtime-wiring findings were acted on. `runner.py` now
> wires `StateEnginePhysics` (interpolating NASA OEM arcs from `data/oem/`, also ingested
> into `oem_state_vectors` by `pipelines.ingest.nasa_oem`), `ThermalModel3Node`, and
> `PowerModel`; `power_state` (SOC-gated), `thermal_state` (249/310 K + surface bounds),
> heater setpoint (268.15 K), and array constants (44.8 m², 0.28 BOL) were corrected to the
> contracts. Live verification: Kafka/DB rows now vary with the real Artemis II arc
> (thermal nodes drifting, array ≤ 16.5 kW < 17.1 kW ceiling). The extracted timeline is
> ingested into `mission_events` by `pipelines.ingest.mission_events` (**DRAFT — not yet
> fact-checked against the PDF**). Backend gained `/oem`, `/oem/arcs`, `/mission-events`.
> Sections below remain as the audit record of what was found.
>
> **✅ UPDATE 2026-10-20:** the §2.2 "Integrator caveat" graduated to a confirmed bug and
> was fixed: conduction between nodes was never added to the heat-flow vector (K acted only
> as damping — the shadow node received no heat and cold-soaked to ~60 K, dragging the bay
> to COLD_SURVIVAL, dashboard caught it). The step now applies conductive exchange and
> auto-subcycles at ≤10 s per substep (time-scale-safe). Thermal defaults retuned to a
> physically sane bay (A 0.2 m², K 0.2–0.3 W/K, internal heat fraction 0.30 ≈ 363 W —
> MODEL_ASSUMPTION): equilibrium ≈ 296 K NOMINAL, verified dt-independent and live.

---

## 0. Executive Summary

| Area | Verdict |
|------|---------|
| Contract 01 (state) physics bounds | ✅ Sound — all numeric bounds reproduce from first principles |
| Contract 02 (thermal) physics bounds | ✅ Sound, minor internal inconsistencies |
| Contract 03 (power) physics bounds | ✅ Sound — battery/SOC rules are physics-correct |
| Runtime wiring of owned models | ❌ **Broken** — runner emits constants; models never execute |
| Impl vs contract in owned models | ⚠️ Two contract violations in unwired code paths |
| Live data in DB | ❌ Constant placeholder values (verified, see §4) |

**Headline finding:** `runner.py` `_tick_state_engine/_tick_thermal/_tick_power` return
hardcoded constants. The well-tested `StateEnginePhysics`, `ThermalModel3Node`, and
`PowerModel` classes are **never instantiated at runtime**. All "verified rows" in the DB
are identical constants — the pipeline works, the physics doesn't run.

---

## 1. Contract correctness (physics sense)

### 1.1 `01_state_engine` — ✅ correct

- **Solar flux range 1347–1375 W/m²** — reproduces exactly: 1361/1.005² = 1347.5,
  1361/0.995² = 1374.7. Solar constant 1361 W/m² = IAU 2015. ✅
- **Light time 0.02–1.38 s** — 410,000 km → 1.368 s ≈ 1.38 s. ✅
- **Speed ceiling 12 km/s** vs Artemis II entry ~11 km/s — sane. ✅
- **Position bound (410,000 km)²** vs max distance 406,773–413,144 km — consistent. ✅
- **Solar incidence [0,180]°, eclipse_fraction/state consistency rules** — correct and
  well stated. ✅

Minor issues:
1. **Self-contradiction:** `limitations` says *"cylindrical shadow model (no penumbra)"*
   but the `eclipse_state` enum includes `PENUMBRA` and `eclipse_fraction` says
   intermediate values occur only in PENUMBRA. Decide: either the model implements
   penumbra (code does — see §3) and the limitation text is stale, or remove PENUMBRA.
2. **Stale mixed-case field name:** `solar_flux_w_m2` quality text still references
   "`solar_flux_W_m2`" (post-normalization leftover).

### 1.2 `02_thermal_model` — ✅ mostly correct physics

- 3 K deep-space sink, Stefan–Boltzmann balance, eclipse zero-solar rule, hysteresis
  rule — all correct. ✅
- Stated equilibrium ~390–420 K at 1 AU with α=0.92 (ε-dependent) — plausible for a
  high-absorptivity exterior panel. ✅
- `temp_shadow_face_k` conduction-capacity constraint references conductance ≈ 0.2 W/K —
  matches nothing else in repo; keep as reference assumption. OK.

Minor issues:
1. **Stale mixed-case in text:** `temp_sun_face_K`, `temp_shadow_face_K`, and the SLS
   249–310 K discussion retained pre-normalization casing.
2. **Heater setpoint confusion:** `limitations` states "Heater setpoint is −5°C (268 K)",
   `heater_active` calls 268 K a MODEL_ASSUMPTION — but the implementation default is
   **283.15 K (10 °C)** (`ThermalModel3Node.heater_setpoint_k`). Pick one value and
   align config + contract + code.
3. `q_radiated_w` requiring ≥ 0 conflicts with reality only if a node ever gets colder
   than T_env — modeled env is 3 K, nodes clamped to ≥ 3 K, so fine.

### 1.3 `03_power_model_output` — ✅ correct

- SOC ∈ [0,100], "fix the model, not the contract" language — right. ✅
- Battery current sign convention, magnitude formula `|I| = |net_W| / V` — correct. ✅
- `power_state` strictly SOC-gated — good contract design. ✅
- Max array bound 17,100 W (1361 × 44.8 m² × 0.28) — internally consistent, though see
  §3.4 (implementation uses 56 m² / 0.30 / temp-derate floor 0.5 giving ≥ 11,432 W cap;
  the *source* figure is "4 wings, 11.2 kW" — the 44.8 m² is itself flagged UNVERIFIED
  in the contract, good).

Minor issues:
1. Contract text uses mixed-case names `solar_array_power_W`, `total_load_W`,
   `battery_current_A` inside quality descriptions (normalization leftovers).
2. `available_power_w` "800 W floor" and "15,000 W" bound use constants that are
   elsewhere flagged UNVERIFIED — fine since phrased as derived, but the 15,000 W number
   depends on the 44.8 m² assumption.

---

## 2. Owned implementations vs contracts (static review)

### 2.1 `StateEnginePhysics` (state_engine/physics.py)

- Kepler solver, Keplerian→ECI rotation, universal-variable two-body propagation,
  Stumpff functions — **standard and correct** formulations. ✅
- `compute_eclipse_state` uses a **conical** model with penumbra (angular-radius test +
  linear penumbra interpolation) — physically better than the contract's stated
  cylindrical model; reconciles point 1.1.1 above. ✅ physics / ⚠️ doc mismatch.
- `compute_solar_flux` = S₀/r². ✅
- `compute_light_time` = d/c. ✅
- `compute_dsn_visibility`: elevation = arcsin(site_up·LOS) — correct for static sites
  (no Earth rotation, simplified). OK for placeholder, must use real ECEF→ECI rotation
  when wired to real DSN geometry. ⚠️
- `compute_state_at_met` is an explicit placeholder (300 km circular equatorial orbit;
  Sun on circular 1 AU orbit). Fine *once wired*, but produces earth_distance ~6,678 km
  with light_time 0.022 s — unlike the constants in `runner.py`. ⚠️ runner bypasses it.

### 2.2 `ThermalModel3Node` (thermal/physics.py)

- Lumped-capacitance formulation with conductance matrix — correct structure. ✅
- Radiative/conductive helper functions correct (SB law, two-gray-surface exchange,
  Fourier's law). ✅
- **Contract violation:** `thermal_state()` thresholds (T_elec < 273.15 → COLD_SURVIVAL,
  > 323.15 → HOT_LIMIT) do **not** match contract (COLD_SURVIVAL < 249 K bay or
  surface < 100 K; HOT_LIMIT > 310 K bay or sun-face > 450 K, incl. surface conditions).
  Must be fixed when wired into the runner.
- **Heater setpoint mismatch:** default 283.15 K vs contract's 268 K (−5 °C). Align.
- **Integrator caveat:** the solve `(C/dt + H)·dT = Q_net` with `H` containing the
  linearized radiative conductance omits the `C/dt·T_old` term a strict backward-Euler
  would include. The fixed point (steady state energy balance) is correct, but
  transient time constants are off; acceptable for a demo model, document as such.
- Node clamping to [3, 500] K consistent with contract (3 K floor; 450 K "fail"
  threshold vs 500 hard clamp — contract asserts no hard 450 K bound, so OK).

### 2.3 `PowerModel` (power/physics.py)

- Cosine loss, temperature derating (−0.5 %/°C above 25 °C, floor 0.5), Coulomb
  counting, I = P/V — standard and correct. ✅
- **Contract violation in `_update_power_state()`:** contract mandates SOC-gating alone
  (CRITICAL at soc ≤ 10 %, LOW_POWER_MODE 10 < soc ≤ 20 %, regardless of net power and
  explicitly: "A NOMINAL state with battery_soc_pct = 5 is a data integrity failure").
  Implementation instead: CRITICAL only if soc < 20 % **and** net < 0; so a fully
  sunlit, discharging-balanced system at SOC 5 % would emit… NOMINAL. **Must fix.**
- **Voltage model caveat:** `v_temp = (25 − temp_c) × 0.16` *increases* voltage in the
  cold. Real Li-ion OCV barely moves with temperature; the comment even says "Cold =
  higher voltage". It's a documented model assumption (contract permits this), but flag
  for rework once comms/thermal couple in.
- **Constants mismatch vs contract/source:** array area 56 m² ("2 wings × 28 m²") and
  efficiency 0.30 vs contract-sourced 4 wings / ~44.8 m² / 11.2 kW design point.
  `state_engine/physics.py` duplicates SOLAR_ARRAY_AREA_M2 = 56 m² with efficiency 0.30 —
  two sources of truth for the same hardware. Consolidate into config.
- `available_power_w = array + max_discharge_power` does not implement the contract's
  stated semantic ("available above essential loads (800 W floor)… negative = CRITICAL").
  Decide and align.

### 2.4 Cross-model bus — ✅ correct design

1-tick lag semantics implemented as documented; thermal↔power coupling via
`electronics_bay_temp_k` / `power_dissipation_w`. Note: `power_dissipation_w` is fed
`total_load_w` (contract arch doc says ~8 % of electrical load converts to bay heat) —
when wired, the thermal model should receive a *fraction*, not 100 % of load, or the
contract's own coupling description ("~8 %") is the thing to drop. Open decision.

---

## 3. Runtime wiring — the real problem (verified against live DB)

`runner.py` tick functions state "TODO: Implement thermal/power/comms/radiation models"
and return constants. Verified live:

| Table | Evidence |
|-------|----------|
| `thermal_output` | `temp_electronics_bay_k` = 293.15 for **every** row (min=max, 1 distinct value over 209,000+ rows) |
| `power_output` | `battery_soc_pct` = 90 for every row |
| `state_snapshot` | `x_km` = 0 for every row; `earth_distance_km` constant 384,400 km |

Consequences:
1. Docs claiming "StateEngine / Thermal / Power ✅ Complete and verified" are misleading
   — *code* exists and unit tests pass, but no physics executes at runtime.
2. The placeholder state **violates contract 01**: `earth_distance_km = 384,400` while
   √(x²+y²+z²) = 0 — breaks the <1 km consistency rule. Any future Layer-1 anomaly
   detector would fire on every tick.
3. Dashboard design (next doc) must treat thermal/power/trajectory pages as
   "placeholder-mode" until the runner is wired.

**Fix list for the runner (owned scope):**
- Instantiate `StateEnginePhysics(liftoff_utc)`, `ThermalModel3Node.from_config(...)`,
  `PowerModel(...)` in `SimulatorRunner.__init__`.
- `_tick_state_engine` → interpolate the NASA OEM arcs in
  `data/oem/all-artemis-ii-oem-files.zip` (CCSDS OEM v2.0, EME2000, Earth-centered,
  UTC, 240 s cadence) — e.g. load the latest arc at startup, linear/Lagrange-interpolate
  to MET. (`StateEnginePhysics.compute_state_at_met` circular-orbit placeholder is a
  fallback until the OEM loader exists.)
- `_tick_thermal` → `thermal.step(...)` using state + `cross_model.power_dissipation_w`.
- `_tick_power` → `power.step(...)` using state + cross-model temp/degradation.
- Fix `PowerModel._update_power_state` and `ThermalModel3Node.thermal_state`/`heater_setpoint_k`
  to match contracts **before** enabling.
- Keep constants for comms/radiation/packet/anomaly/ML (others' scope), clearly
  tagged placeholder.

---

## 4. Suggested contract edits (low-risk, non-normative text only)

1. `01_state_engine`: reconcile penumbra (either drop "no penumbra" from limitations or
   drop PENUMBRA from enum — recommend keeping PENUMBRA since the implementation
   models it).
2. Normalize leftover mixed-case names inside `type: text` quality descriptions in all
   three contracts (`solar_flux_W_m2`, `temp_sun_face_K`, `solar_array_power_W`, …).
3. `02_thermal`: state the 268 K setpoint once, remove the 268-vs-283 contradiction.
4. `03_power`: align `available_power_w` text with implementation (or vice versa).

*Physics bounds themselves need no changes.*
