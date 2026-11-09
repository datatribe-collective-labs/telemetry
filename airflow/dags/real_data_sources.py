"""The real-data ingest jobs that the Airflow DAGs in `real_data_ingest.py` run.

Kept free of Airflow imports so plain unit tests (`tests/unit/airflow/`) can import
it without Airflow installed. Listed in `.airflowignore`: it holds no DAG.

Each source is one `packages/pipelines/src/pipelines/ingest/<source>.py` module,
run through its existing CLI (`python -m pipelines.ingest.<source>`, the same
command as in RUN_SERVICES.md) with the `pipelines` venv baked into the image.
"""

import os
import shlex

# Where airflow/Dockerfile puts the pipelines venv and the OEM zip. The tasks run
# from this directory, because nasa_oem reads `data/oem/...` relative to it.
PIPELINES_DIR = os.environ.get("PIPELINES_DIR", "/opt/pipelines")
PIPELINES_PYTHON = os.environ.get("PIPELINES_PYTHON", f"{PIPELINES_DIR}/.venv/bin/python")

# One slot, shared by both DAGs (created by the `airflow-init` compose service):
# at most one ingest job runs at a time across Airflow, as the JPL SSD fair-use
# policy asks (one request at a time).
INGEST_POOL = "real_data_ingest"

# Every ingest module, in run order: the local files first (no network), then the APIs.
BACKFILL_SOURCES = (
    "nasa_oem",
    "mission_events",
    "jpl_orion",
    "jpl_moon",
    "jpl_dsn_geometry",
    "donki",
    "iswa_goes_protons",
    "jpl_cad",
)

# The daily refresh. The Artemis II ephemeris (OEM, Horizons) and the timeline are
# final, so only these are re-fetched: jpl_cad's window moves with "now"; DONKI and
# the provisional iSWA GOES feed can still be revised for the mission window.
REFRESH_SOURCES = ("donki", "iswa_goes_protons", "jpl_cad")


def ingest_command(source: str) -> str:
    """Shell command that runs one ingest module with the pipelines venv."""
    if source not in BACKFILL_SOURCES:
        raise ValueError(f"unknown ingest source: {source!r}")
    return f"{shlex.quote(PIPELINES_PYTHON)} -m pipelines.ingest.{source}"
