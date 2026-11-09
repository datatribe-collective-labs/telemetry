"""DAG tests. They need Airflow, so they run in the Airflow image:

    docker compose run --rm --build airflow-tests

and are skipped natively. `airflow.sdk` (not `airflow`) is the probe: the repo's
own `airflow/` folder can import as an empty namespace package.
"""

import sys

import pytest

pytest.importorskip("airflow.sdk")

from airflow.configuration import conf
from airflow.dag_processing.dagbag import DagBag

BACKFILL = (
    "nasa_oem",
    "mission_events",
    "jpl_orion",
    "jpl_moon",
    "jpl_dsn_geometry",
    "donki",
    "iswa_goes_protons",
    "jpl_cad",
)
REFRESH = ("donki", "iswa_goes_protons", "jpl_cad")


@pytest.fixture(scope="module")
def dagbag():
    # The dag-processor puts the DAG bundle folder on sys.path (so real_data_ingest.py
    # can import real_data_sources); a bare DagBag doesn't, so do it here.
    dags_folder = conf.get("core", "dags_folder")
    sys.path.insert(0, dags_folder)
    try:
        yield DagBag(dag_folder=dags_folder)
    finally:
        sys.path.remove(dags_folder)


def test_dags_import_without_errors(dagbag):
    assert dagbag.import_errors == {}
    assert set(dagbag.dag_ids) == {"real_data_backfill", "real_data_refresh"}


@pytest.mark.parametrize(
    ("dag_id", "sources", "schedule"),
    [("real_data_backfill", BACKFILL, None), ("real_data_refresh", REFRESH, "@daily")],
)
def test_dags_run_sources_one_at_a_time_in_order(dagbag, dag_id, sources, schedule):
    dag = dagbag.dags[dag_id]
    assert dag.max_active_tasks == 1
    assert dag.max_active_runs == 1
    assert dag.schedule == schedule
    tasks = sorted(dag.tasks, key=lambda t: -t.priority_weight)
    assert tuple(t.task_id for t in tasks) == sources
    assert len({t.priority_weight for t in tasks}) == len(tasks)
    for task in tasks:
        assert task.pool == "real_data_ingest"
        assert task.weight_rule == "absolute"
        assert not task.upstream_task_ids  # a failed source doesn't block the rest
        assert task.bash_command.endswith(f"-m pipelines.ingest.{task.task_id}")
        assert task.cwd == "/opt/pipelines"
