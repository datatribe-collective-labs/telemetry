# Digital Twin Dashboard

Dashboards for the Artemis II / Orion digital twin. Strategy: Streamlit now,
Vanilla JS + Plotly.js later (see `docs/architecture/DASHBOARD_ARCHITECTURE.md`).

## `src/prototype/` - Streamlit Digital Twin v1

Consumes the FastAPI backend (`packages/backend`, `http://localhost:8000`) through
the client in `data/backend_api.py`, which returns the `contracts` Pydantic models.
It does not query the database directly.

Pages: Overview / Health, Trajectory, Thermal, Power, Space Weather, DSN Coverage.
Design notes: `docs/architecture/DASHBOARD_V1_DESIGN.md`.

### Run

The backend must be running, with data in TimescaleDB (full startup order in
`RUN_SERVICES.md`). From the repo root:

```bash
uv sync --all-packages   # the prototype needs streamlit + httpx + contracts in the shared .venv
uv run --package backend python -m backend.main             # terminal 1
uv run streamlit run dashboard/src/prototype/app.py         # terminal 2 -> http://localhost:8501
```

The prototype is not a workspace package, so it runs with a plain `uv run`.

## `src/replay/`

Empty placeholder for now.
