# Digital Twin dashboard

How the project's one dashboard is built: a multi-page Streamlit app in
`dashboard/src/prototype/` that shows the **synthetic data** (simulated Orion telemetry)
with the **real data** (NASA/JPL) alongside. How to run it:
[`dashboard/README.md`](../../dashboard/README.md). Where it sits in the whole system:
[`ARCHITECTURE.md`](../ARCHITECTURE.md).

## Data flow

```
backend (FastAPI) --> data/backend_api.py --> views/_data.py --> pages (views/*.py)
```

- **`data/backend_api.py`** is the one HTTP client. It is synchronous (`httpx`), reads
  `$BACKEND_URL` (default `http://localhost:8000`) and returns the `contracts` Pydantic
  models. The dashboard never connects to the database.
- **`views/_data.py`** holds the `@st.cache_data` loaders. The backend returns at most
  1,000 rows per request, so `fetch_all` pages through each table. Real tables are cached
  for minutes; the synthetic history reloads at most once a minute, and each refresh
  between reloads only fetches the newest rows.
- **Pages** turn the DataFrames into Plotly charts.

## Pages

Written for non-experts first: each page answers one question.

| Page | File | Question | Charts |
|------|------|----------|--------|
| Mission (landing) | `views/mission.py` | Where is Orion, and is it OK? | Earth-Moon map (real and simulated path), mission timeline, system status, radio link timeline |
| Spacecraft health | `views/health.py` | Is Orion warm enough, and does it have power? | Electronics temperature and heater, battery charge, solar power vs load |
| Radiation journey | `views/radiation.py` | What did the flight expose the cabin to, and why? | Dose rate, total dose by source, dose per mission stage, real solar particles with an Artemis I what-if |
| Space environment | `views/environment.py` | Was there a solar storm, and could Earth reach Orion? | Two whole-flight answers, solar particles and events, which DSN site can reach Orion now, contact windows, the lunar flyby blackout |
| Model accuracy (for engineers) | `views/accuracy.py` | Does the simulation match reality? | Distance between the simulated and the real Orion |

Pages are registered with `st.Page` in `app.py` and live in `views/`. The folder must
not be called `pages/`: Streamlit would also run those files as stand-alone pages
(see the comment in `app.py`).

## Live and replay

One sidebar (`views/_controls.py`) is rendered on every page, so its state carries over
between pages:

- **Live on** (default): each page's data section is an `st.fragment` that reruns every
  5 seconds (`views/_live.py`) and follows the simulator's newest tick.
- **Live off:** a mission-time range slider selects the window. On the Mission page a
  replay slider (with Play) moves Orion and the Moon along the real NASA/JPL path, so
  the page also works without the simulator running.

The simulator can run faster than real time or start mid-mission (`PHYSICS_MODELS_TIME_SCALE`,
`PHYSICS_MODELS_START_MET_SECONDS`; see [`RUN_SERVICES.md`](../../RUN_SERVICES.md)), so the dashboard has no
time controls of its own beyond these.

## Source badges and explainers

Every chart calls `explain("<page>.<chart>")`, which renders three things from
`views/_explain.py`:

1. badges for where the data comes from (`SOURCES`): **Real · NASA/JPL**,
   **Synthetic · our simulation** or **Placeholder · not simulated yet**,
2. a one-sentence plain-language summary (`SUMMARIES`),
3. an "About this chart" expander with what it shows, how to read it and why it matters
   (`EXPLAINERS`).

A unit test fails if a page uses a key that is missing from these dicts, or if a dict has
text for a chart no page shows.

## Shared helpers

| Module | Holds |
|--------|-------|
| `_controls.py` | Sidebar and mission constants (liftoff, mission window) |
| `_data.py` | Cached, paged loaders |
| `_live.py` | Refresh interval, current simulator run |
| `_explain.py` | Badges, summaries, explainers |
| `_trajectory.py` | Earth-Moon map, live/replay readout, real-vs-simulated separation |
| `_timeline.py` | Shading intervals, line breaks at replay jumps |
| `_phases.py` | The five mission phases, boiled down from the ~110-segment planned timeline |
| `_status.py` | Plain-language wording and colours for the models' state codes |
| `_link.py` | Radio link gaps and their reasons |
| `_blackout.py` | NASA's planned lunar flyby blackout window (real-data page) |
| `_radiation.py` | Dose by source and stage, and the Radiation journey charts |

The pure helpers are unit tested in `tests/unit/dashboard/`.

## Design decisions

| Decision | Why |
|----------|-----|
| Backend REST only, no database access | Contract-shaped JSON is enforced once, in the backend; the dashboard stays stateless |
| Real and simulated data on the same chart where both exist | Comparing the simulation with NASA/JPL data is the point of the project |
| Every chart badged Real / Synthetic / Placeholder | Placeholder values must not look like physics |
| Plain language first, an engineers' page apart | The audience is mostly non-experts |
| Plotly | One library for the Earth-Moon map and the time series, with consistent hover |
| Polling with `st.fragment`, no WebSocket | The backend has no WebSocket endpoints; a 5-second refresh suits a 1 Hz simulator |
| One dashboard | See [`decisions/ONE_DASHBOARD.md`](../decisions/ONE_DASHBOARD.md) |

## Not built

- **Anomaly and ML pages**: the simulator only emits placeholder anomaly events and ML
  features, so no page shows them.
- **A JavaScript "Mission Control" dashboard** (Vanilla JS + Plotly.js, pushed over
  WebSocket) was the long-term plan. Neither it nor the backend WebSocket endpoints exist.
- **`dashboard/src/replay/`** is an empty placeholder.
