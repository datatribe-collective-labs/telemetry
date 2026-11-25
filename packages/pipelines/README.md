# pipelines

The **real data** path: small batch jobs that fetch public NASA/JPL data and write it to
TimescaleDB. One self-contained module per source in `src/pipelines/ingest/`. Each owns its
table (schema, hypertable) and is run with `python -m`. Where it sits:
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).

## Sources

| Module | Source | Table |
|--------|--------|-------|
| `nasa_oem` | NASA OEM ephemeris files (`data/oem/`, no network) | `oem_state_vectors` |
| `mission_events` | Mission timeline (`contracts.planned_attitude`, no network, draft) | `mission_events` |
| `jpl_orion` | JPL Horizons, Orion (VECTORS) | `orion_ephemeris` |
| `jpl_moon` | JPL Horizons, Moon (VECTORS) | `moon_ephemeris` |
| `jpl_dsn_geometry` | JPL Horizons, Orion from each DSN site (OBSERVER) | `dsn_site_geometry` |
| `donki` | NASA DONKI space weather events | `donki_events` |
| `iswa_goes_protons` | GOES proton flux via NASA iSWA HAPI | `goes_integral_protons` |
| `jpl_cad` | JPL SSD close approaches (CAD) | `close_approaches` |

## Run

From the repo root, with the database up (`docker compose up -d timescaledb`) and `.env`
in place:

```bash
uv run --package pipelines python -m pipelines.ingest.jpl_orion
uv run --package pipelines python -m pipelines.ingest.jpl_orion --help   # its options
```

Most modules take their time window and query options as command-line flags. The defaults
cover the Artemis II mission (for `jpl_cad`: the next 60 days). Re-running is safe: rows
are upserted on the table's key (`mission_events` replaces its whole table). In Docker,
Airflow runs the same commands (`airflow/README.md`).

The connection comes from `DATABASE_URL`, or else `POSTGRES_USER` / `POSTGRES_PASSWORD` /
`POSTGRES_DB` on `localhost:5433` (`src/pipelines/db.py`, the only shared code).

## Rules

- **One request at a time.** The JPL APIs' fair-use policy forbids concurrent requests;
  Airflow's one-slot pool keeps the jobs sequential too.
- **Horizons VECTORS:** request `TIME_TYPE=UT` and `REF_PLANE=FRAME` (UT, EME2000), and parse
  the plain-text table, not `CSV_FORMAT=YES`. More source gotchas are in `CLAUDE.md`.
- **No import from `backend`**, and no shared database package: this duplication is
  deliberate.

## Add a source

1. `src/pipelines/ingest/<source>.py`, shaped like `jpl_cad.py`: schema DDL, hypertable,
   a dataclass for parsed records, `fetch_*` / `upsert_*` / `main()`.
2. Add it to `BACKFILL_SOURCES` (and `REFRESH_SOURCES` if its data still changes) in
   `airflow/dags/real_data_sources.py`. A unit test fails until it is listed.
3. Unit tests in `tests/unit/pipelines/ingest/<source>/` (HTTP mocked with `responses`).
4. The backend route and dashboard chart: the full checklist is in the root `README.md`.

## Tests

```bash
uv run pytest tests/unit/pipelines
```
