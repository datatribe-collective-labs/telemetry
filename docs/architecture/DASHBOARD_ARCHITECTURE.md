# Digital Twin Dashboard — Architecture & Data Display Strategy

**Status:** 
- **Prototype:** `packages/streamlit_dashboard/` — data source/pipeline exploration only (existing)
- **Digital Twin v1:** `dashboard/src/prototype/` (Streamlit + Plotly) — synthetic telemetry pages
- **Production:** `dashboard/` (Vanilla JS + Plotly.js) — **this is the real dashboard**

**Backend:** FastAPI (`packages/backend/`) serves all data via REST + WebSocket  
**Database:** TimescaleDB in Docker (port 5433) — pipelines write, backend reads, dashboard consumes

**No Superset.** JS/HTML/Plotly.js is sufficient for all visualization needs.

---

## 1. Dashboard Architecture

### Three Tiers

| Tier | Location | Purpose | Technology |
|------|----------|---------|------------|
| **Pipeline Explorer** | `packages/streamlit_dashboard/` | Explore raw JPL/NASA data ingestion, verify pipelines | Streamlit (existing) |
| **Digital Twin v1 (Prototype)** | `dashboard/src/prototype/` | Rapid iteration on synthetic telemetry views, validate physics models | Streamlit + Plotly |
| **Production Dashboard** | `dashboard/src/production/` | Mission Control grade, real-time, WebSocket-driven | Vanilla JS + Plotly.js |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE EXPLORER (separate repo area)                   │
│  packages/streamlit_dashboard/                                              │
│  Pages: Close Approaches, Orion Ephemeris, DSN Geometry, DONKI, GOES       │
│  Purpose: Verify ingestion pipelines, explore raw JPL data                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  NO synthetic telemetry pages here. Pure JPL/NASA data exploration.        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    DIGITAL TWIN v1 (Streamlit Prototype)                    │
│  dashboard/src/prototype/                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ Overview/   │  │ Trajectory  │  │ Thermal/    │  │ Anomaly/ML/     │   │
│  │ Health      │  │ (Real vs    │  │ Power/      │  │ Coupling Debug  │   │
│  │             │  │  Synthetic) │  │ Comms/Rad   │  │                 │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │
│         │                │                │                 │             │
│         ▼                ▼                ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    FASTAPI BACKEND (REST API)                       │  │
│  │  /telemetry/synthetic/*  /orion /donki /close-approaches          │  │
│  │  /iswa-goes-protons /dsn-geometry /health                        │  │
│  └────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DASHBOARD (dashboard/src/production/)         │
│  Vanilla JS + Plotly.js + WebSocket                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ Live        │  │ Mission     │  │ 3D          │  │ Operator        │   │
│  │ Telemetry   │  │ Replay      │  │ Trajectory  │  │ Alerts          │   │
│  │ Wall        │  │ (Historical)│  │ (Three.js)  │  │ (Toast/WS)      │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │
│         │                │                │                 │             │
│         ▼                ▼                ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              FASTAPI BACKEND (REST + WebSocket)                     │  │
│  │  /telemetry/synthetic/*  /orion /donki /close-approaches          │  │
│  │  /iswa-goes-protons /dsn-geometry /health                        │  │
│  │  /ws/live  (1Hz synthetic stream)                                    │  │
│  └────────────────────────────────┬────────────────────────────────────┘  │
│                                   │                                        │
│         ┌─────────────────────────┼─────────────────────────┐             │
│         ▼                         ▼                         ▼             │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐       │
│  │ TimescaleDB │          │    Kafka    │          │   Redis     │       │
│  │ (Historical)│          │  (Live)     │          │  (Cache)    │       │
│  └─────────────┘          └─────────────┘          └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Principle
- **Pipelines → DB/Kafka only** (no direct dashboard access)
- **Backend → Dashboard** (REST API with contract-compliant JSON + WebSocket for live)
- **Dashboard → Backend** (queries with filters, pagination, WebSocket for live)

---

## 2. Data Sources — What We Have

### 2.1 Real Data (JPL/NASA APIs → Pipelines → TimescaleDB)

| Table | Source | Update Cadence | Key Fields | Dashboard Page |
|-------|--------|----------------|------------|----------------|
| `orion_ephemeris` | JPL Horizons (-1024) | 4 min (OEM), 1s (burns) | x,y,z,vx,vy,vz, range, speed, light_time | **Orion Trajectory** |
| `close_approaches` | JPL SSD CAD API | Daily batch | des, CA_time, dist, v_rel, h_mag | **Close Approaches** |
| `donki_events` | NASA DONKI | ~Hourly | CME, SEP, FLR, GST events | **Space Weather** |
| `goes_integral_protons` | ISWA HAPI (GOES) | 5 min | P1-P500 integral flux (pfu) | **Radiation Monitor** |
| `dsn_site_geometry` | JPL Horizons (observer) | 4 min | azimuth, elevation, range, visible per DSS | **DSN Coverage** |

### 2.2 Synthetic Data (Physics Models → Kafka → Backend → TimescaleDB)

| Kafka Topic | Contract | Physics Model | Key Fields | Dashboard Page |
|-------------|----------|---------------|------------|----------------|
| `trajectory` | `SyntheticStateSnapshot` | StateEngine | position, velocity, solar_flux, eclipse, DSN vis | **State Engine** |
| `telemetry` | `SyntheticThermalOutput` | Thermal (3-node) | T_sun, T_shadow, T_bay, q_solar, q_rad, heater | **Thermal** |
| `telemetry` | `SyntheticPowerOutput` | Power | array_W, SOC, V, I, net_W, available_W, state | **Power** |
| `telemetry` | `SyntheticCommsOutput` | Comms (TBD) | EIRP, FSPL, Eb/N0, margin, rate, SQ, state | **Comms** |
| `telemetry` | `SyntheticRadiationOutput` | Radiation (TBD) | dose_rate, cumulative, degradation_factors, SEP | **Radiation** |
| `telemetry` | `SyntheticTelemetryPacket` | PacketAssembler | All combined + all_nominal | **Overview / Health** |
| `cross_model_state` | `SyntheticCrossModelState` | CrossModelBus | coupling variables (1-tick lag) | **Coupling Debug** |
| `events` | `SyntheticAnomalyEvent` | AnomalyDetector (TBD) | type, layer, severity, field, residual | **Anomalies** |
| `ml_features` | `SyntheticMLFeatureVector` | MLFeatureBuilder (TBD) | 37 features for ML | **ML Debug** |

---

## 3. Dashboard Pages — What to Display & Why

### 3.1 Overview / Health (Primary Landing Page)

**Purpose:** Mission Control "at a glance" — single screen health summary

| Widget | Data Source | Fields | Why |
|--------|-------------|--------|-----|
| **Mission Phase Banner** | StateEngine | MET, phase name | Context for all other data |
| **All Nominal Indicator** | `SyntheticTelemetryPacket` | `all_nominal` (boolean) | Red/Green — immediate GO/NO-GO |
| **Subsystem Health Grid** | Packet | thermal_state, power_state, comm_state, radiation (sep_active) | 4-quadrant: Thermal/Power/Comms/Rad |
| **Key Vitals** | Packet | T_bay (°C), SOC (%), Link Margin (dB), Dose Rate (mrad/hr) | Critical parameters with thresholds |
| **Position Summary** | StateEngine | Range (km), Speed (km/s), Light Time (s), Eclipse | Orbital context |
| **DSN Status** | StateEngine / DSN Geometry | Visible complexes, best elevation | Comm window awareness |

**Visual:** 4×2 card grid + small 3D trajectory inset + timeline bar

---

### 3.2 Orion Trajectory (Real + Synthetic Comparison)

**Purpose:** Validate physics model against ground truth

| View | Real Data (JPL) | Synthetic (StateEngine) | Why |
|------|-----------------|-------------------------|-----|
| **3D Trajectory** | `orion_ephemeris` x,y,z | StateEngine x,y,z | Visual overlap — divergence = model error |
| **Range vs Time** | range_km | earth_distance_km | Quantitative comparison |
| **Speed vs Time** | speed_kms | √(vx²+vy²+vz²) | Energy validation |
| **Residuals** | — | Real - Synthetic | **Most important** — shows model accuracy |
| **Orbital Energy** | v²/2 - μ/r | Same computation | Conservative quantity — should match exactly |

**Key Insight:** The synthetic model should reproduce JPL Horizons within numerical tolerance. Any divergence indicates:
- OEM interpolation error
- Two-body vs N-body dynamics mismatch
- Frame transformation bug (EME2000 vs other)

---

### 3.3 Thermal Subsystem

**Purpose:** Monitor thermal health, validate 3-node model

| Widget | Contract Fields | Thresholds (ODCS) | Why |
|--------|-----------------|-------------------|-----|
| **3-Node Temps** | T_sun, T_shadow, T_bay (K) | T_bay: 249-310K (SLS ref), T_sun < 450K | Core thermal state |
| **Heat Flows** | q_solar, q_rad, q_internal, heater_W | q_solar=0 in UMBRA | Energy balance verification |
| **Heater Timeline** | heater_active (bool) | Hysteresis: on<setpoint, off>setpoint+DB | Survival heater operation |
| **Thermal State** | thermal_state enum | NOMINAL / COLD_SURVIVAL / HOT_LIMIT | Health rollup |
| **Eclipse Correlation** | eclipse_state + T_shadow | Shadow face drops in eclipse | Model validation |
| **Cross-Model** | q_internal vs Power.total_load | ~8% of electrical load | Coupling verification |

**Visual:** 3 temperature traces + heat flow stack + heater on/off events on timeline

---

### 3.4 Power Subsystem

**Purpose:** Electrical power health, battery management

| Widget | Contract Fields | Thresholds (ODCS) | Why |
|--------|-----------------|-------------------|-----|
| **Power Balance** | array_W, load_W, net_W, battery_I | net_W sign = battery_I sign | Real-time balance |
| **Battery SOC** | SOC (%) | **0-100% hard limit** (Li-ion physics) | Most critical — CRITICAL at ≤10% |
| **Bus Voltage** | V (V) | Model eq only (no hardware bound) | Health indicator |
| **Available Power** | available_W | ≥0 (negative = CRITICAL) | Margin for comms/science |
| **Power State** | power_state enum | Strict SOC-gated (see ODCS) | Health rollup |
| **Array Efficiency** | array_efficiency | 0-1, degrades with radiation | Degradation tracking |
| **Eclipse Impact** | eclipse_fraction + array_W | Array=0 in UMBRA | Model validation |

**Visual:** Power balance waterfall + SOC timeline with state transitions + efficiency trend

---

### 3.5 Communications Subsystem (TBD — model not built)

**Purpose:** Link health, data rate management

| Widget | Contract Fields | Thresholds (ODCS) | Why |
|--------|-----------------|-------------------|-----|
| **Link Margin** | link_margin_dB | <0 = NO_LINK | Primary comm health |
| **Data Rate** | data_rate_kbps | 0,16,64,128,256,512,1250 | Adaptive rate selection |
| **Signal Quality** | signal_quality (0-1) | 0 at NO_LINK, >0 at NOMINAL | Normalized health |
| **EIRP/FSPL/Pr** | eirp_dBW, FSPL_dB, Pr_dBW | Physics-derived (Friis) | Link budget debug |
| **DSN Geometry** | dsn_site_geometry (real) | elevation ≥ 10° = visible | Real ground truth |

**Cross-reference:** Real DSN geometry (from `dsn_site_geometry` table) vs synthetic comm_state

---

### 3.6 Radiation Subsystem (TBD — model not built)

**Purpose:** Dose accumulation, hardware degradation, SEP alerting

| Widget | Contract Fields | Thresholds (ODCS) | Why |
|--------|-----------------|-------------------|-----|
| **Dose Rate** | dose_rate_mrad_hr | ≥0, no fixed ceiling | Real-time exposure |
| **Cumulative Dose** | cumulative_krad | Monotonic non-decreasing | Total mission exposure |
| **Degradation Factors** | array_deg, α_deg, ε_deg | 0<factor≤1, non-increasing | Hardware aging |
| **SEP Alert** | sep_event_active (bool) | Consistent with GOES protons | Storm warning |
| **Belt Transit** | in_belt (from ML features) | Context for dose spikes | Anomaly interpretation |

**Cross-reference:** Real GOES protons (`goes_integral_protons`) → SEP flag → synthetic sep_event_active

---

### 3.7 Space Weather (Real Data)

**Purpose:** External environment driving radiation/comms anomalies

| Page | Real Data Table | Key Visualizations |
|------|-----------------|-------------------|
| **DONKI Events** | `donki_events` | Timeline of CME/SEP/FLR/GST, event details |
| **GOES Protons** | `goes_integral_protons` | P1-P500 flux stacks, S1-S5 storm thresholds |
| **DSN Coverage** | `dsn_site_geometry` | Polar plots per complex, visibility windows |
| **Close Approaches** | `close_approaches` | NEO flyby timeline, distance/velocity |

**Why Real Data Here:** These are *inputs* to physics models (radiation, comms plasma noise). Dashboard shows ground truth that drives synthetic outputs.

---

### 3.8 Anomaly & ML Detection (TBD)

**Purpose:** Automated anomaly flagging for ops team

| Widget | Contract Fields | Layers |
|--------|-----------------|--------|
| **Event Feed** | event_id, timestamp, type, severity, description | All layers |
| **Layer 1: Contract** | CONTRACT_VIOLATION, field, bound violated | Hard rejects |
| **Layer 2: Physics Rules** | T1_THERMAL_RUNAWAY, P1_SOC_DROP, C1_LINK_DROP, residual | Physics baseline deviation |
| **Layer 3: ML** | ML_ISOLATION_FOREST, anomaly_score | Learned patterns |
| **Feature Inspector** | 37 ML features per tick | Model debugging |
| **Mission Phase Gate** | mission_phase filter | Suppress expected anomalies (e.g., heater in eclipse) |

---

### 3.9 Cross-Model Coupling Debug (Internal)

**Purpose:** Verify 1-tick lag coupling works correctly

| Coupling Path | Source Field | Target Field | Validation |
|---------------|--------------|--------------|------------|
| Thermal → Power | T_bay (K) | battery voltage temp derating | Voltage matches temp curve |
| Power → Thermal | total_load_W × 8% | q_internal_W | Heat flow matches |
| Radiation → Power | array_deg | array_efficiency | Efficiency = BOL × deg |
| Radiation → Thermal | α_deg, ε_deg | Q_solar, Q_rad | Coating properties track |
| Radiation → Comms | plasma_noise_factor | signal_quality | SQ degrades during SEP |

**Visual:** Sankey diagram of coupling + time-series of each coupling variable

---

## 4. Implementation — Streamlit Prototype (Now)

### 4.1 Backend API Endpoints — **ALREADY IMPLEMENTED**

The FastAPI backend at `packages/backend/src/backend/` already has **all synthetic and real data endpoints**:

#### Synthetic Telemetry (`/telemetry/synthetic/`)
| Endpoint | Table | Response Model | Filters |
|----------|-------|----------------|---------|
| `GET /state` | `state_snapshot` | `SyntheticStateResponse` | date_from, date_to, limit, offset |
| `GET /state/{timestamp_utc}` | `state_snapshot` | `SyntheticStateSnapshot` | — |
| `GET /thermal` | `thermal_output` | `SyntheticThermalResponse` | date_from, date_to, thermal_state |
| `GET /power` | `power_output` | `SyntheticPowerResponse` | date_from, date_to, power_state |
| `GET /comms` | `comms_output` | `SyntheticCommsResponse` | date_from, date_to, comm_state |
| `GET /radiation` | `radiation_output` | `SyntheticRadiationResponse` | date_from, date_to, sep_event_active |
| `GET /cross-model` | `cross_model_state` | `SyntheticCrossModelResponse` | date_from, date_to |
| `GET /packet` | `telemetry_packet` | `SyntheticTelemetryPacketResponse` | date_from, date_to, all_nominal, thermal_state, power_state, comm_state |
| `GET /packet/{timestamp_utc}` | `telemetry_packet` | `SyntheticTelemetryPacket` | — |
| `GET /latest` | `telemetry_packet` | `SyntheticTelemetryPacket` | — |
| `GET /anomalies` | `anomaly_events` | `SyntheticAnomalyResponse` | date_from, date_to, anomaly_type, detection_layer, severity, mission_phase |
| `GET /ml-features` | `ml_feature_vectors` | `SyntheticMLFeaturesResponse` | date_from, date_to |

#### Real Data (root-level routes)
| Endpoint | Table | Response Model |
|----------|-------|----------------|
| `GET /orion` | `orion_ephemeris` | `OrionEphemerisResponse` |
| `GET /close-approaches` | `close_approaches` | `CloseApproachResponse` |
| `GET /donki` | `donki_events` | `DonkiEventResponse` |
| `GET /iswa-goes-protons` | `goes_integral_protons` | `GoesIntegralProtonsResponse` |
| `GET /dsn-geometry` | `dsn_site_geometry` | `DsnSiteGeometryResponse` |

#### Health
| Endpoint | Response Model |
|----------|----------------|
| `GET /health` | `HealthResponse` |

#### Missing (Need to Add)
| Endpoint | Purpose |
|----------|---------|
| `GET /ws/live` | WebSocket for 1Hz live synthetic telemetry stream |
| `GET /ws/events` | WebSocket for live anomaly events |

### 4.2 Streamlit Prototype Structure (Digital Twin v1)

```
dashboard/src/prototype/
├── app.py                    # Main entry + navigation
├── data/
│   ├── engine.py             # DB engine (shared or copy from streamlit_dashboard)
│   ├── backend_api.py        # REST client for FastAPI
│   ├── synthetic.py          # Synthetic telemetry queries
│   └── real_data/            # Real data queries (orion.py, etc.)
├── pages/
│   ├── welcome.py            # Landing
│   ├── overview.py           # Health + all_nominal
│   ├── trajectory.py         # Real vs Synthetic comparison
│   ├── thermal.py            # 3-node thermal
│   ├── power.py              # Power subsystem
│   ├── comms.py              # Comms (placeholder until model)
│   ├── radiation.py          # Radiation (placeholder until model)
│   ├── anomalies.py          # Anomaly events + ML
│   ├── coupling.py           # Cross-model debug
│   └── space_weather.py      # Real: DONKI + GOES + DSN
```

**Current state:** only `overview.py`, `trajectory.py`, `thermal.py`, `power.py`, `space_weather.py`, `dsn_coverage.py` exist (`data/` contains only `backend_api.py`). `welcome.py`, `comms.py`, `radiation.py`, `anomalies.py`, `coupling.py` remain to be built.

**Note:** `packages/streamlit_dashboard/` remains unchanged — it's for pipeline/JPL data exploration only. The Digital Twin prototype lives in `dashboard/src/prototype/`.

### 4.3 Backend API Client Pattern

```python
# dashboard/src/prototype/data/backend_api.py
import httpx
from contracts import *  # Pydantic models (contracts package)

class BackendAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    async def get_synthetic_thermal(self, date_from, date_to, limit=1000) -> SyntheticThermalResponse:
        resp = await self.client.get("/telemetry/synthetic/thermal", 
            params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "limit": limit})
        return SyntheticThermalResponse(**resp.json())
    
    async def get_real_orion(self, date_from, date_to, limit=1000) -> OrionEphemerisResponse:
        resp = await self.client.get("/orion",
            params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "limit": limit})
        return OrionEphemerisResponse(**resp.json())
```

---

## 5. Production Dashboard (Vanilla JS + Plotly.js) — Future

### 5.1 Structure
```
dashboard/src/production/
├── index.html                 # Main entry
├── assets/
│   ├── main.js                # App bootstrap, routing
│   ├── api.js                 # REST + WebSocket client
│   ├── charts/                # Plotly.js chart components
│   │   ├── trajectory3d.js    # 3D orbit (Plotly.js 3D)
│   │   ├── timeseries.js      # Multi-axis time series
│   │   ├── gauges.js          # Real-time gauge indicators
│   │   └── heatmap.js         # Thermal/power heatmaps
│   ├── pages/
│   │   ├── overview.js        # Health grid + all_nominal
│   │   ├── trajectory.js      # Real vs Synthetic + residuals
│   │   ├── thermal.js         # 3-node temps + heat flows
│   │   ├── power.js           # Power balance + SOC + state
│   │   ├── comms.js           # Link margin + data rate
│   │   ├── radiation.js       # Dose + degradation + SEP
│   │   ├── anomalies.js       # Event feed + layer filter
│   │   ├── coupling.js        # Sankey + coupling time-series
│   │   └── space_weather.js   # GOES + DONKI + DSN
│   └── components/
│       ├── mission_timeline.js # Phase bar with annotations
│       ├── dsn_status.js      # DSN complex visibility
│       └── alert_toast.js     # WebSocket-driven alerts
├── styles/
│   ├── main.css               # Dark theme, responsive grid
│   └── variables.css          # CSS custom properties
└── vite.config.js             # Build config
```

### 5.2 Key Components

| Component | Technology | Data Source |
|-----------|------------|-------------|
| **Live Telemetry Wall** | Plotly.js `extendTraces` + WebSocket | `/ws/live` (1Hz) |
| **3D Trajectory** | Plotly.js `Scatter3d` + Earth mesh | REST `/telemetry/synthetic/state` + `/orion` |
| **Mission Timeline** | Custom Canvas/Plotly | Phase from `planned_attitude.py` + events |
| **DSN Status** | Polar Plotly chart | `/dsn-geometry` |
| **Alert System** | WebSocket `/ws/events` → toast | Anomaly events |

### 5.3 Backend Serving Strategy
```python
# FastAPI serves:
# - REST API for historical queries (JS initial load, pagination)
# - WebSocket /ws/live for 1Hz synthetic telemetry stream
# - WebSocket /ws/events for live anomaly events
# - Static files for JS dashboard build (mounted at /dashboard)
# - SPA fallback for client-side routing
```

---

## 6. Priority Implementation Order

| Phase | Location | Pages | Backend Endpoints | Physics Models Required |
|-------|----------|-------|-------------------|------------------------|
| **1 (Now)** | `dashboard/src/prototype/` | Overview, Trajectory, Thermal, Power, Space Weather | /telemetry/synthetic/state, /telemetry/synthetic/thermal, /telemetry/synthetic/power, /telemetry/synthetic/packet, /orion, /iswa-goes-protons, /dsn-geometry, /close-approaches, /donki | StateEngine, Thermal, Power ✅ |
| **2** | `dashboard/src/prototype/` | Comms, Radiation, Coupling | /synthetic/comms, /synthetic/radiation, /synthetic/cross-model | Comms, Radiation models |
| **3** | `dashboard/src/prototype/` | Anomalies, ML Features | /telemetry/synthetic/anomalies, /telemetry/synthetic/ml-features | AnomalyDetector, MLFeatureBuilder |
| **4 (Prod)** | `dashboard/src/production/` | JS/Plotly.js migration | WebSocket `/ws/live`, REST | All models production-ready |

---

## 7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Backend as API gateway** | Pipelines don't touch frontend; single data contract enforcement |
| **Streamlit prototype first** | Fast iteration, Python-native, uses same Pydantic contracts |
| **Real vs Synthetic comparison** | Primary validation method — JPL Horizons is ground truth |
| **ODCS contracts drive UI** | Field bounds, enums, critical flags come from contracts, not hard-coded |
| **WebSocket for live** | 1Hz synthetic telemetry → push to browser, not polling |
| **Superset removed** | JS/HTML/Plotly.js is sufficient for all visualization needs (see header) |
| **Separate anomaly page** | Different audience (ops vs engineers), different refresh rate |

---

## 8. Next Steps

1. **Add backend API routes** for synthetic telemetry (already have Pydantic response models)
2. **Create `backend_api.py`** client in streamlit_dashboard
3. **Build Streamlit pages**: overview → trajectory → thermal → power
4. **Integrate real data pages**: space_weather (merge donki/goes/dsn), keep close_approaches
5. **Add WebSocket** for live updates (phase 2)
6. **Build Comms/Radiation models** → unlock those dashboard pages
7. **Build Anomaly/ML pipeline** → unlock anomaly page
8. **Production JS** → replace Streamlit