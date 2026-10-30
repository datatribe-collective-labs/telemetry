# Digital Twin Dashboard

Dashboards for the Artemis II / Orion digital twin: **synthetic data** (spacecraft
telemetry simulated by `packages/physics_models`) shown with **real data** (NASA/JPL)
alongside for comparison. See "Real data vs synthetic data" in the root `README.md`.

Not to be confused with the **Data Explorer** (`packages/streamlit_dashboard/`),
which shows real data only, straight from TimescaleDB.

Strategy: Streamlit now, a Vanilla JS + Plotly.js "Mission Control" later (see
`docs/architecture/DASHBOARD_ARCHITECTURE.md`).

## `src/prototype/` - Streamlit Digital Twin dashboard (v1)

Consumes the FastAPI backend (`packages/backend`, `http://localhost:8000`) through
the client in `data/backend_api.py`, which returns the `contracts` Pydantic models.
It does not query the database directly.

| Page | Synthetic data | Real data alongside |
|------|----------------|---------------------|
| Overview / Health | latest telemetry packet | - |
| Trajectory | state engine trajectory | JPL Horizons Orion trajectory (residuals) |
| Thermal | thermal model | - |
| Power | power model | - |
| Space Weather | - | GOES protons, DONKI events, DSN geometry |
| DSN Coverage | - | DSN site geometry |

Comms, radiation and packet values are still placeholders from the physics models.
Design notes: `docs/architecture/DASHBOARD_V1_DESIGN.md`.

### Run

The backend must be running, with data in TimescaleDB (full startup order in
`RUN_SERVICES.md`). From the repo root:

```bash
uv sync --all-packages   # the dashboard needs streamlit + httpx + contracts in the shared .venv
uv run --package backend python -m backend.main             # terminal 1
uv run streamlit run dashboard/src/prototype/app.py         # terminal 2 -> http://localhost:8501
```

It is not a workspace package, so it runs with a plain `uv run`.

## `src/replay/`

Empty placeholder for now.
