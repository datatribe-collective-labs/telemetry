"""Viewer explainers for dashboard visualizations.

Every chart gets an "About this visualization" expander answering:
WHAT it shows / HOW to read it / WHY it matters.

Texts are grounded in the ODCS contracts (packages/contracts/src/odcs/) and the
Artemis II mission docs (docs/overview/, data/oem/). Synthetic = physics models
output (contracts 01-05); Real = JPL/NASA API data via pipelines.
"""

import streamlit as st

EXPLAINERS: dict[str, str] = {
    # ---- Overview page ----
    "overview.status": """
**What:** The spacecraft's latest self-reported health line: mission clock timestamp,
subsystem states and the aggregated `all_nominal` flag from the synthetic telemetry packet.

**How:** Green = subsystem reports NOMINAL per the ODCS contract rules (e.g. battery SOC
> 20 %; bay temp inside 249–310 K). Any state outside its contract band flips the flag.

**Why:** Mirrors a Mission Control "GO/NO-GO" wall — the first thing an operator looks at.
""",
    "overview.subsystems": """
**What:** One card per subsystem (Thermal / Power / Comms / Radiation) with its current
state from the combined telemetry packet.

**How:** States come straight from the models (`thermal_state`, `power_state`,
`comm_state`, plus the SEP flag from radiation). Cards turn amber/red when a contract
rule trips even if the global flag still lags a tick behind.

**Why:** Localizes *which* subsystem is driving a problem before you dive into its page.
""",
    "overview.vitals": """
**What:** Recent history of the five numbers that decide whether the mission is fine:
bay temperature, battery SOC, link margin, dose rate and Earth range.

**How:** Time series from the backend (`/telemetry/synthetic/*`); dashed bands are the
contract thresholds. Hover any point for the exact UTC value.

**Why:** Contracts encode "safe vs unsafe" as exact bounds — this chart shows how close
the vehicle rides to them, i.e. *margin*, which is what trend-watchers actually track.
""",
    # ---- Trajectory page ----
    "trajectory.3d": """
**What:** 3D Earth-centered view (EME2000 frame) of two trajectories around the Earth
sphere (blue): the real JPL Horizons/OEM arc (cyan) and the StateEngine replay (red
dashed). Dot color encodes speed.

**How:** Orbit with the mouse. Positions come from `/telemetry/real/orion` (NASA/JPL
ground truth, 4-min cadence) and `/telemetry/synthetic/state` (the physics replay).
The synthetic line interpolates NASA's own planning OEM arcs, so a faithful model traces
the cyan line almost exactly.

**Why:** The whole twin's premise: synthetic vs reality on one plot — divergence between
the lines *is* model error. Watch the lunar-distance excursion grow toward flyby day.
""",
    "trajectory.compare": """
**What:** Position components, velocity components, Earth range and speed — real vs
synthetic overlaid per-axis, with residual curves (real − synthetic) underneath.

**How:** Same colors per quantity (cyan X, red Y, teal Z); dashed = synthetic. The
residual panels should stay near zero; any drift is a bug in interpolation or frames.

**Why:** Component-wise comparison exposes frame/time-tag errors that a scalar range
plot would hide — e.g. the ~69 s Horizons TDB/UT time-tag gotcha documented in CLAUDE.md.
""",
    "trajectory.residuals": """
**What:** Statistics (mean, std, max) of each residual component over the merged window.

**How:** Residuals are computed on timestamps matched within 30 s of each other (real is
4-min cadence, synthetic 1 Hz). Until the replay clock reaches the real arc's start the
numbers read "no overlap yet".

**Why:** One number answers "is the twin drifting?" — a growing mean X-residual typically
means ephemeris mismatch; growing std means timing jitter.
""",
    "trajectory.solar": """
**What:** Solar flux at the spacecraft (W/m²), sun-incidence angle on the array face,
and eclipse state (SUNLIT / PENUMBRA / UMBRA).

**How:** Flux follows the inverse-square law from 1361 W/m² at 1 AU; the incidence angle
drives both array power and hot-face heating. Eclipse steps down to 0 flux in UMBRA.

**Why:** Every thermal and power event in this simulation is downstream of these three
curves — the 64-min HEO Earth eclipse and the ~1 h lunar flyby eclipse are the mission's
cold-soak stories.
""",
    # ---- Thermal page ----
    "thermal.temps": """
**What:** The three model nodes in °C: sun-facing exterior panel, shadow-facing
radiator, and the electronics bay.

**How:** Dashed lines mark the contract-02 bands: bay cold-survival 249 K (−24 °C) and
hot limit 310 K (37 °C). The exterior faces can safely swing much wider than the bay.

**Why:** The bay holds avionics and batteries — the mission-critical node. Exterior
nodes swing through eclipse; the bay should stay in band via insulation + heater. If it
doesn't, the survival heater story (below) becomes visible.
""",
    "thermal.flows": """
**What:** Heat flows (W): absorbed sunlight, radiated loss, internal avionics heat
(coupled from the power model), heater input — plus the net balance (in − out).

**How:** Energy balance closes when the curves mirror each other: Q_absorbed + Q_internal
≈ Q_radiated at steady state. Net ≈ 0 means equilibrium; large positive = warming.

**Why:** This is the contract's conservation rule made visible — a model bug that breaks
energy bookkeeping shows up here as an imbalance before it shows in temperatures.
""",
    "thermal.heater": """
**What:** Survival-heater ON/OFF events over the bay temperature trace.

**How:** Contract hysteresis: heater turns on below 268 K (−5 °C), off above 270 K.
Red shading marks active periods.

**Why:** Heater duty cycle is the cheapest "how cold is the mission?" proxy. In the
HEO eclipse and lunar-flyby shadow you should see it hold the bay above the setpoint —
that's its whole job.
""",
    "thermal.eclipse": """
**What:** Shadow-face temperature against eclipse state, and the eclipse mix over the
window.

**How:** In UMBRA, `q_solar` drops to zero and the shadow face free-cools toward the
deep-space sink (~3 K). Recovery after umbra ends validates the model's time constants.

**Why:** Eclipse thermal behavior decides battery survival during the mission's two
night-side passes — this page is where cold-soak becomes visible.
""",
    # ---- Power page ----
    "power.balance": """
**What:** Solar array generation vs total spacecraft load vs net power (generation −
load), W.

**How:** Net > 0 charges the battery, net < 0 discharges it (contract sign convention).
In UMBRA the array line dives to zero (no sunlight = no generation, physics ceiling at
≈17.1 kW face-on at 1 AU, design rating 11.2 kW).

**Why:** This is the power system's whole story in one chart — eclipses show up as
demand fed by the battery alone.
""",
    "power.battery": """
**What:** Battery SOC (%), bus voltage (V) and current (A) with charge/discharge sign.

**How:** SOC is contract-hard-limited to 0–100 %. Colored bands mark contract states:
NOMINAL > 20 %, LOW_POWER 10–20 %, CRITICAL ≤ 10 %. Current follows I = P/V on the
28 V nominal bus — both battery numbers are explicitly labeled model assumptions
(no public Orion battery spec).

**Why:** SOC is the mission's fuel gauge — the battery covers every eclipse; a
discharge slope you can't explain means a load is modeled wrong.
""",
    "power.available": """
**What:** Available power headroom (W) and the distribution of power states.

**How:** Headroom is what remains above essential loads for non-essential consumers
like the comms transmitter; negative would violate the contract (state → CRITICAL).

**Why:** This is the answer to "can we still transmit / run experiments right now?"
""",
    "power.efficiency": """
**What:** Effective array efficiency and its degradation factor over time.

**How:** Contract 03: η_eff = η_BOL × temperature derating × radiation damage; radiation
degradation only moves non-increasingly once the radiation model lands (placeholder now).

**Why:** Separates recoverable effects (angle, temperature) from permanent aging
(radiation) — the basis for long-mission power trends.
""",
    # ---- Space weather page ----
    "weather.goes": """
**What:** Real GOES integral proton flux channels (P1…P500, pfu) on a log scale —
the actual space-radiation environment measured in Earth orbit.

**How:** Log y-axis is essential: channels span orders of magnitude. The NOAA S1 storm
threshold is 10 pfu on the ≥10 MeV channel — contract's `sep_event_active` flag derives
from exactly that.

**Why:** This is ground truth for the radiation model: when flux crosses S1, the twin
should flag an SEP event and comms should degrade — the dashboard cross-checks that
join literally.
""",
    "weather.donki": """
**What:** NASA DONKI space-weather events (CME, SEP, solar flares, geomagnetic storms)
as a table and type histogram.

**How:** Each row carries start/end/event time and the full payload; the histogram shows
the mission window's event mix.

**Why:** DONKI explains *why* GOES spiked — an SEP event on Apr 7-8 near flyby would be
the mission-relevant radiation story, visible here before the model ingests it.
""",
    "weather.combined": """
**What:** GOES P1 flux with DONKI event markers on one timeline.

**How:** Vertical lines at event times; the proton trace validates that flagged events
actually carry particles.

**Why:** Single view connecting cause (solar events) to effect (proton flux at Earth) —
the operational context driving the twin's radiation and comms placeholders.
""",
    # ---- DSN coverage page ----
    "dsn.current": """
**What:** Which DSN complexes (Goldstone, Canberra, Madrid) currently *see* Orion from
the real JPL Horizons observer geometry.

**How:** A pass = elevation ≥ 10° above the local horizon (configurable model
assumption; not a universal DSN rule).

**Why:** Contact windows drive comms data rate and anomaly-alert latency — if no site
is up, the link margin on Overview should drop to NO_LINK.
""",
    "dsn.elevation": """
**What:** Elevation angle of Orion over time per site/antenna.

**How:** Curves rising above 10° are passes; 90° = directly overhead. Comparing across
sites shows the handover pattern between complexes.

**Why:** Elevation margin above the mask sets real link quality — deeper into view means
lower atmospheric loss on the S-band link.
""",
    "dsn.polar": """
**What:** Polar sky plots (azimuth × elevation) of Orion's track seen from each
70 m-class DSN site.

**How:** Read like a star chart: center = zenith (90° el), outer ring = horizon. The
colored arcs are passes along UTC.

**Why:** The classic way antenna operators visualize a track — immediately shows whether
a pass skirts the horizon (bad, lossy) or culminates high (healthy).
""",
    "dsn.range": """
**What:** Earth–spacecraft range and range-rate per site.

**How:** Range grows to ~413,000 km at the lunar flyby and collapses at entry;
range-rate inflection marks flyby. FSPL scales with log-distance, so range is the
primary driver of link margin loss through the mission.

**Why:** Antenna pointing angles aside, *this* is what makes flyby comms hard.
""",
    "dsn.windows": """
**What:** Continuous visibility windows (pass intervals) per complex as a Gantt strip.

**How:** Each bar = one uninterrupted pass; combined bars give total mission coverage.

**Why:** Scheduling answers "when can we send commands / when must data buffer?" — the
DSN handover gaps should match the comms model's NO_LINK periods.
""",
}


def explain(key: str) -> None:
    """Render the "About this visualization" expander for a chart key."""
    text = EXPLAINERS.get(key)
    if not text:
        return
    with st.expander("About this visualization"):
        st.markdown(text)
