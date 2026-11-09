"""Airflow DAGs that load the real NASA/JPL data into TimescaleDB.

- `real_data_backfill`: manual trigger. Every ingest module, e.g. after a fresh
  deploy or a `docker compose down -v`.
- `real_data_refresh`: daily, the sources that can still change.

Tasks have no dependencies on each other: a failed source does not block the
others, and the DAG run still ends "failed" so it is visible. They run strictly
one at a time (`max_active_tasks=1` plus the one-slot `real_data_ingest` pool,
shared by both DAGs), in the listed order via descending `priority_weight`.
"""

from datetime import UTC, datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from real_data_sources import (
    BACKFILL_SOURCES,
    INGEST_POOL,
    PIPELINES_DIR,
    REFRESH_SOURCES,
    ingest_command,
)

DEFAULT_ARGS = {
    "owner": "telemetry",
    "pool": INGEST_POOL,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


def ingest_dag(dag_id: str, sources: tuple[str, ...], schedule: str | None, doc_md: str) -> DAG:
    with DAG(
        dag_id=dag_id,
        schedule=schedule,
        start_date=datetime(2026, 11, 1, tzinfo=UTC),
        catchup=False,
        max_active_runs=1,
        max_active_tasks=1,
        default_args=DEFAULT_ARGS,
        tags=["real-data", "ingest"],
        doc_md=doc_md,
    ) as dag:
        for rank, source in enumerate(sources):
            BashOperator(
                task_id=source,
                bash_command=ingest_command(source),
                cwd=PIPELINES_DIR,
                # First listed source runs first.
                priority_weight=len(sources) - rank,
                weight_rule="absolute",
            )
    return dag


backfill = ingest_dag(
    "real_data_backfill",
    BACKFILL_SOURCES,
    schedule=None,
    doc_md="Load **all** real data (OEM arcs, timeline, Horizons, DSN, DONKI, GOES, CAD). "
    "Trigger by hand after a fresh deploy.",
)

refresh = ingest_dag(
    "real_data_refresh",
    REFRESH_SOURCES,
    schedule="@daily",
    doc_md="Re-fetch the real data that can still change (DONKI, GOES protons, JPL CAD).",
)
