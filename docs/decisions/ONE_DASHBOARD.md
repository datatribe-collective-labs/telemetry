# One dashboard: retire the Data Explorer

> **Status:** proposed 2026-11-04 (issue #32); accepted once agreed in the PR review
> **Replaces:** the three-tier dashboard plan in `docs/architecture/DASHBOARD_ARCHITECTURE.md`
> (#25) and the "deliberately independent" rule for `packages/streamlit_dashboard` in `CLAUDE.md`.

## Context

The repo had two Streamlit apps:

| | Data Explorer | Digital Twin dashboard |
|---|---|---|
| Code | `packages/streamlit_dashboard/` | `dashboard/src/prototype/` |
| Data | real data only | synthetic data, with real data alongside |
| Reads from | TimescaleDB directly (SQL) | the backend API |

The Data Explorer came first and proved the ingest -> store -> visualize pattern. By
#38/#39 the Digital Twin dashboard read the same real-data tables (Orion ephemeris, DSN
geometry, DONKI, GOES) through the backend, with every chart labelled Real / Synthetic /
Placeholder. That left two data layers for the same tables, two caches (60 s vs 10 min)
that could disagree after a re-ingest, and overlapping charts, and the split confused
readers: it looked like "batch vs streaming" but wasn't, since the Digital Twin
dashboard shows both.

## Decision

1. **One app**, the Digital Twin dashboard (`dashboard/src/prototype/`), reading all data
   through the backend.
2. **Retire the Data Explorer without porting its pages.** Compared with the Digital Twin
   dashboard on `main`, its content was already covered or was debugging detail:

   | Data Explorer content | Already in the Digital Twin dashboard? | Outcome |
   |---|---|---|
   | Orion 3D trajectory + Moon | Mission map (with Moon and replay) | dropped |
   | Orion distance / speed over time | Mission readout at any replay time | dropped |
   | Orion specific orbital energy | no - engineer-level, no story for this audience | dropped |
   | Orion raw vectors | Model accuracy → Raw data | dropped |
   | DSN relay timeline | Space environment → Contact windows | dropped |
   | DSN elevation per day | "Orion is N° above the horizon" in contact-now | dropped |
   | DSN signal delay (light time) | no | **added** to contact-now |
   | DSN offset chart | no - technical detail | dropped |
   | GOES storm scale (S1/S2/S3+) | storm bands on the particles chart | dropped |
   | GOES other energy channels | no - ≥10 MeV is what the NOAA storm scale uses | dropped; revisit with the radiation model |
   | DONKI events table | under the particles chart | dropped |
   | DONKI inventory / raw JSON | no - debugging; use the backend's `/docs` or `psql` | dropped |
   | Close Approaches | no | dropped (see below) |

3. **Close Approaches is not shown.** Asteroid flybys don't affect the spacecraft: the
   closest during the flight was 2026 GD, ~58,000 km from Orion on Apr 9 and roughly
   15-30 m across, far too faint and light to register on any sensor. The `jpl_cad` ingest,
   its table and the `/close-approaches` route stay (`jpl_cad.py` is the reference ingest
   pattern); removing them is a separate decision.

## Consequences

- Nothing is lost at the data level: every ingest job, table and backend route stays, so
  a dropped chart can come back on a Digital Twin dashboard page later.
- Adding a real data source now means ingest module + backend model/route + dashboard
  page (see "Adding another data source" in the root `README.md`), instead of a
  self-contained ingest + Explorer page.
- The dashboard is now a virtual `uv` workspace member (`dashboard/pyproject.toml`) that
  declares its own dependencies; before, it got `streamlit`/`plotly`/`pandas` only
  because the Data Explorer package installed them into the shared `.venv`. Run it with
  `uv run --package dashboard streamlit run dashboard/src/prototype/app.py`.
- Later: rename `dashboard/src/prototype` to `dashboard/app` (#32, last step), and the JS
  "Mission Control" front end remains the long-term plan.
