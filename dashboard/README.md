# Digital Twin Dashboard

The project's one dashboard for the Artemis II / Orion digital twin: **synthetic data**
(spacecraft telemetry simulated by `packages/physics_models`) shown with **real data**
(NASA/JPL) alongside for comparison. See "Real data vs synthetic data" in the root
`README.md`. It replaced the earlier real-data-only Data Explorer
(`docs/decisions/ONE_DASHBOARD.md`).

Architecture and design decisions: [`docs/architecture/DASHBOARD.md`](../docs/architecture/DASHBOARD.md).

## `src/prototype/` - Streamlit Digital Twin dashboard (v1)

Consumes the FastAPI backend (`packages/backend`) at `$BACKEND_URL` (default
`http://localhost:8000`) through the client in `data/backend_api.py`, which returns
the `contracts` Pydantic models.
It does not query the database directly.

Written for non-experts first: five pages, each answering one question, with
one shared sidebar (a **Live** toggle, or a mission-time slider when Live is off).

| Page | Question it answers | Synthetic data | Real data |
|------|---------------------|----------------|-----------|
| Mission | Where is Orion, and is it OK? | trajectory, system status, radio link | JPL Horizons Orion trajectory and Moon, mission timeline |
| Spacecraft health | Is it warm enough, and does it have power? | thermal, power, eclipse | - |
| Radiation journey | What did the flight expose the cabin to, and why? | dose at one cabin sensor, by source and mission stage | GOES protons |
| Space environment | What is space around it like; can we talk to it, and how long does a signal take? | - | GOES protons, DONKI events, DSN geometry |
| Model accuracy (for engineers) | Does the simulation match reality? | trajectory | JPL Horizons Orion trajectory |

Every chart carries data-source badges (**Real** / **Synthetic** / **Placeholder**),
a one-line plain-language summary and an "About this chart" expander. All three
live in `views/_explain.py` (`SOURCES`, `SUMMARIES`, `EXPLAINERS`), keyed by the
name passed to `explain("<page>.<chart>")`; unit tests fail if a page uses a key
that is missing there, or if text exists for a chart no page shows.

Shared helpers (`views/_*.py`): `_controls` (sidebar, mission constants),
`_data` (cached fetches that page through the backend's 1,000-row limit),
`_trajectory` (map, readout, real-vs-simulated separation), `_timeline`
(shading intervals, line breaks at replay jumps), `_status` (plain-language
states), `_live` (refresh interval, current producer run), `_phases` (mission
phases), `_link` (radio link gaps), `_radiation` (dose charts), `_blackout` (the
lunar flyby blackout).

### Run

The backend must be running, with data in TimescaleDB (full startup order in
`RUN_SERVICES.md`). In Docker, `docker compose up -d --build` starts the dashboard
(`dashboard/Dockerfile`) with everything it needs -> http://localhost:8501.

Natively, for working on the code (`docker compose stop backend dashboard` first,
they share the ports). From the repo root:

```bash
uv sync --all-packages
uv run --package backend python -m backend.main                              # terminal 1
uv run --package dashboard streamlit run dashboard/src/prototype/app.py       # terminal 2 -> http://localhost:8501
```

`dashboard/pyproject.toml` makes `dashboard` a *virtual* workspace member: it declares
the dashboard's dependencies (`streamlit`, `plotly`, `pandas`, `httpx`, `contracts`) but
isn't built or installed, so pages keep importing each other as
`dashboard.src.prototype...` from the repo root (`app.py` puts it on `sys.path`).

## `src/replay/`

Empty placeholder for now.
