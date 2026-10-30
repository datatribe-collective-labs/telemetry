# Digital Twin Dashboard v1 — Design (Streamlit Prototype)

**Date:** 2026-10-19
**Location:** `dashboard/src/prototype/` (Streamlit + Plotly)
**Scope:** the *Digital Twin* dashboard. `packages/streamlit_dashboard/` is a separate,
internal pipeline-explorer for real JPL/NASA data — **do not extend it**.
Superset is removed from the plan. Production "Mission Control" JS comes later (see
`DASHBOARD_ARCHITECTURE.md` §5); v1 is Streamlit.

**Reality check:** as of 2026-10-19 the
state engine interpolates real NASA OEM arcs and thermal/power run their real models;
comms, radiation, packet assembly, anomaly and ML features still emit placeholders.
Everything below works in both modes; comms/radiation widgets carry a placeholder banner
until those generators land (other contributors' scope).

**Replay controls exist** (`time_scale` / `start_met_seconds`, env or config — see
`RUN_SERVICES.md`): the demo can run at ×300 or jump to the flyby, so the dashboard does
not need its own time controls for v1; `st.fragment` refresh is enough.

---

## 1. What v1 must answer (user questions → pages)

| Mission-ops question | Page | Primary data |
|----------------------|------|--------------|
| Is the vehicle healthy *right now*? | **Overview** | `GET /telemetry/synthetic/latest` |
| Where is Orion / how far along the flyby? | **Trajectory** | `/telemetry/real/orion` + `/telemetry/synthetic/state` |
| Is the thermal system behaving (esp. through eclipse)? | **Thermal** | `/telemetry/synthetic/thermal` |
| Do we have power margin (battery drain in eclipse)? | **Power** | `/telemetry/synthetic/power` |
| Can we talk to it? (DSN windows, link budget) | **Comms & DSN** | `/telemetry/synthetic/comms` + `/dsn-geometry` (real) |
| Is the space environment nominal? (SEP storm?) | **Space Weather** | `/donki`, `/iswa-goes-protons` |

Layout principle: **one row of KPI cards on top of every page** (mission clock, range,
all_nominal) so context survives page switches.

## 2. Data organization

All data comes from the FastAPI backend (`http://localhost:8000`) via the existing
`dashboard/src/prototype/data/backend_api.py` client. **No direct DB connections in the
dashboard** — the backend enforces contract-shaped JSON.

```
dashboard/src/prototype/
├── app.py                 # st.navigation entry — registers the 6 pages
├── data/
│   ├── backend_api.py     # REST client (exists) — add caching wrappers here
│   ├── mission_clock.py   # liftoff_utc from config → MET, mission phase labels
│   └── trajectory_flyby.py# Earth/Moon ephemeris helpers, flyby event markers
└── pages/
    ├── overview.py        # exists
    ├── trajectory.py      # exists → becomes flyby-centric in v1
    ├── thermal.py         # exists
    ├── power.py           # exists
    ├── comms_dsn.py       # new (upgrade from placeholder)
    └── space_weather.py   # exists
```

Caching: use `@st.cache_data(ttl=15)` on list endpoints; the backend is the single
data authority, so 15 s freshness beats polling the DB directly. Page-level
`st.fragment(run_every=...)` for live-ish refresh; no WebSocket in v1 (backend `/ws/*`
not implemented).

### Time base
Everything is keyed by `timestamp_utc` (contract primary key). Add a derived **MET
(mission elapsed time)** in `data/mission_clock.py` from `liftoff_utc`
(`packages/physics_models/configs/*`: 2026-04-01T22:35Z). Every plot shows both UTC and
MET on the x-axis (use secondary hover text — dual axes in Plotly are more pain than
value). Mission event markers come from a small table in `mission_clock.py`
(launch, ICPS sep, HEO start/end, TLI, flyby, entry) — initial values from the contract
notes, refined from the external research summarized in §6.

## 3. Page designs

### 3.1 Overview (landing)
- **GO/NO-GO banner:** `all_nominal` from `/telemetry/synthetic/latest` (big
  green/red `st.metric`), plus thermal_state / power_state / comm_state chips.
- **KPI row:** range (km), speed (km/s), light time (s), SOC (%), bay temp (°C),
  dose rate (mrad/hr) — from latest packet.
- **Mission timeline strip:** horizontal annotated line from liftoff to splashdown,
  current MET marker, event markers (ICPS, eclipse window, TLI, flyby, entry).
- **3D inset:** current position point on the trajectory plot (same figure as
  Trajectory page, simplified) — gives the "where am I" answer without a page switch.

### 3.2 Trajectory — the flyby page (v1 centerpiece)
This page must make the **Artemis II free-return lunar flyby** visually legible.

- **Main figure:** Plotly `Scatter3d` with:
  - **Earth** sphere (wireframe at 6,371 km) + Moon sphere at its mean position for the
    flyby epoch — place the Moon from the `orion_ephemeris`-relative geometry or a
    simple circular orbit approximation at 384,400 km (documented approximation for v1).
  - **Real track:** `x/y/z` from `/telemetry/real/orion` (JPL Horizons -1024) drawn as a
    line; flyby closest-approach marker (min `range` to Moon) highlighted.
  - **Synthetic track:** `/telemetry/synthetic/state` line in a contrasting color with
    lower opacity. *In placeholder mode this is a constant dot near Earth-Moon midway —
    show it greyed with a "placeholder data" caption instead of pretending it's a track.*
  - **DSN ground stations** (3 points on the Earth sphere) + line-of-sight to current
    position when `dsn_visibility` true.
- **Side panels:** range-vs-time, speed-vs-time (real vs synthetic overlay) and a
  **residuals** chart (real − synthetic) — the model-validation widget. In placeholder
  mode, overlay a warning banner: "synthetic trajectory is a placeholder constant".
- **Flyby metrics box:** closest approach distance/time, peak speed, eclipse windows
  (shaded regions on the time plots) using `eclipse_state`.
- Interactions: hover shows MET + UTC; animation (Plotly frames over tick index) plays
  the flyby at ~×1000 speed. Keep animation optional (off by default, perf).

### 3.3 Thermal
- 3 node temperatures (`temp_sun_face_k`, `temp_shadow_face_k`, `temp_electronics_bay_k`),
  y-axis in °C (contract is K; display °C with toggle) with threshold bands:
  249–310 K electronics band, 450 K sun-face line (from contract 02).
- Heat-flow stacked chart: `q_solar_absorbed_w`, `q_internal_w` vs `q_radiated_w`
  (energy balance view), heater on/off events as vertical markers.
- Eclipse correlation: shade `eclipse_state != SUNLIT` regions — the thermal story of the
  flyby is *cold soak in shadow*.

### 3.4 Power
- Power-balance traces: `solar_array_power_w` vs `total_load_w`, `net_power_w` (area
  chart), battery SOC (%) with the contract-gated state bands
  (NOMINAL > 20 %, LOW_POWER 10–20 %, CRITICAL ≤ 10 % — colored bands directly from
  contract 03 rules).
- Battery voltage + current dual axis under the SOC chart.
- Available-power headroom gauge (`available_power_w` vs 800 W essential floor — v1
  shows it as a `st.progress`-style bar or bullet chart).

### 3.5 Comms & DSN (new page; replaces old `dsn_coverage.py` in the prototype)
- Link budget per tick: `eirp_dbw + fspl + received_power → eb_n0_db → link_margin_db`
  waterfall (Plotly `Waterfall` chart) — makes the Friis chain inspectable.
- Link margin vs time with 0 dB "NO_LINK" line and adaptive `data_rate_kbps` step trace
  (validValues set from contract: 0/16/64/128/256/512/1250).
- **Real DSN layer:** `/dsn-geometry` az/el polar chart per complex + visibility windows
  on a 24 h Gantt strip; compare real geometry visibility vs synthetic
  `dsn_visibility` bit (contract-consistency indicator).
- Placeholder banner while comms model is unimplemented (audit §0).

### 3.6 Space Weather
- GOES integral protons `/iswa-goes-protons` — channel stack (P1…P500) log-scale,
  S1–S5 threshold lines; DONKI event list `/donki` as a table + timeline.
- Derived flag: predicted `sep_event_active` (proton flux > 10 pfu, contract 03
  radiation rule) vs synthetic radiation field — join-check widget identical in spirit
  to the DSN comparison.

## 4. Visualization decisions (and why)

| Decision | Rationale |
|----------|-----------|
| Plotly, not matplotlib/altair | Single 3D engine for the flyby + consistent hover/time handling |
| Backend REST only, no DB from dashboard | Contract compliance is enforced once (backend); dashboard stays stateless |
| MET + event markers everywhere | The flyby story is chronological; engineers think in MET |
| Dual real+synthetic overlays on every applicable plot | Model validation is the project purpose ("real vs synthetic" is the whole point) |
| Contract bounds drive thresholds | Bands/lines come from ODCS rules, not hand-picked numbers; when contracts change, pages change |
| Placeholder banners, not fake polish | Audit showed trajectory/thermal/power emit constants; pages must label that honestly rather than chart flat lines as if they were physics |
| No WebSocket in v1 | `/ws/*` endpoints are unimplemented; 15 s cache polling is enough for prototype cadence |
| No Superset | Removed from the plan (see header) |

## 5. Build order

| Step | Deliverable | Depends on |
|------|-------------|-----------|
| 1 | `data/mission_clock.py` + event table; Overview page refresh w/ banner + timeline | backend (exists) |
| 2 | Trajectory page: Earth/Moon 3D, real Orion track, event/flyby markers | step 1 |
| 3 | Thermal + Power pages with contract threshold bands | backend (exists) |
| 4 | Comms & DSN page (link budget waterfall + real DSN overlay) | comms placeholders acceptable |
| 5 | Space Weather page + SEP join-check | existing endpoints |
| 6 | ~~Wire physics into runner (audit §3)~~ ✅ done 2026-10-19 — pages now show real curves for state/thermal/power | ✅ |
| 7 | Animation mode + polish, then start the JS production plan | all above |

Success criterion for v1: a reviewer can open the dashboard, watch the flyby replay
from liftoff to splashdown, see the eclipse cold-soak and battery story, and tell at a
glance whether synthetic telemetry matches JPL ground truth.

## 6. Open inputs / sources

**External research completed 2026-10-19** (ChatGPT answers + first-hand ESA
verification). Load-bearing updates for this design:
- Trajectory is a **hybrid free-return** (NASA NTRS, ChatGPT-cited); closest lunar
  approach ≈ 6,545 km above the surface (NASA FD6, ChatGPT-cited) — use these on the
  Trajectory page, with attribution.
- EPS: 4 wings × 3 panels, 11.2 kW peak, 120 V distribution (ESA ✅ verified);
  battery 100 Ah/28 V is an explicit MODEL_ASSUMPTION.
- **MET↔UTC drift:** timeline-PDF METs drift ≈ 1 h from the OEM trajectory by lunar
  close approach. `mission_clock.py` must derive UTC event times from the OEM arc
  (trajectory = temporal ground truth), and show timeline-METs as labeled
  planning-grid values — never silently shift either. `mission_events` stays DRAFT
  until the planned_attitude fact-check (task defined in the research doc).

**Primary source now in the repo** (`docs/overview/` PDFs + `data/oem/` OEM store):
- `data/oem/all-artemis-ii-oem-files.zip` — 9 usable NASA CCSDS OEM v2.0 arcs (EME2000, UTC, km/km/s,
  240 s cadence; 10th member is a legacy PROP_MAN entry arc, skipped). Latest arc spans
  2026-04-02 → entry (413,144 km max geocentric range, 10.999 km/s at EI). **This is the
  interpolation source used by `StateEnginePhysics` in the runner** and the ground-truth
  line for the Trajectory page.
- `artemis-ii-overview-timeline-public-final.pdf` — official event METs (planning grid;
  remember the ~1 h late-mission drift vs the OEM arc noted above).
- `sls-5558-artemis-ii-sls-reference-guide.pdf` — SLS Reference Guide (contract 02's
  Source #12 for the 249–310 K flight-computer range).

Remaining approximation: flyby closest-approach **to the Moon** needs a Moon ephemeris
join (OEM is Earth-centered); until then the Moon uses a circular 384,400 km
approximation labeled APPROX.
