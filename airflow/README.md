# airflow

Schedules the real-data ingest jobs (`packages/pipelines`). Each task runs one ingest
module with its normal command, `python -m pipelines.ingest.<source>`, through a
`BashOperator`. Airflow is opt-in: compose profile `airflow`.

## DAGs

| DAG | Schedule | Sources |
|-----|----------|---------|
| `real_data_backfill` | manual | All eight: `nasa_oem`, `mission_events`, `jpl_orion`, `jpl_moon`, `jpl_dsn_geometry`, `donki`, `iswa_goes_protons`, `jpl_cad` |
| `real_data_refresh` | daily | The ones whose data can still change: `donki`, `iswa_goes_protons`, `jpl_cad` |

Tasks have no dependencies on each other: a failed source doesn't stop the others, but the
run still ends "failed" so it shows. Tasks run strictly **one at a time**, in the listed
order (JPL fair use). Both DAGs share the one-slot `real_data_ingest` pool, which
`airflow-init` creates. Each task retries twice, 5 minutes apart, with a 30-minute
timeout.

## Run

```bash
docker compose --profile airflow up -d --build      # UI: http://localhost:8080 (user admin)
docker compose exec airflow-scheduler airflow dags trigger real_data_backfill
docker compose exec airflow-scheduler airflow dags list-runs real_data_backfill
```

The admin password is `AIRFLOW_ADMIN_PASSWORD` (default `admin` on a laptop; required in
production). Airflow keeps its metadata in an `airflow` database on the same PostgreSQL
server. The UI listens on `127.0.0.1` only; on the server, use
`ssh -L 8080:localhost:8080 <server>`.

## Files

| Path | Holds |
|------|-------|
| `dags/real_data_ingest.py` | The two DAGs |
| `dags/real_data_sources.py` | The source lists and the task command. No Airflow imports, so plain unit tests can import it. Listed in `.airflowignore` |
| `Dockerfile` | Airflow 3.3 (slim) plus a separate `pipelines` venv in `/opt/pipelines`, so the ingest jobs don't share Airflow's dependencies. Its `test` stage adds pytest |

A new ingest module must be added to `BACKFILL_SOURCES` (and to `REFRESH_SOURCES` if its
data still changes); a unit test fails until every module is listed.

## Tests

```bash
uv run pytest tests/unit/airflow                    # natively: the source lists; the DAG tests skip
docker compose run --rm --build airflow-tests       # the DAG tests, in the Airflow image
```
