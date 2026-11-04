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

Written for non-experts first: four pages, each answering one question, with
one shared sidebar (a **Live** toggle, or a mission-time slider when Live is off).

| Page | Question it answers | Synthetic data | Real data |
|------|---------------------|----------------|-----------|
| Mission | Where is Orion, and is it OK? | trajectory, thermal/power state | JPL Horizons Orion trajectory |
| Spacecraft health | Is it warm enough, and does it have power? | thermal, power, eclipse | - |
| Space environment | What is space around it like; can we talk to it? | - | GOES protons, DONKI events, DSN geometry |
| Model accuracy (for engineers) | Does the simulation match reality? | trajectory | JPL Horizons Orion trajectory |

Comms and radiation are not simulated yet (fixed placeholders in `physics_models`), so
the Mission page shows them as grey "Not simulated yet" tiles instead of a status.

Every chart carries data-source badges (**Real** / **Synthetic** / **Placeholder**),
a one-line plain-language summary and an "About this chart" expander. All three
live in `pages/_explain.py` (`SOURCES`, `SUMMARIES`, `EXPLAINERS`), keyed by the
name passed to `explain("<page>.<chart>")`; unit tests fail if a page uses a key
that is missing there, or if text exists for a chart no page shows.

Shared helpers (`pages/_*.py`): `_controls` (sidebar, mission constants),
`_data` (cached fetches that page through the backend's 1,000-row limit),
`_trajectory` (map, readout, real-vs-simulated separation), `_timeline`
(shading intervals, line breaks at replay jumps), `_status` (plain-language
states), `_live` (refresh interval, current producer run).

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
